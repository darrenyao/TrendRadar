"""
Supabase Storage - Python 端 Supabase 存储适配器

功能：
- 存储 Twitter 帖子到 Supabase
- 存储分析结果
- 生成和存储 Embeddings
"""

import os
from datetime import datetime
from typing import Optional

import pytz

# Supabase Python 客户端
try:
    from supabase import create_client, Client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("[警告] supabase-py 未安装，请运行: pip install supabase")

# OpenAI 用于生成 embedding
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .scraper import TwitterPost
from .analyzer import AnalysisResult, TopicCluster


class SupabaseStorage:
    """
    Supabase 存储适配器

    将数据同步到 Supabase 数据库，支持向量存储
    """

    def __init__(
        self,
        supabase_url: str = None,
        supabase_key: str = None,
        embedding_model: str = "text-embedding-3-small",
        timezone: str = "Asia/Shanghai",
    ):
        """
        初始化 Supabase 存储

        Args:
            supabase_url: Supabase 项目 URL
            supabase_key: Supabase API Key
            embedding_model: Embedding 模型名称
            timezone: 时区
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase-py 未安装，请运行: pip install supabase")

        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_ANON_KEY")
        self.embedding_model = embedding_model
        self.timezone = pytz.timezone(timezone)

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "请设置 SUPABASE_URL 和 SUPABASE_ANON_KEY 环境变量"
            )

        self.client: Client = create_client(self.supabase_url, self.supabase_key)

        # 初始化 OpenAI 客户端用于 embedding
        self.openai_client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv("TWITTER_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("TWITTER_LLM_BASE_URL")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key, base_url=base_url)

    def _generate_embedding(self, text: str) -> Optional[list[float]]:
        """生成文本 embedding"""
        if not self.openai_client:
            return None

        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[警告] 生成 embedding 失败: {e}")
            return None

    def _generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[Optional[list[float]]]:
        """批量生成 embeddings"""
        if not self.openai_client or not texts:
            return [None] * len(texts)

        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"[警告] 批量生成 embedding 失败: {e}")
            return [None] * len(texts)

    # ========== 帖子存储 ==========

    def save_posts(
        self, posts: list[TwitterPost], generate_embeddings: bool = True
    ) -> int:
        """
        保存帖子到 Supabase

        Args:
            posts: 帖子列表
            generate_embeddings: 是否生成 embeddings

        Returns:
            保存的帖子数量
        """
        if not posts:
            return 0

        # 准备帖子数据
        posts_data = []
        for post in posts:
            posts_data.append(
                {
                    "post_id": post.post_id,
                    "author": post.author,
                    "author_handle": post.author_handle,
                    "content": post.content,
                    "timestamp": post.timestamp.isoformat(),
                    "likes": post.likes,
                    "retweets": post.retweets,
                    "replies": post.replies,
                    "url": post.url,
                    "media_urls": post.media_urls,
                }
            )

        # 批量 upsert
        try:
            result = (
                self.client.table("twitter_posts")
                .upsert(posts_data, on_conflict="post_id")
                .execute()
            )
            saved_count = len(result.data)
            print(f"[Supabase] 保存 {saved_count} 条帖子")

            # 生成并保存 embeddings
            if generate_embeddings and self.openai_client:
                self._save_post_embeddings(posts)

            return saved_count
        except Exception as e:
            print(f"[错误] Supabase 保存帖子失败: {e}")
            return 0

    def _save_post_embeddings(self, posts: list[TwitterPost]) -> None:
        """保存帖子的 embeddings"""
        texts = [post.content for post in posts]
        embeddings = self._generate_embeddings_batch(texts)

        embedding_records = []
        for post, embedding in zip(posts, embeddings):
            if embedding:
                embedding_records.append(
                    {
                        "content": post.content[:500],  # 截断过长内容
                        "content_type": "post",
                        "reference_id": post.post_id,
                        "embedding": embedding,
                        "metadata": {
                            "author": post.author,
                            "timestamp": post.timestamp.isoformat(),
                        },
                    }
                )

        if embedding_records:
            try:
                self.client.table("embeddings").insert(embedding_records).execute()
                print(f"[Supabase] 保存 {len(embedding_records)} 条 embeddings")
            except Exception as e:
                print(f"[警告] 保存 embeddings 失败: {e}")

    def get_posts_by_user(
        self, username: str, limit: int = 50
    ) -> list[dict]:
        """获取指定用户的帖子"""
        try:
            result = (
                self.client.table("twitter_posts")
                .select("*")
                .eq("author", username)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"[错误] 获取帖子失败: {e}")
            return []

    # ========== 分析结果存储 ==========

    def save_analysis(
        self, result: AnalysisResult, generate_embeddings: bool = True
    ) -> bool:
        """
        保存分析结果

        Args:
            result: 分析结果
            generate_embeddings: 是否生成 embeddings

        Returns:
            是否成功
        """
        try:
            # 准备聚类数据
            clusters_data = []
            for cluster in result.clusters:
                clusters_data.append(
                    {
                        "topic_id": cluster.topic_id,
                        "topic_name": cluster.topic_name,
                        "topic_summary": cluster.topic_summary,
                        "keywords": cluster.keywords,
                        "post_ids": [p.post_id for p in cluster.posts],
                        "importance_score": cluster.importance_score,
                    }
                )

            # 保存分析结果
            analysis_data = {
                "period": result.analyzed_at.strftime("%Y-%m-%d_%H"),
                "summary": result.summary,
                "clusters": clusters_data,
                "total_posts": result.total_posts,
                "analyzed_users": result.analyzed_users,
                "analyzed_at": result.analyzed_at.isoformat(),
            }

            self.client.table("analysis_results").insert(analysis_data).execute()
            print("[Supabase] 保存分析结果成功")

            # 生成并保存 embeddings
            if generate_embeddings and self.openai_client:
                self._save_analysis_embeddings(result)

            return True
        except Exception as e:
            print(f"[错误] 保存分析结果失败: {e}")
            return False

    def _save_analysis_embeddings(self, result: AnalysisResult) -> None:
        """保存分析结果的 embeddings"""
        embedding_records = []

        # 保存总结的 embedding
        if result.summary:
            summary_embedding = self._generate_embedding(result.summary)
            if summary_embedding:
                embedding_records.append(
                    {
                        "content": result.summary,
                        "content_type": "summary",
                        "reference_id": result.analyzed_at.strftime("%Y-%m-%d_%H"),
                        "embedding": summary_embedding,
                        "metadata": {
                            "analyzed_at": result.analyzed_at.isoformat(),
                            "total_posts": result.total_posts,
                        },
                    }
                )

        # 保存聚类的 embeddings
        for cluster in result.clusters:
            cluster_text = f"{cluster.topic_name}: {cluster.topic_summary}"
            cluster_embedding = self._generate_embedding(cluster_text)
            if cluster_embedding:
                embedding_records.append(
                    {
                        "content": cluster_text,
                        "content_type": "cluster",
                        "reference_id": cluster.topic_id,
                        "embedding": cluster_embedding,
                        "metadata": {
                            "topic_name": cluster.topic_name,
                            "keywords": cluster.keywords,
                            "importance_score": cluster.importance_score,
                        },
                    }
                )

        if embedding_records:
            try:
                self.client.table("embeddings").insert(embedding_records).execute()
                print(f"[Supabase] 保存 {len(embedding_records)} 条分析 embeddings")
            except Exception as e:
                print(f"[警告] 保存分析 embeddings 失败: {e}")

    # ========== 语义搜索 ==========

    def semantic_search(
        self,
        query: str,
        content_type: str = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[dict]:
        """
        语义搜索

        Args:
            query: 搜索查询
            content_type: 内容类型筛选
            limit: 返回数量
            threshold: 相似度阈值

        Returns:
            搜索结果列表
        """
        query_embedding = self._generate_embedding(query)
        if not query_embedding:
            print("[警告] 无法生成查询 embedding")
            return []

        try:
            result = self.client.rpc(
                "match_embeddings",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": limit,
                },
            ).execute()

            results = result.data or []

            # 按内容类型筛选
            if content_type:
                results = [r for r in results if r.get("content_type") == content_type]

            return results
        except Exception as e:
            print(f"[错误] 语义搜索失败: {e}")
            return []

    # ========== 统计与管理 ==========

    def get_statistics(self) -> dict:
        """获取统计信息"""
        try:
            result = self.client.table("statistics").select("*").execute()
            if result.data:
                return result.data[0]
            return {}
        except Exception as e:
            print(f"[警告] 获取统计失败: {e}")
            return {}

    def cleanup_old_data(self, retention_days: int = 30) -> int:
        """清理旧数据"""
        cutoff_date = datetime.now(self.timezone)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - retention_days)

        try:
            result = (
                self.client.table("twitter_posts")
                .delete()
                .lt("created_at", cutoff_date.isoformat())
                .execute()
            )
            deleted_count = len(result.data)
            print(f"[Supabase] 清理 {deleted_count} 条旧数据")
            return deleted_count
        except Exception as e:
            print(f"[错误] 清理数据失败: {e}")
            return 0


# 导出单例
_supabase_instance: Optional[SupabaseStorage] = None


def get_supabase_storage() -> Optional[SupabaseStorage]:
    """获取 Supabase 存储实例"""
    global _supabase_instance

    if _supabase_instance is None:
        try:
            _supabase_instance = SupabaseStorage()
        except Exception as e:
            print(f"[警告] Supabase 初始化失败: {e}")
            return None

    return _supabase_instance


# 测试函数
def _test_supabase():
    """测试 Supabase 存储"""
    storage = SupabaseStorage()

    # 获取统计
    stats = storage.get_statistics()
    print(f"统计信息: {stats}")

    # 测试语义搜索
    results = storage.semantic_search("AI 人工智能", limit=5)
    print(f"搜索结果: {len(results)} 条")


if __name__ == "__main__":
    _test_supabase()
