"""Tests for InputFeederAgent."""
import pytest
from unittest.mock import AsyncMock, patch

# Check if Claude Agent SDK is available
try:
    from claude_agent_sdk import ClaudeSDKClient
    HAS_CLAUDE_SDK = True
except ImportError:
    HAS_CLAUDE_SDK = False

pytestmark = pytest.mark.skipif(not HAS_CLAUDE_SDK, reason="Claude Agent SDK not installed")


def test_input_feeder_has_correct_system_prompt(monkeypatch):
    """Test InputFeederAgent has domain-specific prompt."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.input_feeder import InputFeederAgent

    agent = InputFeederAgent()
    prompt = agent.get_system_prompt()

    # Should mention cards and card creation
    assert "卡片" in prompt or "card" in prompt.lower()
    assert "create_card" in prompt


def test_input_feeder_is_base_agent(monkeypatch):
    """Test InputFeederAgent inherits from BaseAgent."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.input_feeder import InputFeederAgent
    from src.agents.base_agent import BaseAgent

    agent = InputFeederAgent()
    assert isinstance(agent, BaseAgent)


def test_input_feeder_has_mcp_server(monkeypatch):
    """Test InputFeederAgent has access to MCP server."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.input_feeder import InputFeederAgent

    agent = InputFeederAgent()
    server = agent._get_mcp_server()
    assert server is not None


def test_parse_card_ids_extracts_ids(monkeypatch):
    """Test _parse_card_ids extracts card IDs from text."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.input_feeder import InputFeederAgent

    agent = InputFeederAgent()

    text = "创建了 card-abc12345 和 card-def67890"
    ids = agent._parse_card_ids(text)

    assert len(ids) == 2
    assert "card-abc12345" in ids
    assert "card-def67890" in ids


def test_parse_card_ids_handles_empty_response(monkeypatch):
    """Test _parse_card_ids handles empty response."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.input_feeder import InputFeederAgent

    agent = InputFeederAgent()
    ids = agent._parse_card_ids("没有创建任何卡片")

    assert ids == []


def test_input_feeder_prompt_mentions_heat_score(monkeypatch):
    """Test prompt includes heat score guidance."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.input_feeder import InputFeederAgent

    agent = InputFeederAgent()
    prompt = agent.get_system_prompt()

    assert "heat_score" in prompt or "热度" in prompt
