"""
配置管理器 - 整合用户配置并导出为 TrendRadar 可用的格式
"""

from typing import Dict, List, Optional
from models import Database, UserManager, KeywordManager, NotificationConfigManager, PushConfigManager
import yaml
import os


class ConfigManager:
    """配置管理器 - 连接数据库和主程序"""

    def __init__(self, db_path: str = "config/users.db"):
        self.db = Database(db_path)
        self.user_mgr = UserManager(self.db)
        self.keyword_mgr = KeywordManager(self.db)
        self.notif_mgr = NotificationConfigManager(self.db)
        self.push_mgr = PushConfigManager(self.db)

    def get_user_full_config(self, user_id: str) -> Optional[Dict]:
        """
        获取用户的完整配置

        Returns:
            {
                "user": {...},
                "keywords": [...],
                "notification": {...},
                "push": {...}
            }
        """
        user = self.user_mgr.get_user(user_id)
        if not user:
            return None

        return {
            "user": user,
            "keywords": self.keyword_mgr.get_keywords(user_id),
            "notification": self.notif_mgr.get_config(user_id),
            "push": self.push_mgr.get_config(user_id),
        }

    def get_all_users_configs(self, enabled_only: bool = True) -> List[Dict]:
        """
        获取所有用户的配置

        Args:
            enabled_only: 是否只返回启用的用户

        Returns:
            用户配置列表
        """
        users = self.user_mgr.list_users(enabled_only=enabled_only)
        configs = []

        for user in users:
            user_id = user["user_id"]
            config = {
                "user": user,
                "keywords": self.keyword_mgr.get_keywords(user_id),
                "notification": self.notif_mgr.get_config(user_id),
                "push": self.push_mgr.get_config(user_id),
            }
            configs.append(config)

        return configs

    def export_user_config_to_yaml(self, user_id: str, output_dir: str = "config/users") -> Optional[str]:
        """
        将用户配置导出为 YAML 文件

        Args:
            user_id: 用户ID
            output_dir: 输出目录

        Returns:
            导出的文件路径，失败返回 None
        """
        config = self.get_user_full_config(user_id)
        if not config:
            return None

        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"{user_id}.yaml")

        # 转换为 TrendRadar 可用的格式
        trendradar_config = self._convert_to_trendradar_format(config)

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(trendradar_config, f, allow_unicode=True, default_flow_style=False)

        return filepath

    def export_all_configs(self, output_dir: str = "config/users") -> int:
        """
        导出所有启用用户的配置

        Returns:
            导出的文件数量
        """
        users = self.user_mgr.list_users(enabled_only=True)
        count = 0

        for user in users:
            if self.export_user_config_to_yaml(user["user_id"], output_dir):
                count += 1

        return count

    def _convert_to_trendradar_format(self, config: Dict) -> Dict:
        """
        将数据库配置转换为 TrendRadar main.py 可以识别的格式
        """
        user = config["user"]
        notif = config["notification"]
        push = config["push"]

        return {
            "user_info": {
                "user_id": user["user_id"],
                "name": user["name"],
                "enabled": bool(user["enabled"]),
            },
            "keywords": config["keywords"],
            "report": {
                "mode": push.get("mode", "daily"),
                "rank_threshold": push.get("rank_threshold", 5),
            },
            "notification": {
                "enable_notification": True,
                "webhooks": {
                    "feishu_url": notif.get("feishu_url", ""),
                    "dingtalk_url": notif.get("dingtalk_url", ""),
                    "wework_url": notif.get("wework_url", ""),
                    "telegram_bot_token": notif.get("telegram_bot_token", ""),
                    "telegram_chat_id": notif.get("telegram_chat_id", ""),
                    "email_from": notif.get("email_from", ""),
                    "email_password": notif.get("email_password", ""),
                    "email_to": notif.get("email_to", ""),
                    "email_smtp_server": notif.get("email_smtp_server", ""),
                    "email_smtp_port": notif.get("email_smtp_port", ""),
                    "ntfy_server_url": notif.get("ntfy_server_url", "https://ntfy.sh"),
                    "ntfy_topic": notif.get("ntfy_topic", ""),
                    "ntfy_token": notif.get("ntfy_token", ""),
                },
                "push_window": {
                    "enabled": bool(push.get("push_window_enabled", False)),
                    "time_range": {
                        "start": push.get("push_window_start", "20:00"),
                        "end": push.get("push_window_end", "22:00"),
                    },
                    "once_per_day": bool(push.get("push_window_once_per_day", True)),
                },
            },
        }

    def import_keywords_from_file(self, user_id: str, filepath: str) -> int:
        """
        从文件导入关键词（每行一个）

        Returns:
            导入的关键词数量
        """
        if not os.path.exists(filepath):
            return 0

        with open(filepath, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]

        return self.keyword_mgr.add_keywords_batch(user_id, keywords)

    def validate_notification_config(self, config: Dict) -> List[str]:
        """
        验证通知配置

        Returns:
            错误列表（空列表表示验证通过）
        """
        errors = []

        # 检查至少配置了一种通知方式
        has_config = False
        notification_fields = [
            "feishu_url",
            "dingtalk_url",
            "wework_url",
            "telegram_bot_token",
            "email_from",
            "ntfy_topic",
        ]

        for field in notification_fields:
            if config.get(field):
                has_config = True
                break

        if not has_config:
            errors.append("至少需要配置一种通知方式")

        # Telegram 需要同时配置 token 和 chat_id
        if config.get("telegram_bot_token") and not config.get("telegram_chat_id"):
            errors.append("Telegram 需要同时配置 Bot Token 和 Chat ID")

        if config.get("telegram_chat_id") and not config.get("telegram_bot_token"):
            errors.append("Telegram 需要同时配置 Bot Token 和 Chat ID")

        # 邮件需要配置发件人、密码和收件人
        email_fields = ["email_from", "email_password", "email_to"]
        email_config_count = sum(1 for f in email_fields if config.get(f))
        if 0 < email_config_count < 3:
            errors.append("邮件通知需要同时配置发件人、密码和收件人")

        return errors
