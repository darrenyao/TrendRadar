"""
Twitter Storage - 数据存储模块

功能：
- 存储抓取的帖子数据
- 存储分析结果
- 管理推送记录
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytz

from .scraper import TwitterPost
from .analyzer import AnalysisResult, TopicCluster


class TwitterStorage:
    """
    Twitter数据存储管理器

    数据目录结构：
    output/twitter/
    ├── posts/                    # 原始帖子数据
    │   └── 2025-11-26/
    │       ├── elonmusk.json
    │       └── testuser.json
    ├── analysis/                 # 分析结果
    │   └── 2025-11-26/
    │       ├── morning.json
    │       ├── noon.json
    │       └── evening.json
    └── push_records/             # 推送记录
        └── 2025-11-26.json
    """

    def __init__(
        self,
        base_dir: str = None,
        timezone: str = "Asia/Shanghai",
        retention_days: int = 30,
    ):
        """
        初始化存储管理器

        Args:
            base_dir: 基础存储目录
            timezone: 时区
            retention_days: 数据保留天数
        """
        self.base_dir = Path(base_dir or "output/twitter")
        self.timezone = pytz.timezone(timezone)
        self.retention_days = retention_days

        # 创建目录结构
        self.posts_dir = self.base_dir / "posts"
        self.analysis_dir = self.base_dir / "analysis"
        self.push_records_dir = self.base_dir / "push_records"

        for dir_path in [self.posts_dir, self.analysis_dir, self.push_records_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _get_date_str(self, dt: datetime = None) -> str:
        """获取日期字符串"""
        if dt is None:
            dt = datetime.now(self.timezone)
        return dt.strftime("%Y-%m-%d")

    def _get_today_dir(self, base_path: Path) -> Path:
        """获取今日数据目录"""
        today_dir = base_path / self._get_date_str()
        today_dir.mkdir(parents=True, exist_ok=True)
        return today_dir

    # ========== 帖子存储 ==========

    def save_posts(self, username: str, posts: list[TwitterPost]) -> str:
        """
        保存用户帖子

        Args:
            username: 用户名
            posts: 帖子列表

        Returns:
            保存的文件路径
        """
        today_dir = self._get_today_dir(self.posts_dir)
        file_path = today_dir / f"{username}.json"

        # 读取已有数据并合并
        existing_posts = self.load_posts(username)
        existing_ids = {p.post_id for p in existing_posts}

        # 添加新帖子
        new_posts = [p for p in posts if p.post_id not in existing_ids]
        all_posts = existing_posts + new_posts

        # 保存
        data = {
            "username": username,
            "updated_at": datetime.now(self.timezone).isoformat(),
            "posts": [p.to_dict() for p in all_posts],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(file_path)

    def load_posts(
        self, username: str, date_str: str = None
    ) -> list[TwitterPost]:
        """
        加载用户帖子

        Args:
            username: 用户名
            date_str: 日期字符串（默认今日）

        Returns:
            帖子列表
        """
        date_str = date_str or self._get_date_str()
        file_path = self.posts_dir / date_str / f"{username}.json"

        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return [TwitterPost.from_dict(p) for p in data.get("posts", [])]
        except Exception as e:
            print(f"[错误] 加载帖子失败: {e}")
            return []

    def load_all_posts(self, date_str: str = None) -> list[TwitterPost]:
        """
        加载某日所有用户的帖子

        Args:
            date_str: 日期字符串（默认今日）

        Returns:
            所有帖子列表
        """
        date_str = date_str or self._get_date_str()
        date_dir = self.posts_dir / date_str

        if not date_dir.exists():
            return []

        all_posts = []
        for file_path in date_dir.glob("*.json"):
            username = file_path.stem
            posts = self.load_posts(username, date_str)
            all_posts.extend(posts)

        return all_posts

    def get_new_posts_since(
        self, since_time: datetime, usernames: list[str] = None
    ) -> list[TwitterPost]:
        """
        获取指定时间之后的新帖子

        Args:
            since_time: 起始时间
            usernames: 用户名列表（为空则获取所有）

        Returns:
            新帖子列表
        """
        all_posts = self.load_all_posts()

        if usernames:
            all_posts = [p for p in all_posts if p.author in usernames]

        return [p for p in all_posts if p.timestamp > since_time]

    # ========== 分析结果存储 ==========

    def save_analysis(
        self, result: AnalysisResult, period: str = "daily"
    ) -> str:
        """
        保存分析结果

        Args:
            result: 分析结果
            period: 时段标识（morning/noon/evening/daily）

        Returns:
            保存的文件路径
        """
        today_dir = self._get_today_dir(self.analysis_dir)
        file_path = today_dir / f"{period}.json"

        data = result.to_dict()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(file_path)

    def load_analysis(
        self, period: str = "daily", date_str: str = None
    ) -> Optional[AnalysisResult]:
        """
        加载分析结果

        Args:
            period: 时段标识
            date_str: 日期字符串

        Returns:
            分析结果
        """
        date_str = date_str or self._get_date_str()
        file_path = self.analysis_dir / date_str / f"{period}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 重建分析结果
            clusters = []
            for cluster_data in data.get("clusters", []):
                posts = [
                    TwitterPost.from_dict(p) for p in cluster_data.get("posts", [])
                ]
                cluster = TopicCluster(
                    topic_id=cluster_data.get("topic_id", ""),
                    topic_name=cluster_data.get("topic_name", ""),
                    topic_summary=cluster_data.get("topic_summary", ""),
                    keywords=cluster_data.get("keywords", []),
                    posts=posts,
                    importance_score=cluster_data.get("importance_score", 0),
                    created_at=datetime.fromisoformat(
                        cluster_data.get("created_at", datetime.now().isoformat())
                    ),
                )
                clusters.append(cluster)

            return AnalysisResult(
                clusters=clusters,
                summary=data.get("summary", ""),
                analyzed_at=datetime.fromisoformat(data.get("analyzed_at", "")),
                total_posts=data.get("total_posts", 0),
                analyzed_users=data.get("analyzed_users", []),
            )
        except Exception as e:
            print(f"[错误] 加载分析结果失败: {e}")
            return None

    # ========== 推送记录管理 ==========

    def record_push(self, period: str, success: bool = True) -> None:
        """
        记录推送

        Args:
            period: 时段标识
            success: 是否成功
        """
        date_str = self._get_date_str()
        file_path = self.push_records_dir / f"{date_str}.json"

        # 读取已有记录
        records = {}
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                pass

        # 添加新记录
        records[period] = {
            "pushed_at": datetime.now(self.timezone).isoformat(),
            "success": success,
        }

        # 保存
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def has_pushed_today(self, period: str) -> bool:
        """
        检查今日是否已推送

        Args:
            period: 时段标识

        Returns:
            是否已推送
        """
        date_str = self._get_date_str()
        file_path = self.push_records_dir / f"{date_str}.json"

        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                records = json.load(f)

            record = records.get(period)
            if record and record.get("success"):
                return True
        except Exception:
            pass

        return False

    # ========== 数据清理 ==========

    def cleanup_old_data(self) -> int:
        """
        清理过期数据

        Returns:
            清理的目录数量
        """
        cutoff_date = datetime.now(self.timezone) - timedelta(days=self.retention_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        cleaned_count = 0

        for base_path in [self.posts_dir, self.analysis_dir]:
            if not base_path.exists():
                continue

            for date_dir in base_path.iterdir():
                if date_dir.is_dir() and date_dir.name < cutoff_str:
                    try:
                        # 删除目录中的所有文件
                        for file in date_dir.glob("*"):
                            file.unlink()
                        date_dir.rmdir()
                        cleaned_count += 1
                        print(f"[清理] 已删除过期数据: {date_dir}")
                    except Exception as e:
                        print(f"[错误] 清理失败: {date_dir}, {e}")

        # 清理推送记录
        for record_file in self.push_records_dir.glob("*.json"):
            if record_file.stem < cutoff_str:
                try:
                    record_file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    print(f"[错误] 清理推送记录失败: {record_file}, {e}")

        return cleaned_count

    def get_statistics(self) -> dict:
        """
        获取存储统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total_days": 0,
            "total_posts": 0,
            "total_analysis": 0,
            "storage_size_mb": 0,
        }

        # 统计帖子数据
        if self.posts_dir.exists():
            for date_dir in self.posts_dir.iterdir():
                if date_dir.is_dir():
                    stats["total_days"] += 1
                    for file in date_dir.glob("*.json"):
                        stats["storage_size_mb"] += file.stat().st_size / 1024 / 1024
                        try:
                            with open(file, "r") as f:
                                data = json.load(f)
                            stats["total_posts"] += len(data.get("posts", []))
                        except Exception:
                            pass

        # 统计分析结果
        if self.analysis_dir.exists():
            for date_dir in self.analysis_dir.iterdir():
                if date_dir.is_dir():
                    stats["total_analysis"] += len(list(date_dir.glob("*.json")))

        stats["storage_size_mb"] = round(stats["storage_size_mb"], 2)

        return stats


# 测试函数
def _test_storage():
    """测试存储功能"""
    storage = TwitterStorage(base_dir="output/twitter_test")

    # 创建测试帖子
    test_posts = [
        TwitterPost(
            post_id="test_1",
            author="testuser",
            author_handle="@testuser",
            content="这是一条测试帖子",
            timestamp=datetime.now(pytz.timezone("Asia/Shanghai")),
            likes=100,
            retweets=20,
        ),
    ]

    # 保存帖子
    path = storage.save_posts("testuser", test_posts)
    print(f"保存帖子到: {path}")

    # 加载帖子
    loaded_posts = storage.load_posts("testuser")
    print(f"加载到 {len(loaded_posts)} 条帖子")

    # 获取统计
    stats = storage.get_statistics()
    print(f"存储统计: {stats}")


if __name__ == "__main__":
    _test_storage()
