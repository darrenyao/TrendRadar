# Agent Layer Implementation Plan (Developer B)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the Agent layer using Claude Agent SDK for the creativity pipeline.

**Architecture:** BaseAgent + 3 domain agents + Obsidian MCP tools

**Tech Stack:** claude-agent-sdk, Python 3.10+, pytest-asyncio

---

## Task 1: Add claude-agent-sdk to requirements.txt

**Files:**
- Modify: `creativity-pipeline/requirements.txt`

**Step 1: Update requirements**

Add claude-agent-sdk dependency:

```
# ==================== Agent SDK (Developer B) ====================
claude-agent-sdk>=0.1.0
anthropic>=0.18.0
```

**Step 2: Install dependencies**

Run: `cd creativity-pipeline && pip install -r requirements.txt`

**Step 3: Verify installation**

Run: `python -c "from claude_agent_sdk import tool, ClaudeSDKClient; print('OK')"`
Expected: OK

---

## Task 2: Create Obsidian MCP Tools

**Files:**
- Create: `creativity-pipeline/src/agents/__init__.py`
- Create: `creativity-pipeline/src/agents/tools/__init__.py`
- Create: `creativity-pipeline/src/agents/tools/obsidian_tools.py`
- Test: `creativity-pipeline/tests/agents/test_obsidian_tools.py`

**Step 1: Write failing test for read_cards tool**

```python
# tests/agents/test_obsidian_tools.py
import pytest
import json
import tempfile
import os
from pathlib import Path

@pytest.fixture
def temp_vault(tmp_path):
    """Create temporary Obsidian vault"""
    cards_dir = tmp_path / "1-input-cards"
    cards_dir.mkdir(parents=True)

    # Create test card
    card_content = """---
id: card-test001
type: card
title: Test Card
status: pending
category: change
heat_score: 50
---

# Test Card

Test content.
"""
    (cards_dir / "card-test001.md").write_text(card_content)
    return tmp_path

@pytest.mark.asyncio
async def test_read_cards_returns_cards(temp_vault, monkeypatch):
    """Test read_cards returns all cards from vault"""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(temp_vault))

    from src.agents.tools.obsidian_tools import read_cards

    result = await read_cards({})

    assert "content" in result
    content = result["content"][0]["text"]
    cards = json.loads(content)
    assert len(cards) == 1
    assert cards[0]["id"] == "card-test001"
```

**Step 2: Run test to verify it fails**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_obsidian_tools.py::test_read_cards_returns_cards -v`
Expected: FAIL with "No module named 'src.agents'"

**Step 3: Create directory structure**

```bash
mkdir -p creativity-pipeline/src/agents/tools
touch creativity-pipeline/src/agents/__init__.py
touch creativity-pipeline/src/agents/tools/__init__.py
```

**Step 4: Write minimal implementation**

```python
# src/agents/tools/obsidian_tools.py
"""Obsidian MCP tools for Agent layer."""
import os
import json
from typing import Dict, Any, List, Callable

from claude_agent_sdk import tool

from ...state import ObsidianStore, Card, Idea, Experiment

def get_store() -> ObsidianStore:
    """Get ObsidianStore instance with configured vault path."""
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "")
    return ObsidianStore(vault_path) if vault_path else ObsidianStore()


@tool("read_cards", "Read all input cards from Obsidian vault", {})
async def read_cards(args: dict) -> dict:
    """Read all cards from the vault."""
    store = get_store()
    cards = store.list_cards()
    cards_data = [c.to_dict() for c in cards]
    return {
        "content": [{"type": "text", "text": json.dumps(cards_data, ensure_ascii=False)}]
    }
```

**Step 5: Run test to verify it passes**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_obsidian_tools.py::test_read_cards_returns_cards -v`
Expected: PASS

**Step 6: Add more tool tests and implementations**

