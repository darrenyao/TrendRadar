"""Tests for MVPRunnerAgent."""
import pytest


def test_mvp_runner_has_correct_system_prompt(monkeypatch):
    """Test MVPRunnerAgent has domain-specific prompt."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    prompt = agent.get_system_prompt()

    # Should mention experiments
    assert "实验" in prompt or "experiment" in prompt.lower()
    assert "create_experiment" in prompt


def test_mvp_runner_is_base_agent(monkeypatch):
    """Test MVPRunnerAgent inherits from BaseAgent."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent
    from src.agents.base_agent import BaseAgent

    agent = MVPRunnerAgent()
    assert isinstance(agent, BaseAgent)


def test_mvp_runner_prompt_mentions_time_constraint(monkeypatch):
    """Test prompt mentions 45-minute time constraint."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    prompt = agent.get_system_prompt()

    assert "45" in prompt or "分钟" in prompt


def test_mvp_runner_prompt_mentions_three_person_rule(monkeypatch):
    """Test prompt mentions three person rule."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    prompt = agent.get_system_prompt()

    assert "三人" in prompt or "three" in prompt.lower()


def test_parse_experiment_id_extracts_id():
    """Test _parse_experiment_id extracts experiment ID from text."""
    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()

    text = "创建了实验 exp-abc12345"
    ids = agent._parse_experiment_id(text)

    assert len(ids) == 1
    assert "exp-abc12345" in ids


def test_parse_experiment_id_handles_date_format():
    """Test _parse_experiment_id handles date-based IDs."""
    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()

    text = "创建了 exp-2026-01-12-001"
    ids = agent._parse_experiment_id(text)

    assert len(ids) == 1
    assert "exp-2026-01-12-001" in ids


def test_parse_experiment_id_handles_empty_response():
    """Test _parse_experiment_id handles empty response."""
    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    ids = agent._parse_experiment_id("没有创建实验")

    assert ids == []
