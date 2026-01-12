import pytest
from unittest.mock import Mock, AsyncMock
from src.dingtalk.reply_service import DingTalkReplyService, ContentType


class TestContentType:
    def test_content_type_values(self):
        assert ContentType.TEXT.value == "text"
        assert ContentType.MARKDOWN.value == "markdown"


class TestDingTalkReplyService:
    @pytest.mark.asyncio
    async def test_reply_text_calls_reply_with_text_type(self):
        service = DingTalkReplyService()
        service.reply = AsyncMock(return_value=True)
        result = await service.reply_text("token123", "hello")
        service.reply.assert_called_once_with("token123", "hello", ContentType.TEXT)
        assert result is True

    @pytest.mark.asyncio
    async def test_reply_markdown_calls_reply_with_markdown_type(self):
        service = DingTalkReplyService()
        service.reply = AsyncMock(return_value=True)
        result = await service.reply_markdown("token123", "**bold**")
        service.reply.assert_called_once_with("token123", "**bold**", ContentType.MARKDOWN)
        assert result is True