Add tests for:
- `read_ideas` - Read all ideas
- `read_experiments` - Read all experiments
- `create_card` - Create new card
- `create_idea` - Create new idea
- `create_experiment` - Create new experiment
- `update_card_status` - Update card status
- `update_idea_status` - Update idea status

**Step 7: Implement all tools**

Complete the obsidian_tools.py with all tool implementations.

**Step 8: Add get_all_tools helper**

```python
def get_all_tools() -> List[Callable]:
    """Return all Obsidian tools for MCP server."""
    return [
        read_cards,
        read_ideas,
        read_experiments,
        create_card,
        create_idea,
        create_experiment,
        update_card_status,
        update_idea_status,
    ]
```

**Step 9: Run all tool tests**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_obsidian_tools.py -v`
Expected: All tests pass

**Step 10: Commit**

```bash
git add creativity-pipeline/src/agents/ creativity-pipeline/tests/agents/
git commit -m "feat(agents): add Obsidian MCP tools for Agent layer"
```

---

## Task 3: Implement BaseAgent

**Files:**
- Create: `creativity-pipeline/src/agents/base_agent.py`
- Test: `creativity-pipeline/tests/agents/test_base_agent.py`

**Step 1: Write failing test for BaseAgent initialization**

```python
# tests/agents/test_base_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_base_agent_creates_mcp_server():
    """Test BaseAgent creates MCP server with Obsidian tools"""
    from src.agents.base_agent import BaseAgent

    class TestAgent(BaseAgent):
        def get_system_prompt(self) -> str:
            return "Test prompt"

    agent = TestAgent()
    server = agent._get_mcp_server()

    assert server is not None
    assert server.name == "obsidian"
```

**Step 2: Run test to verify it fails**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_base_agent.py::test_base_agent_creates_mcp_server -v`
Expected: FAIL

**Step 3: Write BaseAgent implementation**

```python
# src/agents/base_agent.py
"""Base agent class for creativity pipeline."""
from abc import ABC, abstractmethod
from typing import Optional
import os

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_sdk_mcp_server

from .tools.obsidian_tools import get_all_tools


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize base agent.

        Args:
            model: Claude model to use
        """
        self.model = model
        self._mcp_server = None

    def _get_mcp_server(self):
        """Get or create MCP server with Obsidian tools."""
        if self._mcp_server is None:
            self._mcp_server = create_sdk_mcp_server(
                name="obsidian",
                tools=get_all_tools()
            )
        return self._mcp_server

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return agent-specific system prompt."""
        pass

    async def run(self, user_message: str) -> str:
        """Execute agent with user message.

        Args:
            user_message: The message to process

        Returns:
            Agent response text
        """
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=self.get_system_prompt(),
            mcp_servers={"obsidian": self._get_mcp_server()},
            allowed_tools=["mcp__obsidian__*"]
        )

        async with ClaudeSDKClient(options) as client:
            await client.query(user_message)
            response_text = ""
            async for message in client.receive_response():
                if hasattr(message, 'text'):
                    response_text += message.text
            return response_text
```

**Step 4: Run test to verify it passes**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_base_agent.py -v`
Expected: PASS

**Step 5: Add test for run method (mocked)**

```python
@pytest.mark.asyncio
async def test_base_agent_run_with_mock():
    """Test BaseAgent.run with mocked ClaudeSDKClient"""
    with patch('src.agents.base_agent.ClaudeSDKClient') as mock_client_class:
        # Setup mock
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.text = "Test response"
        mock_client.receive_response.return_value = AsyncIterator([mock_message])

        from src.agents.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def get_system_prompt(self) -> str:
                return "Test prompt"

        agent = TestAgent()
        result = await agent.run("Test input")

        assert result == "Test response"
        mock_client.query.assert_called_once_with("Test input")
```

**Step 6: Run all base agent tests**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_base_agent.py -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add creativity-pipeline/src/agents/base_agent.py creativity-pipeline/tests/agents/test_base_agent.py
git commit -m "feat(agents): add BaseAgent with ClaudeSDKClient integration"
```

