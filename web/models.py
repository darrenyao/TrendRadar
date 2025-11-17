"""
TrendRadar 多用户配置数据模型
支持 SQLite 数据库存储
"""

import sqlite3
import json
import secrets
from typing import List, Dict, Optional
from datetime import datetime
import os


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str = "config/users.db"):
        self.db_path = db_path
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以像字典一样访问
        return conn

    def init_db(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 用户表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 关键词表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                keyword TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, keyword)
            )
        """
        )

        # 通知配置表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                feishu_url TEXT,
                dingtalk_url TEXT,
                wework_url TEXT,
                telegram_bot_token TEXT,
                telegram_chat_id TEXT,
                email_from TEXT,
                email_password TEXT,
                email_to TEXT,
                email_smtp_server TEXT,
                email_smtp_port TEXT,
                ntfy_server_url TEXT DEFAULT 'https://ntfy.sh',
                ntfy_topic TEXT,
                ntfy_token TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """
        )

        # 推送配置表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS push_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                mode TEXT DEFAULT 'daily',
                rank_threshold INTEGER DEFAULT 5,
                push_window_enabled BOOLEAN DEFAULT 0,
                push_window_start TEXT DEFAULT '20:00',
                push_window_end TEXT DEFAULT '22:00',
                push_window_once_per_day BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """
        )

        conn.commit()
        conn.close()


class UserManager:
    """用户管理类"""

    def __init__(self, db: Database):
        self.db = db

    def create_user(self, name: str, user_id: Optional[str] = None) -> Dict:
        """
        创建新用户

        Args:
            name: 用户名称
            user_id: 用户ID（可选，不提供则自动生成）

        Returns:
            用户信息字典
        """
        if not user_id:
            user_id = f"user_{secrets.token_hex(8)}"

        token = secrets.token_urlsafe(32)

        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (user_id, name, token)
                VALUES (?, ?, ?)
            """,
                (user_id, name, token),
            )

            # 创建默认的通知配置
            cursor.execute(
                """
                INSERT INTO notification_config (user_id)
                VALUES (?)
            """,
                (user_id,),
            )

            # 创建默认的推送配置
            cursor.execute(
                """
                INSERT INTO push_config (user_id)
                VALUES (?)
            """,
                (user_id,),
            )

            conn.commit()

            return {
                "user_id": user_id,
                "name": name,
                "token": token,
                "enabled": True,
                "created_at": datetime.now().isoformat(),
            }

        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise ValueError(f"用户创建失败：{e}")
        finally:
            conn.close()

    def get_user(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_user_by_token(self, token: str) -> Optional[Dict]:
        """通过 token 获取用户信息"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users WHERE token = ?
        """,
            (token,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def list_users(self, enabled_only: bool = False) -> List[Dict]:
        """列出所有用户"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if enabled_only:
            cursor.execute(
                """
                SELECT * FROM users WHERE enabled = 1 ORDER BY created_at DESC
            """
            )
        else:
            cursor.execute(
                """
                SELECT * FROM users ORDER BY created_at DESC
            """
            )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_user(self, user_id: str, name: Optional[str] = None, enabled: Optional[bool] = None) -> bool:
        """更新用户信息"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)

        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)

        cursor.execute(
            f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE user_id = ?
        """,
            params,
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0

    def delete_user(self, user_id: str) -> bool:
        """删除用户（级联删除关键词和配置）"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM users WHERE user_id = ?
        """,
            (user_id,),
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0

    def regenerate_token(self, user_id: str) -> Optional[str]:
        """重新生成用户 token"""
        new_token = secrets.token_urlsafe(32)

        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET token = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """,
            (new_token, user_id),
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return new_token if affected > 0 else None


class KeywordManager:
    """关键词管理类"""

    def __init__(self, db: Database):
        self.db = db

    def add_keyword(self, user_id: str, keyword: str) -> bool:
        """为用户添加关键词"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO keywords (user_id, keyword)
                VALUES (?, ?)
            """,
                (user_id, keyword.strip()),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # 关键词已存在
            return False
        finally:
            conn.close()

    def add_keywords_batch(self, user_id: str, keywords: List[str]) -> int:
        """批量添加关键词"""
        count = 0
        for keyword in keywords:
            if keyword.strip() and self.add_keyword(user_id, keyword.strip()):
                count += 1
        return count

    def get_keywords(self, user_id: str) -> List[str]:
        """获取用户的所有关键词"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT keyword FROM keywords
            WHERE user_id = ?
            ORDER BY created_at ASC
        """,
            (user_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [row["keyword"] for row in rows]

    def remove_keyword(self, user_id: str, keyword: str) -> bool:
        """删除关键词"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM keywords
            WHERE user_id = ? AND keyword = ?
        """,
            (user_id, keyword),
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0

    def clear_keywords(self, user_id: str) -> int:
        """清空用户的所有关键词"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM keywords WHERE user_id = ?
        """,
            (user_id,),
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected


class NotificationConfigManager:
    """通知配置管理类"""

    def __init__(self, db: Database):
        self.db = db

    def get_config(self, user_id: str) -> Dict:
        """获取用户的通知配置"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM notification_config WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            config = dict(row)
            # 移除 ID 字段
            config.pop("id", None)
            config.pop("user_id", None)
            return config

        return {}

    def update_config(self, user_id: str, config: Dict) -> bool:
        """更新用户的通知配置"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # 允许更新的字段
        allowed_fields = [
            "feishu_url",
            "dingtalk_url",
            "wework_url",
            "telegram_bot_token",
            "telegram_chat_id",
            "email_from",
            "email_password",
            "email_to",
            "email_smtp_server",
            "email_smtp_port",
            "ntfy_server_url",
            "ntfy_topic",
            "ntfy_token",
        ]

        updates = []
        params = []

        for field in allowed_fields:
            if field in config:
                updates.append(f"{field} = ?")
                params.append(config[field])

        if not updates:
            return False

        params.append(user_id)

        cursor.execute(
            f"""
            UPDATE notification_config
            SET {', '.join(updates)}
            WHERE user_id = ?
        """,
            params,
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0


class PushConfigManager:
    """推送配置管理类"""

    def __init__(self, db: Database):
        self.db = db

    def get_config(self, user_id: str) -> Dict:
        """获取用户的推送配置"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM push_config WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            config = dict(row)
            # 移除 ID 字段
            config.pop("id", None)
            config.pop("user_id", None)
            return config

        return {}

    def update_config(self, user_id: str, config: Dict) -> bool:
        """更新用户的推送配置"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        allowed_fields = [
            "mode",
            "rank_threshold",
            "push_window_enabled",
            "push_window_start",
            "push_window_end",
            "push_window_once_per_day",
        ]

        updates = []
        params = []

        for field in allowed_fields:
            if field in config:
                updates.append(f"{field} = ?")
                params.append(config[field])

        if not updates:
            return False

        params.append(user_id)

        cursor.execute(
            f"""
            UPDATE push_config
            SET {', '.join(updates)}
            WHERE user_id = ?
        """,
            params,
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0
