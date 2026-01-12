# Agent Layer Design (Developer B)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the Agent layer using Claude Agent SDK to power the creativity pipeline's three core agents.

**Architecture:** Each agent extends BaseAgent with domain-specific prompts. All agents share Obsidian MCP tools created via `@tool` decorator and bundled with `create_sdk_mcp_server()`.

**Tech Stack:** claude-agent-sdk, Python 3.10+, asyncio, pytest-asyncio

---

## Overview

The Agent layer provides AI-powered processing for the creativity pipeline:

1. **InputFeederAgent** - Transforms TrendRadar trending news into structured Cards
2. **IdeaFactoryAgent** - Generates creative Ideas from Cards with scoring
3. **MVPRunnerAgent** - Creates actionable Experiments from confirmed Ideas

## Component Design

### 1. Obsidian MCP Tools (`src/agents/tools/obsidian_tools.py`)

Using `@tool` decorator to wrap ObsidianStore operations:

```python
from claude_agent_sdk import tool
from ..state import ObsidianStore, Card, Idea, Experiment

store = ObsidianStore()

@tool("read_cards", "Read all input cards from Obsidian vault", {})
async def read_cards(args: dict) -> dict:
    cards = store.list_cards()
    return {"content": [{"type": "text", "text": json.dumps([c.to_dict() for c in cards])}]}

@tool("create_card", "Create a new input card", {
    "title": str,
    "content": str,
    "source": str,
    "category": str,
    "keywords": list
})
async def create_card(args: dict) -> dict:
    card = Card(
        id=f"card-{uuid4().hex[:8]}",
        title=args["title"],
        content=args["content"],
        source=args["source"],
        category=args.get("category", "change"),
        keywords=args.get("keywords", [])
    )
    store.save_card(card)
    return {"content": [{"type": "text", "text": f"Created card: {card.id}"}]}

# Similar tools for ideas, experiments, status updates...
```

### 2. BaseAgent (`src/agents/base_agent.py`)

Abstract base providing ClaudeSDKClient setup:

```python
from abc import ABC, abstractmethod
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_sdk_mcp_server
from .tools.obsidian_tools import get_all_tools

class BaseAgent(ABC):
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._client = None
        self._mcp_server = None

    def _get_mcp_server(self):
        if not self._mcp_server:
            self._mcp_server = create_sdk_mcp_server(
                name="obsidian",
                tools=get_all_tools()
            )
        return self._mcp_server

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return agent-specific system prompt"""
        pass

    async def run(self, user_message: str) -> str:
        """Execute agent with user message, return response"""
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

### 3. InputFeederAgent (`src/agents/input_feeder.py`)

Processes TrendRadar data into Cards:

```python
class InputFeederAgent(BaseAgent):
    def get_system_prompt(self) -> str:
        return """你是创意流水线的输入代理。你的任务是将热点新闻转化为结构化的"变化卡片"。

对于每条新闻，你需要：
1. 提取核心变化点
2. 分析受影响的人群
3. 识别潜在机会
4. 评估热度分数 (0-100)

使用 create_card 工具创建卡片，确保：
- title: 简洁的变化描述
- content: 详细的变化内容
- category: change/pain_point/opportunity
- keywords: 相关关键词列表
- heat_score: 基于关注度的热度分数
"""

    async def process_news(self, news_items: List[Dict]) -> List[str]:
        """Process news items into cards"""
        prompt = f"请处理以下热点新闻，为每条创建一张卡片：\n\n{json.dumps(news_items, ensure_ascii=False)}"
        result = await self.run(prompt)
        # Extract card IDs from result
        return self._parse_card_ids(result)
```

### 4. IdeaFactoryAgent (`src/agents/idea_factory.py`)

Generates Ideas from Cards:

```python
class IdeaFactoryAgent(BaseAgent):
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

使用 create_idea 工具创建创意，确保关联源卡片。
"""

    async def generate_ideas(self, card_ids: List[str], count: int = 3) -> List[str]:
        """Generate ideas from selected cards"""
        prompt = f"基于以下卡片ID生成{count}个创意：{card_ids}\n先使用 read_cards 读取卡片内容。"
        result = await self.run(prompt)
        return self._parse_idea_ids(result)
```

### 5. MVPRunnerAgent (`src/agents/mvp_runner.py`)

Creates Experiments from Ideas:

```python
class MVPRunnerAgent(BaseAgent):
    def get_system_prompt(self) -> str:
        return """你是创意流水线的MVP执行代理。你的任务是为确认的创意设计快速验证实验。

实验设计原则：
1. 总时长控制在45分钟内
2. 任务拆分为10分钟左右的小步骤
3. 每个任务有明确的交付物和成功标准
4. 遵循"三人法则"获取反馈

实验任务应包含：
- description: 任务描述
- time_estimate: 预计时长(分钟)
- deliverable: 交付物
- success_criteria: 成功标准
- tools: 所需工具

使用 create_experiment 工具创建实验。
"""

    async def design_experiment(self, idea_id: str) -> str:
        """Design experiment for an idea"""
        prompt = f"为创意 {idea_id} 设计一个MVP验证实验。先使用 read_ideas 读取创意详情。"
        result = await self.run(prompt)
        return self._parse_experiment_id(result)
```

## File Structure

```
creativity-pipeline/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── input_feeder.py
│   │   ├── idea_factory.py
│   │   ├── mvp_runner.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       └── obsidian_tools.py
│   ├── dingtalk/          # Developer A
│   └── state/             # Developer C
├── tests/
│   └── agents/
│       ├── test_obsidian_tools.py
│       ├── test_base_agent.py
│       ├── test_input_feeder.py
│       ├── test_idea_factory.py
│       └── test_mvp_runner.py
└── requirements.txt
```

## Integration with DingTalk (Developer A)

The agents integrate with PipelineCallbackHandler:

```python
# In pipeline_handler.py
class PipelineCallbackHandler:
    def __init__(self, state_machine, agents: Dict[str, BaseAgent]):
        self.agents = agents
        # agents = {
        #     "input_feeder": InputFeederAgent(),
        #     "idea_factory": IdeaFactoryAgent(),
        #     "mvp_runner": MVPRunnerAgent()
        # }
```

## Testing Strategy

1. **Unit Tests**: Mock ClaudeSDKClient, test tool functions with real ObsidianStore
2. **Integration Tests**: Test agent workflows with mocked Claude API
3. **E2E Tests**: Full pipeline with test vault directory