---

## Task 4: Implement InputFeederAgent

**Files:**
- Create: `creativity-pipeline/src/agents/input_feeder.py`
- Test: `creativity-pipeline/tests/agents/test_input_feeder.py`

**Step 1: Write failing test**

```python
# tests/agents/test_input_feeder.py
import pytest
from unittest.mock import AsyncMock, patch

def test_input_feeder_has_correct_system_prompt():
    """Test InputFeederAgent has domain-specific prompt"""
    from src.agents.input_feeder import InputFeederAgent

    agent = InputFeederAgent()
    prompt = agent.get_system_prompt()

    assert "变化卡片" in prompt or "input" in prompt.lower()
    assert "create_card" in prompt
```

**Step 2: Run test to verify it fails**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_input_feeder.py::test_input_feeder_has_correct_system_prompt -v`
Expected: FAIL

**Step 3: Write InputFeederAgent implementation**

```python
# src/agents/input_feeder.py
"""InputFeeder agent for processing news into cards."""
import json
import re
from typing import List, Dict, Any

from .base_agent import BaseAgent


class InputFeederAgent(BaseAgent):
    """Agent that transforms trending news into structured input cards."""

    def get_system_prompt(self) -> str:
        return """你是创意流水线的输入代理。你的任务是将热点新闻转化为结构化的"变化卡片"。

对于每条新闻，你需要：
1. 提取核心变化点
2. 分析受影响的人群
3. 识别潜在机会
4. 评估热度分数 (0-100)

使用 create_card 工具创建卡片，确保：
- title: 简洁的变化描述（20字以内）
- content: 详细的变化内容
- source: 新闻来源
- category: change（变化）/ pain_point（痛点）/ opportunity（机会）
- keywords: 相关关键词列表
- heat_score: 基于关注度的热度分数

处理完所有新闻后，列出创建的所有卡片ID。
"""

    async def process_news(self, news_items: List[Dict[str, Any]]) -> List[str]:
        """Process news items into cards.

        Args:
            news_items: List of news items with title, content, source

        Returns:
            List of created card IDs
        """
        prompt = f"请处理以下热点新闻，为每条创建一张卡片：\n\n{json.dumps(news_items, ensure_ascii=False, indent=2)}"
        result = await self.run(prompt)
        return self._parse_card_ids(result)

    def _parse_card_ids(self, response: str) -> List[str]:
        """Extract card IDs from agent response."""
        # Match patterns like card-abc12345
        pattern = r'card-[a-f0-9]{8}'
        return re.findall(pattern, response)
```

**Step 4: Run test to verify it passes**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_input_feeder.py -v`
Expected: PASS

**Step 5: Add more tests**

- Test `process_news` method with mocked run
- Test `_parse_card_ids` extraction

**Step 6: Commit**

```bash
git add creativity-pipeline/src/agents/input_feeder.py creativity-pipeline/tests/agents/test_input_feeder.py
git commit -m "feat(agents): add InputFeederAgent for news to card processing"
```

---

## Task 5: Implement IdeaFactoryAgent

**Files:**
- Create: `creativity-pipeline/src/agents/idea_factory.py`
- Test: `creativity-pipeline/tests/agents/test_idea_factory.py`

**Step 1: Write failing test**

```python
# tests/agents/test_idea_factory.py
import pytest

def test_idea_factory_has_correct_system_prompt():
    """Test IdeaFactoryAgent has domain-specific prompt"""
    from src.agents.idea_factory import IdeaFactoryAgent

    agent = IdeaFactoryAgent()
    prompt = agent.get_system_prompt()

    assert "创意" in prompt
    assert "create_idea" in prompt
    assert "feasibility" in prompt or "可行性" in prompt
```

**Step 2: Run test to verify it fails**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_idea_factory.py -v`
Expected: FAIL

**Step 3: Write IdeaFactoryAgent implementation**

```python
# src/agents/idea_factory.py
"""IdeaFactory agent for generating ideas from cards."""
import json
import re
from typing import List

