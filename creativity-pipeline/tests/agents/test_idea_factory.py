"""Tests for IdeaFactoryAgent."""
import pytest


def test_idea_factory_has_correct_system_prompt(monkeypatch):
    """Test IdeaFactoryAgent has domain-specific prompt."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.idea_factory import IdeaFactoryAgent

    agent = IdeaFactoryAgent()
    prompt = agent.get_system_prompt()

    # Should mention ideas and idea creation
    assert "创意" in prompt
    assert "create_idea" in prompt


def test_idea_factory_is_base_agent(monkeypatch):
    """Test IdeaFactoryAgent inherits from BaseAgent."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.idea_factory import IdeaFactoryAgent
    from src.agents.base_agent import BaseAgent

    agent = IdeaFactoryAgent()
    assert isinstance(agent, BaseAgent)


def test_idea_factory_prompt_mentions_scoring(monkeypatch):
    """Test prompt includes scoring guidance."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.idea_factory import IdeaFactoryAgent

    agent = IdeaFactoryAgent()
    prompt = agent.get_system_prompt()

    # Should mention the four dimensions
    assert "feasibility" in prompt or "可行性" in prompt
    assert "market" in prompt or "市场" in prompt


def test_parse_idea_ids_extracts_ids():
    """Test _parse_idea_ids extracts idea IDs from text."""
    from src.agents.idea_factory import IdeaFactoryAgent

    agent = IdeaFactoryAgent()

    text = "创建了 idea-abc12345 和 idea-def67890"
    ids = agent._parse_idea_ids(text)

    assert len(ids) == 2
    assert "idea-abc12345" in ids
    assert "idea-def67890" in ids


def test_parse_idea_ids_handles_date_format():
    """Test _parse_idea_ids handles date-based IDs."""
    from src.agents.idea_factory import IdeaFactoryAgent

    agent = IdeaFactoryAgent()

    text = "创建了 idea-2026-01-12-001"
    ids = agent._parse_idea_ids(text)

    assert len(ids) == 1
    assert "idea-2026-01-12-001" in ids


def test_parse_idea_ids_handles_empty_response():
    """Test _parse_idea_ids handles empty response."""
    from src.agents.idea_factory import IdeaFactoryAgent

    agent = IdeaFactoryAgent()
    ids = agent._parse_idea_ids("没有创建任何创意")

    assert ids == []
