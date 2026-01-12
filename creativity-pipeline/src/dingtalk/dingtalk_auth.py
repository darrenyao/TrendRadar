"""
钉钉认证模块（精简版）
"""
import os
import time
import logging
from typing import Optional

from alibabacloud_dingtalk.oauth2_1_0.client import Client as DingTalkOAuth2Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalk_oauth_models

logger = logging.getLogger(__name__)


class DingtalkAuth:
    def __init__(self):
        self._client_id = os.environ.get("DINGTALK_CLIENT_ID", "")
        self._client_secret = os.environ.get("DINGTALK_CLIENT_SECRET", "")
        self.app_access_token: Optional[str] = None
        self.app_expires_in: int = 0
        self.app_last_refresh_time: float = 0
        self.client = self._create_client()
        logger.info(f"DingtalkAuth 初始化完成")

    def _create_client(self) -> DingTalkOAuth2Client:
        config = open_api_models.Config()
        config.protocol = 'https'
        config.region_id = 'central'
        return DingTalkOAuth2Client(config)

    def get_app_access_token(self) -> str:
        if self.app_access_token and self._is_app_token_valid():
            return self.app_access_token
        return self._refresh_app_token()

    def _is_app_token_valid(self) -> bool:
        if not self.app_access_token or not self.app_expires_in or not self.app_last_refresh_time:
            return False
        current_time = time.time()
        return current_time < (self.app_last_refresh_time + self.app_expires_in - 300)

    def _refresh_app_token(self) -> str:
        try:
            request = dingtalk_oauth_models.GetAccessTokenRequest(
                app_key=self._client_id,
                app_secret=self._client_secret
            )
            response = self.client.get_access_token(request)
            if response.body:
                self.app_access_token = response.body.access_token
                self.app_expires_in = response.body.expire_in
                self.app_last_refresh_time = time.time()
                return self.app_access_token
        except Exception as e:
            logger.error(f"获取应用访问令牌失败: {e}")
        return ""


_auth_instance: Optional[DingtalkAuth] = None


def get_auth() -> DingtalkAuth:
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = DingtalkAuth()
    return _auth_instance


def _reset_auth() -> None:
    global _auth_instance
    _auth_instance = None
