"""Tests for BaseAgent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_base_agent_creates_mcp_server(monkeypatch):
    """Test BaseAgent creates MCP server with Obsidian tools."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.base_agent import BaseAgent

    class TestAgent(BaseAgent):
        def get_system_prompt(self) -> str:
            return "Test prompt"

    agent = TestAgent()
    server = agent._get_mcp_server()

    assert server is not None


def test_base_agent_mcp_server_is_singleton(monkeypatch):
    """Test that MCP server is created only once."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.base_agent import BaseAgent

    class TestAgent(BaseAgent):
        def get_system_prompt(self) -> str:
            return "Test prompt"

    agent = TestAgent()
    server1 = agent._get_mcp_server()
    server2 = agent._get_mcp_server()

    assert server1 is server2


def test_base_agent_requires_system_prompt(monkeypatch):
    """Test that BaseAgent requires get_system_prompt implementation."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.base_agent import BaseAgent

    # Cannot instantiate BaseAgent directly
    with pytest.raises(TypeError):
        BaseAgent()


def test_base_agent_accepts_custom_model(monkeypatch):
    """Test BaseAgent accepts custom model parameter."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.base_agent import BaseAgent

    class TestAgent(BaseAgent):
        def get_system_prompt(self) -> str:
            return "Test prompt"

    agent = TestAgent(model="claude-opus-4-20250514")
    assert agent.model == "claude-opus-4-20250514"


def test_base_agent_default_model(monkeypatch):
    """Test BaseAgent has default model."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.base_agent import BaseAgent

    class TestAgent(BaseAgent):
        def get_system_prompt(self) -> str:
            return "Test prompt"

    agent = TestAgent()
    assert agent.model == "claude-sonnet-4-20250514"
