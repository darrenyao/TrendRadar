import pytest
from unittest.mock import Mock, AsyncMock

# 尝试导入，如果 SDK 不可用则跳过测试
try:
    from src.dingtalk.reply_service import DingTalkReplyService, ContentType
    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    DingTalkReplyService = None
    ContentType = None

pytestmark = pytest.mark.skipif(not HAS_SDK, reason="DingTalk SDK not installed")


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