from .base_agent import BaseAgent


class IdeaFactoryAgent(BaseAgent):
    """Agent that generates creative ideas from input cards."""

    def get_system_prompt(self) -> str:
        return """你是创意流水线的创意工厂代理。你的任务是从输入卡片中发现创业/产品机会。

创意生成原则：
1. 针对具体的目标用户
2. 解决真实的痛点
3. 有独特的切入角度
4. MVP可在30分钟内完成

对每个创意进行四维评分 (0-25分)：
- feasibility: 技术可行性
- market: 市场潜力
- personal_fit: 个人匹配度
- uniqueness: 独特性

使用 create_idea 工具创建创意，确保：
- title: 创意名称
- one_liner: 一句话描述
- target_user: 目标用户
- problem: 解决的问题
- unique_angle: 独特切入点
- mvp_time: MVP预计时间（分钟）
- source_cards: 源卡片ID列表
- scores: 四维评分

生成创意后，列出所有创建的创意ID。
"""

    async def generate_ideas(self, card_ids: List[str], count: int = 3) -> List[str]:
        """Generate ideas from selected cards.

        Args:
            card_ids: List of card IDs to generate ideas from
            count: Number of ideas to generate

        Returns:
            List of created idea IDs
        """
        prompt = f"""基于以下卡片生成{count}个创意。

步骤：
1. 先使用 read_cards 读取所有卡片
2. 筛选出ID为 {card_ids} 的卡片
3. 分析这些卡片中的变化/痛点/机会
4. 为每个创意使用 create_idea 工具创建

请开始处理。
"""
        result = await self.run(prompt)
        return self._parse_idea_ids(result)

    def _parse_idea_ids(self, response: str) -> List[str]:
        """Extract idea IDs from agent response."""
        pattern = r'idea-[a-f0-9]{8}'
        return re.findall(pattern, response)
```

**Step 4: Run test to verify it passes**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_idea_factory.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add creativity-pipeline/src/agents/idea_factory.py creativity-pipeline/tests/agents/test_idea_factory.py
git commit -m "feat(agents): add IdeaFactoryAgent for idea generation"
```

---

## Task 6: Implement MVPRunnerAgent

**Files:**
- Create: `creativity-pipeline/src/agents/mvp_runner.py`
- Test: `creativity-pipeline/tests/agents/test_mvp_runner.py`

**Step 1: Write failing test**

```python
# tests/agents/test_mvp_runner.py
import pytest

def test_mvp_runner_has_correct_system_prompt():
    """Test MVPRunnerAgent has domain-specific prompt"""
    from src.agents.mvp_runner import MVPRunnerAgent

    agent = MVPRunnerAgent()
    prompt = agent.get_system_prompt()

    assert "实验" in prompt or "experiment" in prompt.lower()
    assert "create_experiment" in prompt
    assert "45" in prompt or "分钟" in prompt
```

**Step 2: Run test to verify it fails**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_mvp_runner.py -v`
Expected: FAIL

**Step 3: Write MVPRunnerAgent implementation**

```python
# src/agents/mvp_runner.py
"""MVPRunner agent for creating experiments from ideas."""
import re
from typing import Optional

from .base_agent import BaseAgent


