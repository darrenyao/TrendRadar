"""
Post Analyzer - 使用LLM对Twitter帖子进行聚类分析

功能：
- 对帖子内容进行主题分类
- 聚类相似话题
- 生成摘要总结
"""

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pytz

# OpenAI兼容客户端
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[警告] openai 库未安装，请运行: pip install openai")

from .scraper import TwitterPost


@dataclass
class TopicCluster:
    """话题聚类结果"""

    topic_id: str
    topic_name: str
    topic_summary: str
    keywords: list[str]
    posts: list[TwitterPost]
    importance_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "topic_summary": self.topic_summary,
            "keywords": self.keywords,
            "posts": [p.to_dict() for p in self.posts],
            "importance_score": self.importance_score,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AnalysisResult:
    """分析结果"""

    clusters: list[TopicCluster]
    summary: str
    analyzed_at: datetime
    total_posts: int
    analyzed_users: list[str]

    def to_dict(self) -> dict:
        return {
            "clusters": [c.to_dict() for c in self.clusters],
            "summary": self.summary,
            "analyzed_at": self.analyzed_at.isoformat(),
            "total_posts": self.total_posts,
            "analyzed_users": self.analyzed_users,
        }


class PostAnalyzer:
    """
    帖子分析器 - 使用LLM进行聚类分析

    使用方法:
        analyzer = PostAnalyzer(
            llm_base_url="https://api.openai.com/v1",
            llm_api_key="your-api-key"
        )
        result = await analyzer.analyze_posts(posts)
    """

    # 聚类分析系统提示词
    CLUSTERING_SYSTEM_PROMPT = """你是一个专业的内容分析师，擅长对社交媒体帖子进行主题聚类和分析。

你的任务是：
1. 分析给定的Twitter帖子列表
2. 识别主要话题和主题
3. 将相似内容的帖子聚类到同一主题下
4. 为每个话题提供简洁的摘要

请确保：
- 话题分类清晰且有意义
- 摘要简洁但信息完整
- 关键词准确反映话题内容
- 重要性评分基于帖子数量和互动量"""

    # 摘要生成系统提示词
    SUMMARY_SYSTEM_PROMPT = """你是一个专业的内容总结专家。
请根据提供的话题聚类结果，生成一份简洁但全面的总结报告。

报告应包括：
1. 今日重点话题概览
2. 各话题的关键要点
3. 值得关注的趋势或观点

请使用清晰、专业的语言，便于快速阅读理解。"""

    def __init__(
        self,
        llm_base_url: str = None,
        llm_api_key: str = None,
        llm_model: str = "gpt-4o",
        timezone: str = "Asia/Shanghai",
    ):
        """
        初始化分析器

        Args:
            llm_base_url: LLM API base URL
            llm_api_key: LLM API密钥
            llm_model: LLM模型名称
            timezone: 时区
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai 库未安装，请运行: pip install openai")

        self.llm_base_url = llm_base_url or os.getenv(
            "TWITTER_LLM_BASE_URL", "https://api.openai.com/v1"
        )
        self.llm_api_key = llm_api_key or os.getenv("TWITTER_LLM_API_KEY", "")
        self.llm_model = llm_model or os.getenv("TWITTER_LLM_MODEL", "gpt-4o")
        self.timezone = pytz.timezone(timezone)

        self.client = OpenAI(
            base_url=self.llm_base_url,
            api_key=self.llm_api_key,
        )

    def analyze_posts(
        self, posts: list[TwitterPost], min_cluster_size: int = 2
    ) -> AnalysisResult:
        """
        对帖子进行聚类分析

        Args:
            posts: 帖子列表
            min_cluster_size: 最小聚类大小

        Returns:
            分析结果
        """
        if not posts:
            return AnalysisResult(
                clusters=[],
                summary="没有帖子可供分析。",
                analyzed_at=datetime.now(self.timezone),
                total_posts=0,
                analyzed_users=[],
            )

        # 提取用户列表
        users = list(set(p.author for p in posts))

        # 准备帖子数据供LLM分析
        posts_data = self._prepare_posts_for_analysis(posts)

        # 调用LLM进行聚类
        clusters = self._cluster_with_llm(posts_data, posts)

        # 过滤小聚类
        clusters = [c for c in clusters if len(c.posts) >= min_cluster_size]

        # 计算重要性评分
        for cluster in clusters:
            cluster.importance_score = self._calculate_importance(cluster)

        # 按重要性排序
        clusters.sort(key=lambda x: x.importance_score, reverse=True)

        # 生成总结
        summary = self._generate_summary(clusters)

        return AnalysisResult(
            clusters=clusters,
            summary=summary,
            analyzed_at=datetime.now(self.timezone),
            total_posts=len(posts),
            analyzed_users=users,
        )

    def _prepare_posts_for_analysis(self, posts: list[TwitterPost]) -> list[dict]:
        """准备帖子数据供分析"""
        return [
            {
                "id": idx,
                "author": p.author,
                "content": p.content,
                "likes": p.likes,
                "retweets": p.retweets,
                "replies": p.replies,
                "timestamp": p.timestamp.isoformat() if p.timestamp else "",
            }
            for idx, p in enumerate(posts)
        ]

    def _cluster_with_llm(
        self, posts_data: list[dict], original_posts: list[TwitterPost]
    ) -> list[TopicCluster]:
        """使用LLM进行聚类"""
        # 构建分析提示
        prompt = f"""请分析以下Twitter帖子并进行主题聚类：

