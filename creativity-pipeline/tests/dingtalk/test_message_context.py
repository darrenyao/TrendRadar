import pytest
from src.dingtalk.message_context import MessageContext


class TestMessageContext:
    def test_create_from_dict(self):
        data = {
            "senderId": "user123",
            "uid": 12345,
            "orgId": 67890,
            "text": {"content": "hello"},
            "senderNick": "张三",
            "conversationType": "2",
            "conversationId": "conv123",
            "conversationToken": "token123",
        }
        context = MessageContext.from_dingtalk_message(data)
        assert context.user_id == "user123"
        assert context.uid == 12345
        assert context.content == "hello"
        assert context.user_name == "张三"
        assert context.is_group_chat is True

    def test_create_with_minimal_data(self):
        data = {}
        context = MessageContext.from_dingtalk_message(data)
        assert context.user_id == ""
        assert context.uid == 0
        assert context.content == ""

    def test_to_dict(self):
        context = MessageContext(
            user_id="user123",
            uid=12345,
            org_id=67890,
            content="hello"
        )
        result = context.to_dict()
        assert result["user_id"] == "user123"
        assert result["content"] == "hello"
