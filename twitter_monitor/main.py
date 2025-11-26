"""
Twitter Monitor - 主入口模块

功能：
- 整合抓取、分析、存储和调度模块
- 提供统一的运行接口
- 集成到现有TrendRadar通知系统
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz
import yaml

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from .scraper import TwitterScraper, TwitterPost
from .analyzer import PostAnalyzer, AnalysisResult
from .storage import TwitterStorage
from .scheduler import TwitterScheduler, PushPeriod


class TwitterMonitor:
    """
    Twitter监控器 - 主控制类

    整合所有功能模块，提供：
    - 抓取指定用户的Twitter帖子
    - LLM聚类分析
    - 早中晚定时推送

    使用方法:
        monitor = TwitterMonitor()
        await monitor.run()
    """

    def __init__(
        self,
        config_path: str = None,
        timezone: str = "Asia/Shanghai",
    ):
        """
        初始化监控器

        Args:
            config_path: 配置文件路径
            timezone: 时区
        """
        self.timezone = pytz.timezone(timezone)
        self.config = self._load_config(config_path)

        # 初始化各模块
        self.storage = TwitterStorage(
            base_dir=self.config.get("storage_dir", "output/twitter"),
            timezone=timezone,
            retention_days=self.config.get("retention_days", 30),
        )

        self.scheduler = TwitterScheduler(
            timezone=timezone,
            storage=self.storage,
        )

        self.scraper = None  # 延迟初始化
        self.analyzer = None  # 延迟初始化

        # 通知发送函数（从主程序导入）
        self._notification_sender = None

    def _load_config(self, config_path: str = None) -> dict:
        """加载配置"""
        # 默认配置
        config = {
            "enabled": True,
            "users": [],  # 要监控的用户列表
            "max_posts_per_user": 20,
            "storage_dir": "output/twitter",
            "retention_days": 30,
            "push_schedule": {
                "morning": "08:00",
                "noon": "12:00",
                "evening": "20:00",
            },
            "llm": {
                "base_url": os.getenv("TWITTER_LLM_BASE_URL", "https://api.openai.com/v1"),
                "api_key": os.getenv("TWITTER_LLM_API_KEY", ""),
                "model": os.getenv("TWITTER_LLM_MODEL", "gpt-4o"),
            },
        }

        # 尝试从配置文件加载
        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config and "twitter_monitor" in file_config:
                    config.update(file_config["twitter_monitor"])
        else:
            # 尝试从默认位置加载
            default_config = PROJECT_ROOT / "config" / "config.yaml"
            if default_config.exists():
                with open(default_config, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f)
                    if file_config and "twitter_monitor" in file_config:
                        config.update(file_config["twitter_monitor"])

        # 从环境变量覆盖
        if os.getenv("TWITTER_MONITOR_ENABLED"):
            config["enabled"] = os.getenv("TWITTER_MONITOR_ENABLED").lower() == "true"

        if os.getenv("TWITTER_MONITOR_USERS"):
            config["users"] = [
                u.strip()
                for u in os.getenv("TWITTER_MONITOR_USERS", "").split(",")
                if u.strip()
            ]

        return config

    def _init_scraper(self) -> TwitterScraper:
        """初始化抓取器"""
        if self.scraper is None:
            llm_config = self.config.get("llm", {})
            self.scraper = TwitterScraper(
                llm_base_url=llm_config.get("base_url"),
                llm_api_key=llm_config.get("api_key"),
                llm_model=llm_config.get("model"),
                headless=True,
                timezone=str(self.timezone),
            )
        return self.scraper

    def _init_analyzer(self) -> PostAnalyzer:
        """初始化分析器"""
        if self.analyzer is None:
            llm_config = self.config.get("llm", {})
            self.analyzer = PostAnalyzer(
                llm_base_url=llm_config.get("base_url"),
                llm_api_key=llm_config.get("api_key"),
                llm_model=llm_config.get("model"),
                timezone=str(self.timezone),
            )
        return self.analyzer

    def set_notification_sender(self, sender_func) -> None:
        """
        设置通知发送函数

        Args:
            sender_func: 发送通知的函数，签名: func(message: str) -> bool
        """
        self._notification_sender = sender_func

    async def scrape_all_users(self) -> dict[str, list[TwitterPost]]:
        """
        抓取所有配置用户的帖子

        Returns:
            用户名到帖子列表的映射
        """
        users = self.config.get("users", [])
        if not users:
            print("[警告] 未配置要监控的Twitter用户")
            return {}

        print(f"[Twitter] 开始抓取 {len(users)} 个用户的帖子...")

        scraper = self._init_scraper()
        max_posts = self.config.get("max_posts_per_user", 20)

        results = await scraper.scrape_multiple_users(users, max_posts)

        # 保存到存储
        for username, posts in results.items():
            if posts:
                self.storage.save_posts(username, posts)
                print(f"[Twitter] 保存 @{username} 的 {len(posts)} 条帖子")

        return results

    def analyze_posts(
        self, posts: list[TwitterPost] = None
    ) -> AnalysisResult:
        """
        分析帖子

        Args:
            posts: 帖子列表（为空则加载今日所有帖子）

        Returns:
            分析结果
        """
        if posts is None:
            posts = self.storage.load_all_posts()

        if not posts:
            print("[Twitter] 没有可分析的帖子")
            return AnalysisResult(
                clusters=[],
                summary="暂无数据",
                analyzed_at=datetime.now(self.timezone),
                total_posts=0,
                analyzed_users=[],
            )

        print(f"[Twitter] 开始分析 {len(posts)} 条帖子...")

        analyzer = self._init_analyzer()
        result = analyzer.analyze_posts(posts)

        print(f"[Twitter] 分析完成，识别出 {len(result.clusters)} 个话题")

        return result

    def send_notification(self, message: str) -> bool:
        """
        发送通知

        Args:
            message: 通知消息

        Returns:
            是否发送成功
        """
        if self._notification_sender:
            return self._notification_sender(message)

        # 如果没有设置发送函数，尝试导入主程序的通知功能
        try:
            from main import (
                send_to_dingtalk,
                send_to_feishu,
                send_to_wework,
                send_to_telegram,
                send_to_email,
                send_to_ntfy,
            )

            success = False

            # 尝试发送到所有配置的渠道
            if os.getenv("DINGTALK_WEBHOOK_URL"):
                success = send_to_dingtalk(message) or success

            if os.getenv("FEISHU_WEBHOOK_URL"):
                success = send_to_feishu(message) or success

            if os.getenv("WEWORK_WEBHOOK_URL"):
                success = send_to_wework(message) or success

            if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
                success = send_to_telegram(message) or success

            if os.getenv("EMAIL_FROM") and os.getenv("EMAIL_TO"):
                success = send_to_email("Twitter 动态", message) or success

            if os.getenv("NTFY_TOPIC"):
                success = send_to_ntfy(message) or success

            return success

        except ImportError:
            print("[警告] 无法导入通知模块，消息只输出到控制台")
            print(message)
            return True

    async def run_scheduled_push(self) -> bool:
        """
        执行定时推送

        检查当前时段并执行相应的推送任务

        Returns:
            是否执行了推送
        """
        period = self.scheduler.get_current_period()

        if not period:
            print("[Twitter] 当前不在推送时段")
            return False

        if not self.scheduler.should_push(period):
            print(f"[Twitter] {period.value} 时段已推送")
            return False

        print(f"[Twitter] 开始执行 {period.value} 推送...")

        # 抓取最新帖子
        await self.scrape_all_users()

        # 分析帖子
        result = self.analyze_posts()

        # 保存分析结果
        self.storage.save_analysis(result, period.value)

        # 生成推送消息
        period_name = self.scheduler.get_period_display_name(period)
        analyzer = self._init_analyzer()
        message = analyzer.generate_notification_message(result, period_name)

        # 发送通知
        success = self.send_notification(message)

        # 标记已推送
        self.scheduler.mark_pushed(period, success)

        print(f"[Twitter] {period.value} 推送{'成功' if success else '失败'}")

        return success

    async def run_once(self) -> AnalysisResult:
        """
        执行一次完整的抓取和分析流程

        Returns:
            分析结果
        """
        if not self.config.get("enabled", True):
            print("[Twitter] 监控功能已禁用")
            return None

        # 抓取
        await self.scrape_all_users()

        # 分析
        result = self.analyze_posts()

        # 保存
        self.storage.save_analysis(result, "manual")

        return result

    async def run(self) -> None:
        """
        运行监控器

        主循环：检查是否到达推送时间并执行任务
        """
        if not self.config.get("enabled", True):
            print("[Twitter] 监控功能已禁用")
            return

        print("[Twitter] 监控器启动")
        print(f"[Twitter] 监控用户: {', '.join(self.config.get('users', []))}")

        status = self.scheduler.get_schedule_status()
        print(f"[Twitter] 推送时间: 早{status['schedule']['morning']} / "
              f"午{status['schedule']['noon']} / 晚{status['schedule']['evening']}")

        # 首次运行检查
        await self.run_scheduled_push()

        # 清理过期数据
        cleaned = self.storage.cleanup_old_data()
        if cleaned:
            print(f"[Twitter] 清理了 {cleaned} 个过期数据目录")

    def get_status(self) -> dict:
        """
        获取监控器状态

        Returns:
            状态信息
        """
        return {
            "enabled": self.config.get("enabled", True),
            "users": self.config.get("users", []),
            "schedule": self.scheduler.get_schedule_status(),
            "storage": self.storage.get_statistics(),
        }


# ============================================
# 独立运行入口
# ============================================

async def main():
    """主函数 - 独立运行入口"""
    print("=" * 50)
    print("Twitter Monitor - Twitter帖子抓取与聚类分析")
    print("=" * 50)

    # 检查必要配置
    if not os.getenv("TWITTER_LLM_API_KEY"):
        print("\n[错误] 请设置 TWITTER_LLM_API_KEY 环境变量")
        print("示例: export TWITTER_LLM_API_KEY=your-api-key")
        return

    users = os.getenv("TWITTER_MONITOR_USERS", "").split(",")
    users = [u.strip() for u in users if u.strip()]

    if not users:
        print("\n[错误] 请设置 TWITTER_MONITOR_USERS 环境变量")
        print("示例: export TWITTER_MONITOR_USERS=elonmusk,OpenAI")
        return

    print(f"\n监控用户: {', '.join(users)}")

    # 创建监控器并运行
    monitor = TwitterMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
