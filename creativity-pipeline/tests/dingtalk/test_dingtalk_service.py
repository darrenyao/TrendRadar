import pytest
from unittest.mock import Mock, AsyncMock
from src.dingtalk.dingtalk_service import DingTalkService


class TestMessageFormatting:
    def setup_method(self):
        mock_reply = Mock()
        mock_reply.reply_markdown = AsyncMock(return_value=True)
        mock_reply.reply_text = AsyncMock(return_value=True)
        self.service = DingTalkService(mock_reply, "test_conv_id")

    def test_format_morning_message_with_ideas(self):
        ideas = [
            {"title": "创意1", "one_liner": "描述1", "mvp_time": 30},
            {"title": "创意2", "one_liner": "描述2", "mvp_time": 45},
            {"title": "创意3", "one_liner": "描述3", "mvp_time": 60},
        ]
        result = self.service._format_morning_message([], ideas)
        assert "创意1" in result
        assert "创意2" in result
        assert "创意3" in result
        assert "1/2/3" in result

    def test_format_afternoon_message_with_experiment(self):
        experiment = {
            "idea_title": "测试创意",
            "tasks": [
                {"time_estimate": 10, "description": "任务1"},
                {"time_estimate": 20, "description": "任务2"},
            ]
        }
        result = self.service._format_afternoon_message(experiment)
        assert "测试创意" in result
        assert "任务1" in result
        assert "任务2" in result

    def test_format_evening_message(self):
        experiment = {
            "idea_title": "测试创意",
            "status": "in_progress",
        }
        result = self.service._format_evening_message(experiment)
        assert "测试创意" in result
        assert "证据" in result


class TestSendMethods:
    def setup_method(self):
        self.mock_reply = Mock()
        self.mock_reply.reply_markdown = AsyncMock(return_value=True)
        self.mock_reply.reply_text = AsyncMock(return_value=True)
        self.service = DingTalkService(self.mock_reply, "test_conv_id")

    @pytest.mark.asyncio
    async def test_send_morning_push(self):
        result = await self.service.send_morning_push([], [])
        assert result is True
        self.mock_reply.reply_markdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_confirmation(self):
        result = await self.service.send_confirmation("操作成功", "详情信息")
        assert result is True
        call_args = self.mock_reply.reply_text.call_args
        assert "操作成功" in call_args[0][1]