class MVPRunnerAgent(BaseAgent):
    """Agent that designs MVP experiments for validated ideas."""

    def get_system_prompt(self) -> str:
        return """你是创意流水线的MVP执行代理。你的任务是为确认的创意设计快速验证实验。

实验设计原则：
1. 总时长控制在45分钟内
2. 任务拆分为10分钟左右的小步骤
3. 每个任务有明确的交付物和成功标准
4. 遵循"三人法则"获取反馈

实验任务结构：
- id: 任务ID (如 task-01)
- description: 任务描述
- time_estimate: 预计时长（分钟）
- deliverable: 交付物
- success_criteria: 成功标准
- tools: 所需工具列表

三人法则设计：
- target_profiles: 3个目标用户画像
- recruit_script: 招募话术
- feedback_template: 反馈收集模板

使用 create_experiment 工具创建实验，确保：
- idea_id: 关联的创意ID
- idea_title: 创意标题
- estimated_time: 总预计时间
- tasks: 任务列表
- three_person_rule: 三人法则配置

创建实验后，返回实验ID。
"""

    async def design_experiment(self, idea_id: str) -> Optional[str]:
        """Design experiment for an idea.

        Args:
            idea_id: The idea ID to create experiment for

        Returns:
            Created experiment ID or None
        """
        prompt = f"""为创意 {idea_id} 设计一个MVP验证实验。

步骤：
1. 使用 read_ideas 读取创意详情
2. 分析创意的核心假设
3. 设计4-5个验证任务
4. 使用 create_experiment 创建实验

请开始处理。
"""
        result = await self.run(prompt)
        ids = self._parse_experiment_id(result)
        return ids[0] if ids else None

    def _parse_experiment_id(self, response: str) -> list:
        """Extract experiment ID from agent response."""
        pattern = r'exp-[a-f0-9]{8}'
        return re.findall(pattern, response)
```

**Step 4: Run test to verify it passes**

Run: `cd creativity-pipeline && python -m pytest tests/agents/test_mvp_runner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add creativity-pipeline/src/agents/mvp_runner.py creativity-pipeline/tests/agents/test_mvp_runner.py
git commit -m "feat(agents): add MVPRunnerAgent for experiment design"
```

---

## Task 7: Add agents module exports

**Files:**
- Modify: `creativity-pipeline/src/agents/__init__.py`

**Step 1: Update __init__.py**

```python
# src/agents/__init__.py
"""Agent layer for creativity pipeline.

Provides AI-powered agents for the creativity pipeline:
- InputFeederAgent: Transform news into cards
- IdeaFactoryAgent: Generate ideas from cards
- MVPRunnerAgent: Design experiments from ideas
"""
from .base_agent import BaseAgent
from .input_feeder import InputFeederAgent
from .idea_factory import IdeaFactoryAgent
from .mvp_runner import MVPRunnerAgent
from .tools.obsidian_tools import get_all_tools

__all__ = [
    # Base
    "BaseAgent",
    # Agents
    "InputFeederAgent",
    "IdeaFactoryAgent",
    "MVPRunnerAgent",
    # Tools
    "get_all_tools",
]
```

**Step 2: Verify imports work**

Run: `cd creativity-pipeline && python -c "from src.agents import InputFeederAgent, IdeaFactoryAgent, MVPRunnerAgent; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add creativity-pipeline/src/agents/__init__.py
git commit -m "feat(agents): add module exports"
```

---

## Task 8: Run all agent tests

**Step 1: Run full test suite**

Run: `cd creativity-pipeline && python -m pytest tests/agents/ -v`
Expected: All tests pass

**Step 2: Run with coverage**

Run: `cd creativity-pipeline && python -m pytest tests/agents/ --cov=src/agents --cov-report=term-missing`
Expected: Coverage report showing >80% coverage

---

## Task 9: Integration verification

**Step 1: Verify integration with DingTalk module**

```python
# Quick integration test
cd creativity-pipeline
python -c "
from src.dingtalk import PipelineCallbackHandler
from src.agents import InputFeederAgent, IdeaFactoryAgent, MVPRunnerAgent
from src.state import PipelineStateMachine

agents = {
    'input_feeder': InputFeederAgent(),
    'idea_factory': IdeaFactoryAgent(),
    'mvp_runner': MVPRunnerAgent()
}
state_machine = PipelineStateMachine()

# This should work without errors
handler = PipelineCallbackHandler(state_machine, agents)
print('Integration OK')
"
```

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat(agents): complete Agent layer implementation for creativity pipeline"
```
