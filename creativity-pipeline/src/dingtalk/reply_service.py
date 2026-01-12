"""
钉钉消息回复服务 - 支持单聊推送
"""
import json
import logging
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
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
    AI_CARD = "ai_card"


@dataclass
class CardData:
    """AI Card 数据"""
    card_data: Dict[str, Any] = None
    template_id: str = None
    options: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "templateId": self.template_id,
            "cardData": self.card_data or {},
        }
        if self.options:
            result["options"] = self.options
        return result


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

    async def reply_card(self, conversation_token: str, card_data: CardData) -> bool:
        """发送 AI Card 回复"""
        return await self.reply(
            conversation_token,
            json.dumps(card_data.to_dict()),
            ContentType.AI_CARD,
        )

    async def prepare_card(
        self,
        card_data: CardData,
        union_id: str = None,
        open_conversation_id: str = None,
    ) -> Optional[str]:
        """
        主动模式下发送 loading 卡片，返回 conversation_token

        Args:
            card_data: 卡片数据
            union_id: 单聊模式，传入工号（如 "107578"）
            open_conversation_id: 群聊模式，传入会话 ID

        Returns:
            conversation_token 用于后续 update/finish，失败返回 None
        """
        try:
            access_token = self.auth.get_app_access_token()
            if not access_token:
                logger.error("获取 access_token 失败")
                return None

            headers = dingtalk_models.PrepareHeaders()
            headers.x_acs_dingtalk_access_token = access_token

            request = dingtalk_models.PrepareRequest(
                open_conversation_id=open_conversation_id,
                content_type=ContentType.AI_CARD.value,
                content=json.dumps(card_data.to_dict()),
                union_id=union_id
            )

            response = await self.client.prepare_with_options_async(
                request,
                headers,
                util_models.RuntimeOptions()
            )

            conversation_token = response.body.result.conversation_token
            logger.info(f"prepare_card 成功, conversation_token: {conversation_token[:20]}...")
            return conversation_token

        except Exception as e:
            logger.error(f"prepare_card 失败: {e}")
            return None

    async def update_card(
        self,
        conversation_token: str,
        card_data: CardData,
    ) -> bool:
        """
        主动模式下更新卡片内容

        Args:
            conversation_token: prepare_card 返回的 token
            card_data: 新的卡片数据
        """
        try:
            access_token = self.auth.get_app_access_token()
            if not access_token:
                logger.error("获取 access_token 失败")
                return False

            headers = dingtalk_models.UpdateHeaders()
            headers.x_acs_dingtalk_access_token = access_token

            request = dingtalk_models.UpdateRequest(
                conversation_token=conversation_token,
                content_type=ContentType.AI_CARD.value,
                content=json.dumps(card_data.to_dict())
            )

            await self.client.update_with_options_async(
                request,
                headers,
                util_models.RuntimeOptions()
            )

            logger.info("update_card 成功")
            return True

        except Exception as e:
            logger.error(f"update_card 失败: {e}")
            return False

    async def finish_card(self, conversation_token: str) -> bool:
        """
        主动模式下完结卡片

        Args:
            conversation_token: prepare_card 返回的 token
        """
        try:
            access_token = self.auth.get_app_access_token()
            if not access_token:
                logger.error("获取 access_token 失败")
                return False

            headers = dingtalk_models.FinishHeaders()
            headers.x_acs_dingtalk_access_token = access_token

            request = dingtalk_models.FinishRequest(
                conversation_token=conversation_token
            )

            await self.client.finish_with_options_async(
                request,
                headers,
                util_models.RuntimeOptions()
            )

            logger.info("finish_card 成功")
            return True

        except Exception as e:
            logger.error(f"finish_card 失败: {e}")
            return False

    async def send_card_to_user(
        self,
        user_id: str,
        card_data: CardData,
    ) -> bool:
        """
        便捷方法：向单聊用户发送卡片（一站式）

        Args:
            user_id: 工号（如 "107578"）
            card_data: 卡片数据
        """
        # 1. prepare_card 获取 conversation_token
        conversation_token = await self.prepare_card(
            card_data=card_data,
            union_id=user_id,
        )
        if not conversation_token:
            return False

        # 2. finish_card 完结（如果内容已经完整）
        return await self.finish_card(conversation_token)


reply_service = DingTalkReplyService()
