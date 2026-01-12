import pytest
from src.dingtalk.pipeline_handler import PipelineCallbackHandler


class TestParseSelection:
    def setup_method(self):
        self.handler = PipelineCallbackHandler(state_machine=None, agents=None)

    def test_parse_single_digit(self):
        result = self.handler.parse_selection("1")
        assert result == {"type": "select", "value": 1}
        result = self.handler.parse_selection("3")
        assert result == {"type": "select", "value": 3}

    def test_parse_multiple_digits(self):
        result = self.handler.parse_selection("1,2")
        assert result == {"type": "select", "value": [1, 2]}
        result = self.handler.parse_selection("1,2,3")
        assert result == {"type": "select", "value": [1, 2, 3]}

    def test_parse_confirm_keywords(self):
        for kw in ["确认", "ok", "好", "OK"]:
            result = self.handler.parse_selection(kw)
            assert result == {"type": "confirm", "value": None}

    def test_parse_start_keywords(self):
        for kw in ["开始", "start", "START"]:
            result = self.handler.parse_selection(kw)
            assert result == {"type": "start", "value": None}

    def test_parse_downgrade_keywords(self):
        for kw in ["降级", "lite", "简单模式"]:
            result = self.handler.parse_selection(kw)
            assert result == {"type": "downgrade", "value": None}

    def test_parse_skip_keywords(self):
        for kw in ["跳过", "skip"]:
            result = self.handler.parse_selection(kw)
            assert result == {"type": "skip", "value": None}

    def test_parse_evidence_default(self):
        result = self.handler.parse_selection("这是我的反馈")
        assert result == {"type": "evidence", "value": "这是我的反馈"}
        result = self.handler.parse_selection("http://example.com")
        assert result == {"type": "evidence", "value": "http://example.com"}

    def test_parse_strips_whitespace(self):
        result = self.handler.parse_selection("  1  ")
        assert result == {"type": "select", "value": 1}
        result = self.handler.parse_selection("  确认  ")
        assert result == {"type": "confirm", "value": None}
