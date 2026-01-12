"""
钉钉消息回复服务（精简版）
"""
import logging
from typing import Optional
from enum import Enum

from alibabacloud_dingtalk.ai_interaction_1_0.client import Client as DingTalkAIClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.ai_interaction_1_0 import models as dingtalk_models
from alibabacloud_tea_util import models as util_models

from .dingtalk_auth import get_auth

logger = logging.getLogger(__name__)


class ContentType(Enum):
    TEXT = "text"
    MARKDOWN = "markdown"


class DingTalkReplyService:
    def __init__(self):
        self.client = self._create_client()
        self.auth = get_auth()

    def _create_client(self) -> DingTalkAIClient:
        config = open_api_models.Config(
            protocol='https',
            region_id='central'
        )
        return DingTalkAIClient(config)

    async def reply(
        self,
        conversation_token: str,
        content: str,
        content_type: ContentType = ContentType.TEXT,
    ) -> bool:
        try:
            access_token = self.auth.get_app_access_token()
            if not access_token:
                logger.error("获取 access_token 失败")
                return False

            headers = dingtalk_models.ReplyHeaders()
            headers.x_acs_dingtalk_access_token = access_token

            request = dingtalk_models.ReplyRequest(
                conversation_token=conversation_token,
                content_type=content_type.value,
                content=content
            )

            await self.client.reply_with_options_async(
                request,
                headers,
                util_models.RuntimeOptions()
            )

            logger.info(f"发送 {content_type.value} 消息成功")
            return True

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    async def reply_text(self, conversation_token: str, text: str) -> bool:
        return await self.reply(conversation_token, text, ContentType.TEXT)

    async def reply_markdown(self, conversation_token: str, markdown: str) -> bool:
        return await self.reply(conversation_token, markdown, ContentType.MARKDOWN)


reply_service = DingTalkReplyService()
