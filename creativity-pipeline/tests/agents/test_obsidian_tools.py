"""Tests for Obsidian MCP tools."""
import pytest
import json
from pathlib import Path

# Check if Claude Agent SDK is available
try:
    from claude_agent_sdk import tool
    HAS_CLAUDE_SDK = True
except ImportError:
    HAS_CLAUDE_SDK = False

pytestmark = pytest.mark.skipif(not HAS_CLAUDE_SDK, reason="Claude Agent SDK not installed")


@pytest.fixture
def temp_vault(tmp_path):
    """Create temporary Obsidian vault with test data."""
    # Create directory structure
    cards_dir = tmp_path / "cards"
    ideas_dir = tmp_path / "ideas"
    experiments_dir = tmp_path / "experiments"
    archive_dir = tmp_path / "archive"

    for d in [cards_dir, ideas_dir, experiments_dir, archive_dir]:
        d.mkdir(parents=True)

    # Create test card
    card_content = """---
id: card-2026-01-12-001
type: card
title: AI 代码生成工具爆发
status: pending
category: change
heat_score: 85
keywords:
  - AI
  - 代码生成
created: '2026-01-12T09:00:00'
---

# AI 代码生成工具爆发

## 原始内容
AI 代码生成工具市场快速增长...
"""
    (cards_dir / "card-2026-01-12-001.md").write_text(card_content)

    # Create test idea
    idea_content = """---
id: idea-2026-01-12-001
type: idea
title: AI 代码审查助手
one_liner: 让每个开发者都有代码审查专家
target_user: 独立开发者
problem: 缺乏代码审查反馈
unique_angle: 结合项目上下文的个性化审查
mvp_time: 30
source_cards:
  - card-2026-01-12-001
scores:
  feasibility: 20
  market: 18
  personal_fit: 22
  uniqueness: 15
  total: 75
status: candidate
created: '2026-01-12T10:00:00'
---

# AI 代码审查助手

## 价值主张
让每个开发者都有代码审查专家
"""
    (ideas_dir / "idea-2026-01-12-001.md").write_text(idea_content)

    # Create test experiment
    exp_content = """---
id: exp-2026-01-12-001
type: experiment
idea_id: idea-2026-01-12-001
idea_title: AI 代码审查助手
estimated_time: 45
status: pending
tasks:
  - id: task-01
    description: 创建 Landing Page
    time_estimate: 15
    deliverable: 上线的页面
    success_criteria: 可访问
    status: pending
created: '2026-01-12T11:00:00'
---

# 实验: AI 代码审查助手
"""
    (experiments_dir / "exp-2026-01-12-001.md").write_text(exp_content)

    return tmp_path


@pytest.mark.asyncio
async def test_read_cards_returns_cards(temp_vault, monkeypatch):
    """Test read_cards returns all cards from vault."""
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import _read_cards_impl

    result = await _read_cards_impl({})

    assert "content" in result
    content = result["content"][0]["text"]
    cards = json.loads(content)
    assert len(cards) >= 1
    assert any(c["id"] == "card-2026-01-12-001" for c in cards)


@pytest.mark.asyncio
async def test_read_ideas_returns_ideas(temp_vault, monkeypatch):
    """Test read_ideas returns all ideas from vault."""
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import _read_ideas_impl

    result = await _read_ideas_impl({})

    assert "content" in result
    content = result["content"][0]["text"]
    ideas = json.loads(content)
    assert len(ideas) >= 1
    assert any(i["id"] == "idea-2026-01-12-001" for i in ideas)


@pytest.mark.asyncio
async def test_read_experiments_returns_experiments(temp_vault, monkeypatch):
    """Test read_experiments returns all experiments from vault."""
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import _read_experiments_impl

    result = await _read_experiments_impl({})

    assert "content" in result
    content = result["content"][0]["text"]
    experiments = json.loads(content)
    assert len(experiments) >= 1
    assert any(e["id"] == "exp-2026-01-12-001" for e in experiments)


@pytest.mark.asyncio
async def test_create_card_creates_file(temp_vault, monkeypatch):
    """Test create_card creates a new card file."""
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import _create_card_impl

    result = await _create_card_impl({
        "title": "测试卡片",
        "content": "测试内容",
        "source": "测试来源",
        "category": "change",
        "keywords": ["测试", "demo"],
        "heat_score": 60
    })

    assert "content" in result
    response_text = result["content"][0]["text"]
    assert "card-" in response_text

    # Verify file was created
    cards_dir = temp_vault / "cards"
    card_files = list(cards_dir.glob("card-*.md"))
    assert len(card_files) >= 2  # Original + new one


@pytest.mark.asyncio
async def test_create_idea_creates_file(temp_vault, monkeypatch):
    """Test create_idea creates a new idea file."""
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import _create_idea_impl

    result = await _create_idea_impl({
        "title": "测试创意",
        "one_liner": "一句话描述",
        "target_user": "开发者",
        "problem": "测试问题",
        "unique_angle": "独特角度",
        "mvp_time": 30,
        "source_cards": ["card-2026-01-12-001"],
        "scores": {
            "feasibility": 20,
            "market": 15,
            "personal_fit": 18,
            "uniqueness": 12,
            "total": 65
        }
    })

    assert "content" in result
    response_text = result["content"][0]["text"]
    assert "idea-" in response_text


@pytest.mark.asyncio
async def test_create_experiment_creates_file(temp_vault, monkeypatch):
    """Test create_experiment creates a new experiment file."""
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import _create_experiment_impl

    result = await _create_experiment_impl({
        "idea_id": "idea-2026-01-12-001",
        "idea_title": "测试创意",
        "estimated_time": 45,
        "tasks": [
            {
                "id": "task-01",
                "description": "任务1",
                "time_estimate": 15,
                "deliverable": "交付物",
                "success_criteria": "成功标准",
                "status": "pending"
            }
        ],
        "three_person_rule": {
            "target_profiles": [{"type": "开发者", "where_to_find": "GitHub"}],
            "recruit_script": "招募话术",
            "feedback_template": "反馈模板"
        }
    })

    assert "content" in result
    response_text = result["content"][0]["text"]
    assert "exp-" in response_text


@pytest.mark.asyncio
async def test_update_status_updates_card(temp_vault, monkeypatch):
    """Test update_status updates card status."""
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import _update_status_impl, _read_cards_impl

    result = await _update_status_impl({
        "item_id": "card-2026-01-12-001",
        "new_status": "selected"
    })

    assert "content" in result
    assert "成功" in result["content"][0]["text"] or "更新" in result["content"][0]["text"]

    # Verify status was updated
    cards_result = await _read_cards_impl({})
    cards = json.loads(cards_result["content"][0]["text"])
    card = next(c for c in cards if c["id"] == "card-2026-01-12-001")
    assert card["status"] == "selected"


def test_get_all_tools_returns_list(temp_vault, monkeypatch):
    """Test get_all_tools returns all tool functions."""
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import get_all_tools

    tools = get_all_tools()

    assert len(tools) >= 6
    # SdkMcpTool objects have a 'name' attribute
    tool_names = [getattr(t, 'name', str(t)) for t in tools]
    assert "read_cards" in tool_names
    assert "read_ideas" in tool_names
    assert "create_card" in tool_names
    assert "create_idea" in tool_names