帖子列表：
{json.dumps(posts_data, ensure_ascii=False, indent=2)}

请返回JSON格式的聚类结果：
{{
    "clusters": [
        {{
            "topic_name": "话题名称",
            "topic_summary": "话题摘要（1-2句话）",
            "keywords": ["关键词1", "关键词2", "关键词3"],
            "post_ids": [0, 2, 5]  // 属于此话题的帖子ID
        }}
    ]
}}

要求：
1. 每个帖子只能属于一个主题
2. 主题名称简洁明了（不超过10个字）
3. 关键词3-5个
4. 如果某帖子不属于任何主题，可以创建"其他"分类
"""

        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": self.CLUSTERING_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content

            # 解析JSON结果
            result = json.loads(result_text)
            clusters = []

            for idx, cluster_data in enumerate(result.get("clusters", [])):
                post_ids = cluster_data.get("post_ids", [])
                cluster_posts = [
                    original_posts[pid]
                    for pid in post_ids
                    if pid < len(original_posts)
                ]

                if cluster_posts:
                    cluster = TopicCluster(
                        topic_id=f"topic_{idx}",
                        topic_name=cluster_data.get("topic_name", f"话题{idx+1}"),
                        topic_summary=cluster_data.get("topic_summary", ""),
                        keywords=cluster_data.get("keywords", []),
                        posts=cluster_posts,
                        created_at=datetime.now(self.timezone),
                    )
                    clusters.append(cluster)

            return clusters

        except Exception as e:
            print(f"[错误] LLM聚类失败: {e}")
            # 回退到简单分组（按用户分组）
            return self._fallback_clustering(original_posts)

    def _fallback_clustering(self, posts: list[TwitterPost]) -> list[TopicCluster]:
        """回退聚类方法（按用户分组）"""
        user_posts = defaultdict(list)
        for post in posts:
            user_posts[post.author].append(post)

        clusters = []
        for idx, (user, user_posts_list) in enumerate(user_posts.items()):
            cluster = TopicCluster(
                topic_id=f"user_{idx}",
                topic_name=f"@{user} 的动态",
                topic_summary=f"来自 @{user} 的 {len(user_posts_list)} 条帖子",
                keywords=[user],
                posts=user_posts_list,
                created_at=datetime.now(self.timezone),
            )
            clusters.append(cluster)

        return clusters

    def _calculate_importance(self, cluster: TopicCluster) -> float:
        """计算话题重要性评分"""
        if not cluster.posts:
            return 0.0

        # 基于帖子数量
        post_count_score = min(len(cluster.posts) / 10, 1.0) * 30

        # 基于总互动量
        total_engagement = sum(
            p.likes + p.retweets * 2 + p.replies * 1.5 for p in cluster.posts
        )
        engagement_score = min(total_engagement / 10000, 1.0) * 50

        # 基于时效性（最新帖子时间）
        latest_post = max(cluster.posts, key=lambda p: p.timestamp)
        time_diff = (datetime.now(self.timezone) - latest_post.timestamp).total_seconds()
        recency_score = max(0, (86400 - time_diff) / 86400) * 20  # 24小时内递减

        return post_count_score + engagement_score + recency_score

    def _generate_summary(self, clusters: list[TopicCluster]) -> str:
        """生成总结报告"""
        if not clusters:
            return "暂无话题数据。"

        # 构建总结提示
        clusters_info = []
        for cluster in clusters[:10]:  # 最多10个话题
            clusters_info.append(
                {
                    "name": cluster.topic_name,
                    "summary": cluster.topic_summary,
                    "keywords": cluster.keywords,
                    "post_count": len(cluster.posts),
                    "importance": round(cluster.importance_score, 2),
                }
            )

        prompt = f"""请根据以下话题聚类信息，生成一份简洁的中文总结报告：

