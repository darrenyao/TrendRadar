"""Tests for MVPRunnerAgent."""
import pytest

# Check if Claude Agent SDK is available
try:
    from claude_agent_sdk import ClaudeSDKClient
    HAS_CLAUDE_SDK = True
except ImportError:
    HAS_CLAUDE_SDK = False

pytestmark = pytest.mark.skipif(not HAS_CLAUDE_SDK, reason="Claude Agent SDK not installed")


def test_mvp_runner_has_correct_system_prompt(monkeypatch):
    """Test MVPRunnerAgent has domain-specific prompt."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    prompt = agent.get_system_prompt()

    # Should mention experiments
    assert "实验" in prompt or "experiment" in prompt.lower()
    assert "create_experiment" in prompt


def test_mvp_runner_is_base_agent(monkeypatch):
    """Test MVPRunnerAgent inherits from BaseAgent."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent
    from src.agents.base_agent import BaseAgent

    agent = MVPRunnerAgent()
    assert isinstance(agent, BaseAgent)


def test_mvp_runner_prompt_mentions_time_constraint(monkeypatch):
    """Test prompt mentions 45-minute time constraint."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    prompt = agent.get_system_prompt()

    assert "45" in prompt or "分钟" in prompt


def test_mvp_runner_prompt_mentions_three_person_rule(monkeypatch):
    """Test prompt mentions three person rule."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    prompt = agent.get_system_prompt()

    assert "三人" in prompt or "three" in prompt.lower()


def test_parse_experiment_id_extracts_id(monkeypatch):
    """Test _parse_experiment_id extracts experiment ID from text."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()

    text = "创建了实验 exp-abc12345"
    ids = agent._parse_experiment_id(text)

    assert len(ids) == 1
    assert "exp-abc12345" in ids


def test_parse_experiment_id_handles_date_format(monkeypatch):
    """Test _parse_experiment_id handles date-based IDs."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()

    text = "创建了 exp-2026-01-12-001"
    ids = agent._parse_experiment_id(text)

    assert len(ids) == 1
    assert "exp-2026-01-12-001" in ids


def test_parse_experiment_id_handles_empty_response(monkeypatch):
    """Test _parse_experiment_id handles empty response."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    ids = agent._parse_experiment_id("没有创建实验")

    assert ids == []


def test_parse_experiment_data_extracts_json(monkeypatch):
    """Test _parse_experiment_data extracts JSON from response."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    idea = {"id": "idea-001", "title": "Test Idea", "mvp_time": 45}

    response = '''
    Here is the experiment:
    {
        "idea_id": "idea-001",
        "idea_title": "Test Idea",
        "estimated_time": 45,
        "tasks": [
            {"id": "task-01", "description": "Task 1", "time_estimate": 15}
        ],
        "three_person_rule": {
            "target_profiles": [{"type": "Developer"}]
        }
    }
    '''
    result = agent._parse_experiment_data(response, idea)

    assert result["idea_id"] == "idea-001"
    assert len(result["tasks"]) == 1


def test_parse_experiment_data_fallback(monkeypatch):
    """Test _parse_experiment_data returns fallback on invalid JSON."""
    monkeypatch.setenv("VAULT_PATH", "/tmp/vault")

    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    idea = {"id": "idea-001", "title": "Test Idea", "mvp_time": 45}

    response = "无法解析的响应"
    result = agent._parse_experiment_data(response, idea)

    # Should return fallback structure
    assert result["idea_id"] == "idea-001"
    assert "tasks" in result
    assert len(result["tasks"]) >= 1
