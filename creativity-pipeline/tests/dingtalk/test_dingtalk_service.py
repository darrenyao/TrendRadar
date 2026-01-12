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
        """当有创意时，展示 Top 3 创意供选择"""
        ideas = [
            {"title": "创意1", "one_liner": "描述1", "target_user": "开发者", "mvp_time": 30},
            {"title": "创意2", "one_liner": "描述2", "target_user": "产品经理", "mvp_time": 45},
            {"title": "创意3", "one_liner": "描述3", "target_user": "创业者", "mvp_time": 60},
        ]
        result = self.service._format_morning_message([], ideas)
        # 验证创意内容展示
        assert "创意1" in result
        assert "创意2" in result
        assert "创意3" in result
        assert "描述1" in result
        # 验证带编号（1️⃣ 2️⃣ 3️⃣）
        assert "1️⃣" in result
        assert "2️⃣" in result
        assert "3️⃣" in result
        # 验证选择提示
        assert "1/2/3 选择要验证的创意" in result

    def test_format_morning_message_without_ideas_with_cards(self):
        """当无创意但有卡片时，展示素材供选择"""
        cards = [
            {"title": "热点新闻1", "source_platform": "weibo", "is_cross_platform": True},
            {"title": "热点新闻2", "source_platform": "zhihu", "is_cross_platform": False},
            {"title": "热点新闻3", "source_platform": "36kr"},
        ]
        result = self.service._format_morning_message(cards, [])
        # 验证标题
        assert "今日热点素材" in result
        # 验证卡片内容
        assert "热点新闻1" in result
        assert "热点新闻2" in result
        # 验证带编号
        assert "**1.**" in result
        assert "**2.**" in result
        # 验证选择提示
        assert "回复数字选择素材" in result
        # 验证查看更多提示
        assert "更多" in result
        # 验证跨平台标识
        assert "🔥" in result

    def test_format_morning_message_empty(self):
        """当无创意也无卡片时，展示空状态"""
        result = self.service._format_morning_message([], [])
        assert "暂无热点素材" in result
        assert "刷新" in result

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
        # Mock proactive push methods (prepare_card → update_card → finish_card)
        self.mock_reply.prepare_card = AsyncMock(return_value="test_conversation_token")
        self.mock_reply.update_card = AsyncMock(return_value=True)
        self.mock_reply.finish_card = AsyncMock(return_value=True)
        # Mock passive reply methods
        self.mock_reply.reply_card = AsyncMock(return_value=True)
        self.mock_reply.reply_text = AsyncMock(return_value=True)
        self.service = DingTalkService(self.mock_reply, "test_conv_id")

    @pytest.mark.asyncio
    async def test_send_morning_push(self):
        result = await self.service.send_morning_push([], [])
        assert result is True
        # Verify proactive push flow was used
        self.mock_reply.prepare_card.assert_called_once()
        self.mock_reply.update_card.assert_called_once()
        self.mock_reply.finish_card.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_confirmation(self):
        result = await self.service.send_confirmation("操作成功", "详情信息")
        assert result is True
        # send_confirmation uses proactive push flow (not reply)
        self.mock_reply.prepare_card.assert_called_once()

    @pytest.mark.asyncio
    async def test_reply_confirmation(self):
        """Test passive reply confirmation (using existing conversation token)"""
        result = await self.service.reply_confirmation("token123", "操作成功")
        assert result is True
        # Verify reply_card was called with the conversation token
        self.mock_reply.reply_card.assert_called_once()
        call_args = self.mock_reply.reply_card.call_args
        assert call_args[0][0] == "token123"

    @pytest.mark.asyncio
    async def test_reply_to_message(self):
        """Test passive reply to user message"""
        result = await self.service.reply_to_message("token123", "回复内容")
        assert result is True
        self.mock_reply.reply_card.assert_called_once()
        call_args = self.mock_reply.reply_card.call_args
        assert call_args[0][0] == "token123"