话题列表：
{json.dumps(clusters_info, ensure_ascii=False, indent=2)}

要求：
1. 总结控制在200字以内
2. 突出最重要的2-3个话题
3. 使用简洁的语言
4. 适合在消息推送中阅读
"""

        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": self.SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[错误] 生成总结失败: {e}")
            # 回退到简单总结
            top_topics = [c.topic_name for c in clusters[:3]]
            return f"今日主要话题：{'、'.join(top_topics)}。共分析 {sum(len(c.posts) for c in clusters)} 条帖子。"

    def generate_notification_message(
        self, result: AnalysisResult, time_period: str = "今日"
    ) -> str:
        """
        生成推送消息

        Args:
            result: 分析结果
            time_period: 时间段描述（早间/午间/晚间/今日）

        Returns:
            格式化的推送消息
        """
        if not result.clusters:
            return f"【Twitter {time_period}动态】\n\n暂无新动态。"

        lines = [f"【Twitter {time_period}动态】\n"]
        lines.append(f"共分析 {result.total_posts} 条帖子\n")
        lines.append("━" * 20 + "\n")

        # 添加总结
        lines.append(f"{result.summary}\n")
        lines.append("━" * 20 + "\n")

        # 添加话题详情（最多5个）
        for idx, cluster in enumerate(result.clusters[:5], 1):
            lines.append(f"\n📌 {cluster.topic_name}")
            lines.append(f"   {cluster.topic_summary}")
            lines.append(f"   关键词：{', '.join(cluster.keywords[:3])}")
            lines.append(f"   帖子数：{len(cluster.posts)}")

            # 显示热门帖子
            top_post = max(
                cluster.posts, key=lambda p: p.likes + p.retweets, default=None
            )
            if top_post:
                content_preview = (
                    top_post.content[:50] + "..."
                    if len(top_post.content) > 50
                    else top_post.content
                )
                lines.append(f"   热门帖子：{content_preview}")

        lines.append("\n" + "━" * 20)
        lines.append(f"\n分析时间：{result.analyzed_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"关注用户：{', '.join(result.analyzed_users[:5])}")

        return "\n".join(lines)


# 测试函数
def _test_analyzer():
    """测试分析功能"""
    # 创建测试帖子
    from datetime import timedelta

    test_posts = [
        TwitterPost(
            post_id="1",
            author="testuser",
            author_handle="@testuser",
            content="AI技术正在改变世界，GPT-4的能力令人惊叹",
            timestamp=datetime.now(pytz.timezone("Asia/Shanghai")),
            likes=1000,
            retweets=200,
        ),
        TwitterPost(
            post_id="2",
            author="testuser",
            author_handle="@testuser",
            content="最新的AI研究表明，大语言模型正在变得越来越强大",
            timestamp=datetime.now(pytz.timezone("Asia/Shanghai"))
            - timedelta(hours=2),
            likes=500,
            retweets=100,
        ),
        TwitterPost(
            post_id="3",
            author="anotheruser",
            author_handle="@anotheruser",
            content="特斯拉股价今日大涨10%，市场看好其自动驾驶前景",
            timestamp=datetime.now(pytz.timezone("Asia/Shanghai"))
            - timedelta(hours=1),
            likes=2000,
            retweets=500,
        ),
    ]

    analyzer = PostAnalyzer()
    result = analyzer.analyze_posts(test_posts)

    print("分析结果：")
    print(analyzer.generate_notification_message(result))


if __name__ == "__main__":
    _test_analyzer()
