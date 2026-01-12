# 创意流水线系统设计方案

> **文档路径**: `docs/creativity-pipeline-design.md`
> **版本**: v1.0
> **日期**: 2026-01-12
> **协作人员**: 3人并行开发

---

## 项目背景与目标

### 背景
AI已经能够完成大量编码、分析工作，执行不再是瓶颈。**想法和创意以及快速迭代**成为当下时代更重要的能力。但作为工程师，长期聚焦于架构设计、编码落地、线上稳定性等工作，生活半径狭窄，对新潮流新事物观察较少，导致创意能力欠缺。

### 目标
打造一套**「不靠意志力」**的系统：
- **自动触发**：每天固定时间推送任务，不需要想"要不要做"
- **自动喂输入**：系统主动提供素材，不需要"去找素材"
- **自动产出候选**：系统生成想法，人只需要"选"
- **自动分配最小实验**：系统拆解任务，人只需要"执行"
- **自动收证据**：系统追问结果，强制闭环
- **自动复盘**：系统归档总结，迭代优化

**核心原则**：人只做"点一下/选一个/回一句"

---

## 概述

构建一个"系统推着人走"的创意流水线，自动喂输入、生成候选、分配实验、收集证据、复盘归档。人只需"点一下/选一个/回一句"。

## 确认的设计决策

| 决策项 | 选择 |
|--------|------|
| 交互方式 | 钉钉流式网关（复用 lippi-code-agent 实现） |
| Agent架构 | 3 Agent：输入喂养器 + 创意工厂 + 实验执行器 |
| 数据存储 | Obsidian Markdown + YAML frontmatter |
| 行业覆盖 | 全覆盖（科技/AI + 金融 + 社会热点） |
| 运行方式 | Docker 容器化，VPS 部署 |
| Obsidian集成 | Docker volume 挂载共享目录 |

---

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Creativity Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Agent 1    │──│   Agent 2    │──│   Agent 3    │       │
│  │ Input Feeder │  │ Idea Factory │  │  MVP Runner  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                 │                │
│         ▼                 ▼                 ▼                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Obsidian Vault (Markdown Storage)           │   │
│  │  /cards/      /ideas/      /experiments/    /archive/ │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Scheduler (09:00/14:00/21:30)            │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     DingTalk Streaming Gateway (双向通信)             │   │
│  │     复用: lippi-code-agent/src/dingtalk/              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 项目结构

```
creativity-pipeline/
├── src/
│   ├── main.py                     # 入口 + 调度器
│   ├── config.py                   # 配置管理
│   │
│   ├── agents/                     # 3 个 Agent
│   │   ├── base_agent.py           # Agent 基类
│   │   ├── input_feeder.py         # Agent 1: 输入喂养器
│   │   ├── idea_factory.py         # Agent 2: 创意工厂
│   │   └── mvp_runner.py           # Agent 3: 实验执行器
│   │
│   ├── state/                      # 状态管理
│   │   ├── state_machine.py        # 流水线状态机
│   │   ├── obsidian_store.py       # Obsidian 读写
│   │   └── schemas.py              # frontmatter schema
│   │
│   ├── dingtalk/                   # 钉钉集成 (复用 lippi-code-agent)
│   │   ├── stream_client.py        # 流式连接管理
│   │   ├── message_callback.py     # 消息接收处理
│   │   ├── reply_service.py        # 消息发送服务
│   │   ├── stream_card.py          # 流式卡片
│   │   └── pipeline_handler.py     # 创意流水线专用处理器 (新增)
│   │
│   ├── data_sources/               # 数据源
│   │   ├── newsnow_adapter.py      # 复用 TrendRadar
│   │   └── extended_sources.py     # 扩展数据源
│   │
│   └── scheduler/
│       └── daily_scheduler.py      # 3次触达调度
│
├── config/
│   ├── config.yaml                 # 主配置
│   ├── industries.yaml             # 行业/数据源配置
│   └── prompts/                    # Agent prompts
│       ├── input_feeder.md
│       ├── idea_factory.md
│       └── mvp_runner.md
│
├── vault/                          # Obsidian (Docker volume)
│   ├── cards/
│   ├── ideas/
│   ├── experiments/
│   └── archive/
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh
│
└── requirements.txt
```

---

## 3. Obsidian Schema 设计

### Input Card (`/cards/YYYY-MM-DD-{id}.md`)

```yaml
---
id: card-2026-01-12-001
type: card
created: 2026-01-12T09:00:00+08:00
source: newsnow/zhihu
industry: tech/ai
category: change|pain_point|opportunity
keywords: [AI, 大模型, 降价]
status: pending|selected|processed|discarded
heat_score: 8500
---

# AI大模型降价潮

## 原始内容
...

## 变化/痛点分析
- **变化**: ...
- **影响群体**: ...
- **潜在机会**: ...
```

### Idea (`/ideas/YYYY-MM-DD-{id}.md`)

```yaml
---
id: idea-2026-01-12-001
type: idea
created: 2026-01-12T09:30:00+08:00
source_cards: [card-2026-01-12-001, card-2026-01-12-003]
title: "AI成本计算器"
one_liner: "输入用量，输出各家大模型月度成本对比"
target_user: "考虑使用大模型的创业者"
scores:
  feasibility: 9
  market_size: 7
  uniqueness: 6
  personal_fit: 8
  total: 30
status: candidate|top3|confirmed|in_progress|completed|discarded
downgrade_level: normal|lite
---

# AI成本计算器

## MVP定义
...
```

### Experiment (`/experiments/YYYY-MM-DD-{id}.md`)

```yaml
---
id: exp-2026-01-12-001
type: experiment
idea_id: idea-2026-01-12-001
downgrade_level: normal
estimated_time: 45
status: pending|in_progress|awaiting_evidence|completed|failed
wip_slot: true
tasks:
  - id: task-001
    description: "创建项目结构"
    status: pending
    time_estimate: 10
evidence:
  screenshots: []
  feedback: []
  retrospective: null
---
```

---

## 4. 钉钉集成方案

### 复用 lippi-code-agent 实现

**关键文件复用：**
- `stream_client.py` - DingTalkStreamManager 管理连接
- `message_callback_handler.py` - 消息接收
- `reply_service.py` - 消息发送
- `stream_card.py` - 流式卡片 UI

### 新增：PipelineCallbackHandler

```python
# src/dingtalk/pipeline_handler.py

class PipelineCallbackHandler(GraphHandler):
    """创意流水线专用消息处理器"""

    async def process(self, callback: CallbackMessage):
        context = MessageContext.from_dingtalk_message(callback.data)
        content = context.content.strip()

        # 解析用户选择
        selection = self.parse_selection(content)

        if selection["type"] == "select":
            await self.handle_selection(context, selection["value"])
        elif selection["type"] == "confirm":
            await self.handle_confirm(context)
        elif selection["type"] == "evidence":
            await self.handle_evidence(context, selection["value"])
        elif selection["type"] == "downgrade":
            await self.handle_downgrade(context)

    def parse_selection(self, content: str) -> dict:
        """解析: 1/2/3, 确认, 降级, 证据提交等"""
        if content.isdigit():
            return {"type": "select", "value": int(content)}
        if content in ["确认", "ok", "好"]:
            return {"type": "confirm", "value": None}
        if content in ["降级", "lite", "简单模式"]:
            return {"type": "downgrade", "value": None}
        # 其他内容视为证据或反馈
        return {"type": "evidence", "value": content}
```

### 消息卡片设计

**早间推送 (09:00):**
```
📊 今日Top3创意候选

1️⃣ AI成本计算器
   一句话: 输入用量,输出各家成本对比
   验证: 30分钟做个网页demo

2️⃣ 周报自动生成器
   一句话: 从日报聚合周报,一键生成
   验证: 15分钟写个脚本原型

3️⃣ 代码Review助手
   一句话: PR提交后自动生成review建议
   验证: 45分钟集成到GitHub

━━━━━━━━━━━━━━━━━━━━
回复 1/2/3 选择 | 回复「降级」进入简单模式
```

**下午推送 (14:00):**
```
🔧 今日实验任务包

选中创意: AI成本计算器

任务清单:
☐ [10分钟] 创建GitHub仓库+HTML结构
☐ [20分钟] 实现价格计算逻辑
☐ [15分钟] 部署Vercel+分享给3人

三人法则候选:
1. @张三 (AI创业者)
2. @李四 (独立开发者)
3. @王五 (产品经理)

━━━━━━━━━━━━━━━━━━━━
回复「开始」启动 | 回复「降级」切换5分钟任务
```

**晚间推送 (21:30):**
```
🌙 证据收集时间

今日实验: AI成本计算器
状态: 等待证据

请提交:
1. 截图/链接 (发送图片或URL)
2. 用户反馈 (至少1条原话)
3. 一句话复盘

━━━━━━━━━━━━━━━━━━━━
直接回复内容即可 | 回复「跳过」标记未完成
```

---

## 5. 数据源扩展

### 新增平台配置 (config/industries.yaml)

```yaml
industries:
  tech_ai:
    name: "科技/AI"
    sources:
      - id: zhihu
        name: 知乎
      - id: v2ex
        name: V2EX
      - id: 36kr
        name: 36氪
      - id: hackernews
        name: Hacker News
      - id: producthunt
        name: Product Hunt
      - id: github-trending
        name: GitHub Trending

  finance:
    name: "金融财经"
    sources:
      - id: wallstreetcn-hot
        name: 华尔街见闻
      - id: cls-hot
        name: 财联社
      - id: eastmoney
        name: 东方财富
      - id: xueqiu
        name: 雪球

  social:
    name: "社会热点"
    sources:
      - id: weibo
        name: 微博
      - id: douyin
        name: 抖音
      - id: toutiao
        name: 今日头条
      - id: baidu
        name: 百度热搜
      - id: bilibili-hot-search
        name: B站热搜
```

---

## 6. 状态机设计

```
┌─────────┐    选择卡片    ┌──────────┐   生成创意   ┌───────────┐
│  Input  │ ──────────────▶│  Cards   │ ────────────▶│   Ideas   │
│ (每日)  │                │ Selected │              │   Top3    │
└─────────┘                └──────────┘              └───────────┘
                                                           │
                                                     确认Top1
                                                           ▼
┌─────────┐    提交证据    ┌──────────┐   拆分任务   ┌───────────┐
│ Archive │ ◀──────────────│ Evidence │ ◀────────────│Experiment │
│  归档   │                │  收集    │              │   MVP     │
└─────────┘                └──────────┘              └───────────┘
      ▲                          │
      │                    无证据/超时
      │                          ▼
      │                    ┌──────────┐
      └────────────────────│ Downgrade│
           降级完成         │  降档    │
                           └──────────┘
```

### 状态机规则

1. **WIP=1**: 任何时候只有1个活跃实验
2. **证据门槛**: 无证据=未完成→自动降档
3. **三人法则**: 实验默认找3个用户验证
4. **复盘约束**: 下一步只能改1个变量

---

## 7. Docker 配置

### docker-compose.yml

```yaml
services:
  creativity-pipeline:
    build: .
    container_name: creativity-pipeline
    restart: unless-stopped
    volumes:
      - ${OBSIDIAN_VAULT_PATH}:/vault
      - ./config:/app/config:ro
      - ./logs:/app/logs
    environment:
      - TZ=Asia/Shanghai
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DINGTALK_CLIENT_ID=${DINGTALK_CLIENT_ID}
      - DINGTALK_CLIENT_SECRET=${DINGTALK_CLIENT_SECRET}
      - DINGTALK_CORP_ID=${DINGTALK_CORP_ID}
      - MORNING_PUSH_TIME=09:00
      - AFTERNOON_PUSH_TIME=14:00
      - EVENING_PUSH_TIME=21:30
```

---

## 8. 关键文件引用

| 文件 | 用途 |
|------|------|
| `/Users/yixuan.yhl/developers/lippi-code-agent/src/dingtalk/` | 钉钉流式网关完整实现，直接复用 |
| `/Users/yixuan.yhl/developers/TrendRadar/main.py` (434-552) | DataFetcher 类，复用数据抓取 |
| `/Users/yixuan.yhl/developers/TrendRadar/config/config.yaml` | 平台配置参考 |
| `/Users/yixuan.yhl/developers/TrendRadar/docker/` | Docker 配置参考 |

---

## 9. Claude Agent SDK 实现方案

### 依赖安装

```bash
pip install claude-agent-sdk
# 还需要安装 Claude Code CLI
npm install -g @anthropic-ai/claude-code
```

### Agent 实现模式

使用 `ClaudeSDKClient` 保持会话连续性，支持多轮对话：

```python
# src/agents/base_agent.py

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock
)
from typing import Any

# 定义 Obsidian 操作工具
@tool("read_cards", "Read input cards from Obsidian", {"date": str, "status": str})
async def read_cards(args: dict[str, Any]) -> dict[str, Any]:
    cards = obsidian_store.read_cards(args["date"], args["status"])
    return {"content": [{"type": "text", "text": json.dumps(cards, ensure_ascii=False)}]}

@tool("write_idea", "Write idea to Obsidian", {"idea": dict})
async def write_idea(args: dict[str, Any]) -> dict[str, Any]:
    path = obsidian_store.write_idea(args["idea"])
    return {"content": [{"type": "text", "text": f"Idea saved to {path}"}]}

@tool("update_status", "Update item status", {"id": str, "status": str})
async def update_status(args: dict[str, Any]) -> dict[str, Any]:
    obsidian_store.update_status(args["id"], args["status"])
    return {"content": [{"type": "text", "text": f"Status updated: {args['id']} -> {args['status']}"}]}

# 创建 MCP Server
obsidian_server = create_sdk_mcp_server(
    name="obsidian",
    version="1.0.0",
    tools=[read_cards, write_idea, update_status]
)

class BaseAgent:
    """Agent 基类，使用 Claude Agent SDK"""

    def __init__(self, system_prompt: str):
        self.options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            mcp_servers={"obsidian": obsidian_server},
            allowed_tools=[
                "mcp__obsidian__read_cards",
                "mcp__obsidian__write_idea",
                "mcp__obsidian__update_status"
            ],
            permission_mode="acceptEdits"
        )

    async def run(self, prompt: str) -> str:
        """执行 Agent 任务"""
        result = []
        async with ClaudeSDKClient(self.options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            result.append(block.text)
        return "\n".join(result)
```

### 3 个 Agent 定义

```python
# src/agents/input_feeder.py

INPUT_FEEDER_PROMPT = """
你是输入喂养器 Agent。任务是将原始新闻数据转化为结构化的"变化/痛点"卡片。

## 输出要求
为每条有价值的新闻生成卡片，包含：
- category: change | pain_point | opportunity
- industry: tech/ai | finance | social
- keywords: 3-5个关键词
- 变化/痛点分析：发生了什么变化？谁受影响？有什么机会？

## 筛选标准
1. 有明确可衡量的变化
2. 影响特定可识别的群体
3. 在2+平台出现（有验证性）

每天生成10张高质量卡片。
"""

class InputFeederAgent(BaseAgent):
    def __init__(self):
        super().__init__(INPUT_FEEDER_PROMPT)

    async def generate_daily_cards(self, raw_data: list) -> list:
        prompt = f"请从以下原始数据生成10张输入卡片：\n\n{json.dumps(raw_data, ensure_ascii=False)}"
        return await self.run(prompt)
```

```python
# src/agents/idea_factory.py

IDEA_FACTORY_PROMPT = """
你是创意工厂 Agent。任务是从输入卡片生成创意，并筛选出 Top 3。

## 生成框架
对每张选中的卡片，从5个角度生成创意：
1. 工具/效率：什么工具能解决？
2. 内容/媒体：什么内容能回应？
3. 社区：能形成什么社区？
4. 服务：能提供什么服务？
5. 套利：存在什么信息不对称？

## 评分标准
- 可行性 (30%): 一个人能在1小时内做出MVP吗？
- 市场验证 (25%): 有需求证据吗？
- 个人匹配 (25%): 符合用户技能/兴趣吗？
- 独特性 (20%): 有明确差异化吗？

## 输出
生成20个创意，筛选出Top 3，每个包含：
- title: 简短标题
- one_liner: 一句话价值主张
- target_user: 具体目标用户
- mvp_time: 30|60 分钟
- 降级版本: 5分钟能做的最小验证
"""

class IdeaFactoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(IDEA_FACTORY_PROMPT)
```

```python
# src/agents/mvp_runner.py

MVP_RUNNER_PROMPT = """
你是 MVP 执行器 Agent。任务是将确认的创意拆解为可执行任务。

## 任务拆解原则
每个任务必须有：
1. 明确交付物：产出什么？
2. 时间盒：严格限时(5/10/15/20分钟)
3. 成功标准：怎么判断完成？

## 标准任务模板
软件MVP：
1. 创建项目+核心结构 (10分钟)
2. 实现主功能 (20分钟)
3. 部署+分享给3人 (15分钟)

## 三人法则
每个实验必须：
- 识别3个具体的测试用户
- 获取至少1条反馈
- 记录用户反应

## 降级协议
如果用户无法完成正常任务，提供5分钟替代：
- 发1条社交媒体询问
- 用AI生成一张概念图
- 给1个潜在用户发消息
"""

class MVPRunnerAgent(BaseAgent):
    def __init__(self):
        super().__init__(MVP_RUNNER_PROMPT)
```

---

## 10. 实施步骤

### Phase 1: 基础搭建
1. 创建项目结构
2. 复制 dingtalk 模块并适配 (`lippi-code-agent/src/dingtalk/`)
3. 实现 Obsidian 读写 (obsidian_store.py)
4. 配置 Docker + Supercronic

### Phase 2: Agent 实现
1. 安装 Claude Agent SDK + Claude Code CLI
2. 实现 base_agent.py 使用 `ClaudeSDKClient`
3. 定义 Obsidian MCP 工具 (`@tool` 装饰器)
4. 实现 3 个 Agent (InputFeeder, IdeaFactory, MVPRunner)

### Phase 3: 流水线集成
1. 实现状态机
2. 实现 PipelineCallbackHandler (接收钉钉消息)
3. 集成定时调度 (3次触达: 09:00/14:00/21:30)
4. 实现降档机制

### Phase 4: 部署测试
1. Docker 构建测试
2. 钉钉流式连接测试
3. Agent 输出质量测试
4. 端到端流程验证
5. VPS 部署

---

## 11. 验证方案

1. **钉钉连接测试**: 验证流式网关收发消息
2. **Agent 单元测试**: 测试每个 Agent 的输出质量
3. **状态机测试**: 模拟 Input→Idea→MVP→Evidence→Archive 流程
4. **端到端测试**: 跑一天完整周期，验证3次触达正常
5. **降档测试**: 验证超时自动降档机制

---

## 12. 团队协作分工（3人并行开发）

### 分工总览

| 角色 | 负责模块 | 核心任务 | 交付物 |
|------|----------|----------|--------|
| **开发者A** | 钉钉集成层 | 消息收发、用户交互 | dingtalk/ 模块 |
| **开发者B** | Agent层 | 3个Agent实现 | agents/ 模块 |
| **开发者C** | 状态管理层 | Obsidian存储、状态机、调度器 | state/ + scheduler/ 模块 |

### 依赖关系

```
开发者C (状态层)  ──────────────────────────────────────┐
     │                                                   │
     │ 提供接口: ObsidianStore, StateMachine            │
     ▼                                                   │
开发者B (Agent层)                                        │
     │                                                   │
     │ 提供接口: InputFeeder, IdeaFactory, MVPRunner    │
     ▼                                                   │
开发者A (钉钉层)  ◀──────────────────────────────────────┘
     │
     │ 提供接口: DingTalkService (发送/接收)
     ▼
   main.py (入口集成)
```

**建议开发顺序**：C → B → A（状态层先行，Agent层次之，钉钉层最后）

---

### 开发者A：钉钉集成层

#### 职责范围
负责系统与用户之间的所有交互，包括消息接收、解析、响应发送。

#### 具体任务

| 任务 | 描述 | 参考代码 |
|------|------|----------|
| A1. 复制钉钉模块 | 从 lippi-code-agent 复制 dingtalk/ 目录 | `/Users/yixuan.yhl/developers/lippi-code-agent/src/dingtalk/` |
| A2. 适配 PipelineHandler | 新增 pipeline_handler.py，处理创意流水线专用消息 | 见下方代码模板 |
| A3. 消息解析器 | 实现 parse_selection()，支持数字选择、关键词命令 | `1/2/3`, `确认`, `降级` |
| A4. 卡片模板 | 设计3种消息卡片（早间/下午/晚间） | Markdown 格式 |
| A5. 集成测试 | 验证消息收发完整链路 | 发送测试消息，验证回复 |

#### 代码模板

```python
# src/dingtalk/pipeline_handler.py

from dingtalk_stream import GraphHandler, CallbackMessage
from .message_context import MessageContext

class PipelineCallbackHandler(GraphHandler):
    """创意流水线消息处理器"""

    def __init__(self, state_machine, agents):
        self.state_machine = state_machine
        self.agents = agents

    async def process(self, callback: CallbackMessage):
        context = MessageContext.from_dingtalk_message(callback.data)
        selection = self.parse_selection(context.content.strip())

        handlers = {
            "select": self._handle_selection,
            "confirm": self._handle_confirm,
            "evidence": self._handle_evidence,
            "downgrade": self._handle_downgrade,
            "start": self._handle_start,
        }

        handler = handlers.get(selection["type"], self._handle_unknown)
        await handler(context, selection["value"])

    def parse_selection(self, content: str) -> dict:
        """解析用户输入"""
        content = content.lower().strip()

        # 数字选择
        if content.isdigit():
            return {"type": "select", "value": int(content)}

        # 多选: 1,2,3
        if "," in content:
            nums = [int(x) for x in content.split(",") if x.strip().isdigit()]
            return {"type": "select", "value": nums}

        # 关键词映射
        keywords = {
            "确认": "confirm", "ok": "confirm", "好": "confirm",
            "开始": "start", "start": "start",
            "降级": "downgrade", "lite": "downgrade",
            "跳过": "skip", "skip": "skip",
        }

        for kw, action in keywords.items():
            if kw in content:
                return {"type": action, "value": None}

        # 默认视为证据提交
        return {"type": "evidence", "value": content}

    async def _handle_selection(self, context, value):
        """处理选择操作"""
        self.state_machine.record_selection(value)
        await self._send_confirmation(context, f"已选择: {value}")

    async def _handle_confirm(self, context, value):
        """确认 Top1"""
        idea = self.state_machine.confirm_top1()
        tasks = await self.agents["mvp_runner"].generate_tasks(idea)
        await self._send_tasks(context, tasks)

    async def _handle_evidence(self, context, value):
        """记录证据"""
        self.state_machine.record_evidence(value)
        await self._send_confirmation(context, "证据已记录")

    async def _handle_downgrade(self, context, value):
        """触发降级"""
        self.state_machine.trigger_downgrade()
        await self._send_downgrade_tasks(context)
```

#### 对外接口（供其他模块调用）

```python
class DingTalkService:
    async def send_morning_push(self, cards: list, ideas: list) -> bool
    async def send_afternoon_push(self, experiment: dict) -> bool
    async def send_evening_push(self, experiment: dict) -> bool
    async def send_message(self, content: str) -> bool
```

#### 交付检查清单
- [ ] 钉钉流式连接成功
- [ ] 能接收群消息
- [ ] 能解析用户输入（数字、关键词）
- [ ] 能发送 Markdown 卡片
- [ ] 单元测试覆盖核心解析逻辑

---

### 开发者B：Agent 层

#### 职责范围
实现3个Claude Agent，负责创意生成的核心智能。

#### 具体任务

| 任务 | 描述 | 依赖 |
|------|------|------|
| B1. 安装 SDK | `pip install claude-agent-sdk` + Claude Code CLI | 无 |
| B2. BaseAgent | 实现 Agent 基类，封装 ClaudeSDKClient | 无 |
| B3. Obsidian MCP Tools | 定义 @tool 装饰器工具 | 需要 C 的 ObsidianStore |
| B4. InputFeederAgent | 输入喂养器，生成变化/痛点卡片 | B2 + B3 |
| B5. IdeaFactoryAgent | 创意工厂，生成并筛选 Top3 | B2 + B3 |
| B6. MVPRunnerAgent | 实验执行器，拆解任务 | B2 + B3 |
| B7. Prompt 调优 | 优化 Agent 输出质量 | B4-B6 完成后 |

#### 代码模板

```python
# src/agents/base_agent.py

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock
)
from typing import Any
import json

# 需要从 state 模块导入
from state.obsidian_store import obsidian_store

# === Obsidian MCP 工具定义 ===

@tool("read_cards", "读取输入卡片", {"date": str, "status": str})
async def read_cards(args: dict[str, Any]) -> dict[str, Any]:
    """从 Obsidian 读取指定日期和状态的卡片"""
    cards = obsidian_store.read_cards(args["date"], args.get("status", "pending"))
    return {"content": [{"type": "text", "text": json.dumps(cards, ensure_ascii=False)}]}

@tool("write_card", "写入输入卡片", {"card": dict})
async def write_card(args: dict[str, Any]) -> dict[str, Any]:
    """写入新的输入卡片到 Obsidian"""
    path = obsidian_store.write_card(args["card"])
    return {"content": [{"type": "text", "text": f"Card saved to {path}"}]}

@tool("write_idea", "写入创意", {"idea": dict})
async def write_idea(args: dict[str, Any]) -> dict[str, Any]:
    """写入新的创意到 Obsidian"""
    path = obsidian_store.write_idea(args["idea"])
    return {"content": [{"type": "text", "text": f"Idea saved to {path}"}]}

@tool("update_status", "更新状态", {"id": str, "status": str})
async def update_status(args: dict[str, Any]) -> dict[str, Any]:
    """更新项目状态"""
    obsidian_store.update_status(args["id"], args["status"])
    return {"content": [{"type": "text", "text": f"Status updated: {args['id']} -> {args['status']}"}]}

@tool("get_selected_cards", "获取已选择的卡片", {})
async def get_selected_cards(args: dict[str, Any]) -> dict[str, Any]:
    """获取用户选择的卡片"""
    cards = obsidian_store.get_cards_by_status("selected")
    return {"content": [{"type": "text", "text": json.dumps(cards, ensure_ascii=False)}]}

# === MCP Server 创建 ===

obsidian_server = create_sdk_mcp_server(
    name="obsidian",
    version="1.0.0",
    tools=[read_cards, write_card, write_idea, update_status, get_selected_cards]
)

# === Agent 基类 ===

class BaseAgent:
    """Agent 基类"""

    def __init__(self, system_prompt: str, model: str = "claude-sonnet-4-20250514"):
        self.system_prompt = system_prompt
        self.options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=model,
            mcp_servers={"obsidian": obsidian_server},
            allowed_tools=[
                "mcp__obsidian__read_cards",
                "mcp__obsidian__write_card",
                "mcp__obsidian__write_idea",
                "mcp__obsidian__update_status",
                "mcp__obsidian__get_selected_cards",
            ],
            permission_mode="acceptEdits"
        )

    async def run(self, prompt: str) -> str:
        """执行 Agent 任务"""
        result = []
        async with ClaudeSDKClient(self.options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            result.append(block.text)
        return "\n".join(result)

    async def run_with_data(self, prompt: str, data: dict) -> str:
        """带数据执行 Agent 任务"""
        full_prompt = f"{prompt}\n\n数据：\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"
        return await self.run(full_prompt)
```

```python
# src/agents/input_feeder.py

from .base_agent import BaseAgent

INPUT_FEEDER_PROMPT = """
你是输入喂养器 Agent。任务是将原始新闻数据转化为结构化的"变化/痛点"卡片。

## 输出格式
对每条有价值的新闻，生成一张卡片，包含：
```yaml
id: card-{日期}-{序号}
category: change | pain_point | opportunity
industry: tech/ai | finance | social
keywords: [关键词1, 关键词2, 关键词3]
title: 简短标题
content: 原始内容摘要
analysis:
  change: 发生了什么变化
  affected: 谁受到影响
  opportunity: 潜在机会是什么
heat_score: 1-10 (基于跨平台出现次数)
```

## 筛选标准
1. 有明确、可衡量的变化（不是模糊趋势）
2. 影响特定、可识别的群体
3. 在2个以上平台出现（有验证性）
4. 不超过7天前的新闻

## 数量要求
每天输出 10 张高质量卡片。

请使用 write_card 工具保存每张卡片。
"""

class InputFeederAgent(BaseAgent):
    def __init__(self):
        super().__init__(INPUT_FEEDER_PROMPT)

    async def generate_daily_cards(self, raw_news: list) -> list:
        """从原始新闻生成输入卡片"""
        prompt = "请从以下原始新闻数据中生成10张高质量输入卡片："
        return await self.run_with_data(prompt, {"news": raw_news})
```

```python
# src/agents/idea_factory.py

from .base_agent import BaseAgent

IDEA_FACTORY_PROMPT = """
你是创意工厂 Agent。任务是从输入卡片生成创意，并筛选出 Top 3。

## 生成框架
对每张选中的卡片，从5个角度生成创意：
1. **工具/效率**：什么工具能解决这个问题？
2. **内容/媒体**：什么内容能回应这个变化？
3. **社区**：能围绕这个形成什么社区？
4. **服务**：能提供什么服务？
5. **套利**：存在什么信息不对称可以利用？

## 评分维度（总分40分）
- 可行性 (10分): 一个人能在1小时内做出MVP吗？
- 市场验证 (10分): 有需求证据吗？能找到3个愿意试用的人吗？
- 个人匹配 (10分): 符合用户的技能和兴趣吗？
- 独特性 (10分): 有明确的差异化角度吗？

## 输出格式
```yaml
id: idea-{日期}-{序号}
title: 简短有力的标题（不超过15字）
one_liner: 一句话价值主张（不超过50字）
target_user: 具体的目标用户描述
problem: 解决什么问题
unique_angle: 差异化角度
mvp_time: 30 | 60 (分钟)
scores:
  feasibility: 1-10
  market: 1-10
  personal_fit: 1-10
  uniqueness: 1-10
  total: 总分
downgrade_version: 5分钟能做的最小验证
source_cards: [引用的卡片ID列表]
```

## 筛选规则
1. 生成20个创意
2. 按总分排序，选出 Top 3
3. Top 3 中至少有1个"稳妥型"（可行性>=8）
4. Top 3 中至少有1个"创新型"（独特性>=8）
5. 确保 Top 3 来自不同的输入卡片

请使用 get_selected_cards 获取用户选择的卡片，然后使用 write_idea 保存生成的创意。
"""

class IdeaFactoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(IDEA_FACTORY_PROMPT)

    async def generate_ideas(self) -> list:
        """从选中的卡片生成创意"""
        prompt = "请获取用户选择的卡片，生成20个创意，并筛选出Top 3。"
        return await self.run(prompt)
```

```python
# src/agents/mvp_runner.py

from .base_agent import BaseAgent

MVP_RUNNER_PROMPT = """
你是 MVP 执行器 Agent。任务是将确认的创意拆解为可执行任务。

## 任务拆解原则
每个任务必须有：
1. **明确交付物**：产出什么具体的东西？
2. **时间盒**：严格限时（5/10/15/20分钟）
3. **成功标准**：怎么判断完成了？
4. **工具/资源**：需要用到什么？

## 标准任务模板

### 软件MVP（45分钟）
1. [10分钟] 创建项目 + 核心结构
2. [20分钟] 实现主功能（可用AI辅助）
3. [15分钟] 部署 + 分享给3人

### 内容MVP（30分钟）
1. [5分钟] 列出大纲
2. [15分钟] 生成/撰写内容
3. [10分钟] 发布 + 分发

### 调研MVP（40分钟）
1. [10分钟] 定义假设和问题
2. [20分钟] 访谈/问卷
3. [10分钟] 整理发现

## 三人法则
每个实验必须包含：
- 识别3个具体的测试用户（给出建议类型）
- 准备招募话术（可直接复制）
- 记录反馈的模板

## 降级任务（5分钟版）
必须同时提供一个5分钟降级版本：
- 发1条社交媒体询问
- 用AI生成1张概念图
- 给1个潜在用户发消息
- 做1个简单投票

## 输出格式
```yaml
experiment:
  idea_id: 引用的创意ID
  idea_title: 创意标题
  downgrade_level: normal
  estimated_time: 45
  tasks:
    - id: task-001
      description: 任务描述
      time_estimate: 10
      deliverable: 具体交付物
      success_criteria: 完成标准
      tools: [需要的工具]
    - ...

  three_person_rule:
    target_profiles:
      - type: "AI创业者"
        where_to_find: "Twitter/即刻"
      - type: "独立开发者"
        where_to_find: "V2EX/GitHub"
      - type: "产品经理"
        where_to_find: "人人都是产品经理"
    recruit_script: |
      嗨，我在做一个小实验：{one_liner}
      想邀请你花5分钟试用一下，给点反馈。
      感兴趣吗？
    feedback_template: |
      用户:
      第一反应:
      是否愿意继续使用:
      改进建议:

  downgrade_version:
    description: 5分钟降级任务
    task: 具体要做什么
    expected_evidence: 需要提交的证据
```
"""

class MVPRunnerAgent(BaseAgent):
    def __init__(self):
        super().__init__(MVP_RUNNER_PROMPT)

    async def generate_tasks(self, idea: dict) -> dict:
        """为创意生成任务包"""
        prompt = "请为以下创意生成详细的MVP任务包："
        return await self.run_with_data(prompt, idea)
```

#### 对外接口（供其他模块调用）

```python
# 每个 Agent 的接口
class InputFeederAgent:
    async def generate_daily_cards(self, raw_news: list) -> list[Card]

class IdeaFactoryAgent:
    async def generate_ideas(self) -> list[Idea]

class MVPRunnerAgent:
    async def generate_tasks(self, idea: Idea) -> Experiment
```

#### 交付检查清单
- [ ] Claude Agent SDK 安装成功
- [ ] BaseAgent 能正常调用 Claude API
- [ ] Obsidian MCP 工具能读写文件
- [ ] InputFeederAgent 生成格式正确的卡片
- [ ] IdeaFactoryAgent 生成并筛选 Top3
- [ ] MVPRunnerAgent 生成可执行任务包
- [ ] 输出质量符合预期

---

### 开发者C：状态管理层

#### 职责范围
负责数据持久化、状态流转、定时调度。

#### 具体任务

| 任务 | 描述 | 依赖 |
|------|------|------|
| C1. ObsidianStore | Obsidian Markdown 读写，支持 frontmatter | 无 |
| C2. Schema 定义 | Card/Idea/Experiment 的 YAML schema | C1 |
| C3. StateMachine | 状态流转逻辑 | C1 + C2 |
| C4. DailyScheduler | 3次触达定时调度 | 无 |
| C5. 数据源适配 | 复用 TrendRadar DataFetcher | C1 |
| C6. Docker 配置 | Dockerfile + docker-compose.yml | 无 |

#### 代码模板

```python
# src/state/obsidian_store.py

import os
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

class ObsidianStore:
    """Obsidian Markdown 文件存储"""

    def __init__(self, vault_path: str = "/vault"):
        self.vault_path = Path(vault_path)
        self.cards_dir = self.vault_path / "cards"
        self.ideas_dir = self.vault_path / "ideas"
        self.experiments_dir = self.vault_path / "experiments"
        self.archive_dir = self.vault_path / "archive"

        # 确保目录存在
        for dir_path in [self.cards_dir, self.ideas_dir, self.experiments_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """解析 YAML frontmatter"""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return frontmatter, body
        return {}, content

    def _render_markdown(self, frontmatter: dict, body: str) -> str:
        """渲染 Markdown 文件"""
        yaml_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
        return f"---\n{yaml_str}---\n\n{body}"

    def _get_today_prefix(self) -> str:
        """获取今日日期前缀"""
        return datetime.now().strftime("%Y-%m-%d")

    # === Card 操作 ===

    def read_cards(self, date: str = None, status: str = None) -> List[Dict]:
        """读取卡片"""
        date = date or self._get_today_prefix()
        cards = []

        for file_path in self.cards_dir.glob(f"{date}*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = self._parse_frontmatter(f.read())
                if status is None or frontmatter.get("status") == status:
                    cards.append({**frontmatter, "body": body, "path": str(file_path)})

        return cards

    def write_card(self, card: dict) -> str:
        """写入卡片"""
        card_id = card.get("id") or f"card-{self._get_today_prefix()}-{self._next_seq('cards')}"
        card["id"] = card_id
        card["created"] = card.get("created") or datetime.now().isoformat()
        card["status"] = card.get("status") or "pending"

        body = self._generate_card_body(card)
        content = self._render_markdown(card, body)

        file_path = self.cards_dir / f"{card_id}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def get_cards_by_status(self, status: str) -> List[Dict]:
        """按状态获取卡片"""
        cards = []
        for file_path in self.cards_dir.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = self._parse_frontmatter(f.read())
                if frontmatter.get("status") == status:
                    cards.append({**frontmatter, "body": body})
        return cards

    # === Idea 操作 ===

    def write_idea(self, idea: dict) -> str:
        """写入创意"""
        idea_id = idea.get("id") or f"idea-{self._get_today_prefix()}-{self._next_seq('ideas')}"
        idea["id"] = idea_id
        idea["created"] = idea.get("created") or datetime.now().isoformat()
        idea["status"] = idea.get("status") or "candidate"

        body = self._generate_idea_body(idea)
        content = self._render_markdown(idea, body)

        file_path = self.ideas_dir / f"{idea_id}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    # === Experiment 操作 ===

    def write_experiment(self, experiment: dict) -> str:
        """写入实验"""
        exp_id = experiment.get("id") or f"exp-{self._get_today_prefix()}-{self._next_seq('experiments')}"
        experiment["id"] = exp_id
        experiment["created"] = experiment.get("created") or datetime.now().isoformat()
        experiment["status"] = experiment.get("status") or "pending"

        body = self._generate_experiment_body(experiment)
        content = self._render_markdown(experiment, body)

        file_path = self.experiments_dir / f"{exp_id}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def get_active_experiment(self) -> Optional[Dict]:
        """获取活跃实验（WIP=1）"""
        for file_path in self.experiments_dir.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = self._parse_frontmatter(f.read())
                if frontmatter.get("status") in ["pending", "in_progress", "awaiting_evidence"]:
                    return {**frontmatter, "body": body, "path": str(file_path)}
        return None

    # === 状态更新 ===

    def update_status(self, item_id: str, new_status: str) -> bool:
        """更新项目状态"""
        # 根据 ID 前缀确定目录
        if item_id.startswith("card-"):
            directory = self.cards_dir
        elif item_id.startswith("idea-"):
            directory = self.ideas_dir
        elif item_id.startswith("exp-"):
            directory = self.experiments_dir
        else:
            return False

        file_path = directory / f"{item_id}.md"
        if not file_path.exists():
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            frontmatter, body = self._parse_frontmatter(f.read())

        frontmatter["status"] = new_status
        frontmatter["updated"] = datetime.now().isoformat()

        content = self._render_markdown(frontmatter, body)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True

    # === 辅助方法 ===

    def _next_seq(self, type_name: str) -> str:
        """生成下一个序号"""
        today = self._get_today_prefix()
        if type_name == "cards":
            existing = list(self.cards_dir.glob(f"card-{today}*.md"))
        elif type_name == "ideas":
            existing = list(self.ideas_dir.glob(f"idea-{today}*.md"))
        else:
            existing = list(self.experiments_dir.glob(f"exp-{today}*.md"))
        return f"{len(existing) + 1:03d}"

    def _generate_card_body(self, card: dict) -> str:
        """生成卡片正文"""
        analysis = card.get("analysis", {})
        return f"""# {card.get('title', 'Untitled')}

## 原始内容
{card.get('content', '')}

## 变化/痛点分析
- **变化**: {analysis.get('change', '')}
- **影响群体**: {analysis.get('affected', '')}
- **潜在机会**: {analysis.get('opportunity', '')}
"""

    def _generate_idea_body(self, idea: dict) -> str:
        """生成创意正文"""
        return f"""# {idea.get('title', 'Untitled')}

## 价值主张
{idea.get('one_liner', '')}

## 目标用户
{idea.get('target_user', '')}

## 解决问题
{idea.get('problem', '')}

## 差异化角度
{idea.get('unique_angle', '')}

## MVP 定义
预计时间: {idea.get('mvp_time', 30)} 分钟

## 降级版本
{idea.get('downgrade_version', '')}
"""

    def _generate_experiment_body(self, exp: dict) -> str:
        """生成实验正文"""
        tasks = exp.get('tasks', [])
        tasks_md = "\n".join([f"- [ ] [{t.get('time_estimate', 10)}分钟] {t.get('description', '')}" for t in tasks])

        return f"""# 实验: {exp.get('idea_title', 'Untitled')}

## 任务清单
{tasks_md}

## 三人法则
待补充

## 证据区
> 请在此区域提交证据

## 复盘
待补充
"""


# 全局单例
obsidian_store = ObsidianStore(os.environ.get("VAULT_PATH", "/vault"))
```

```python
# src/state/state_machine.py

from typing import Optional, List, Dict
from datetime import datetime
from .obsidian_store import obsidian_store

class PipelineStateMachine:
    """创意流水线状态机"""

    def __init__(self):
        self.store = obsidian_store

    # === 卡片选择 ===

    def record_selection(self, indices: List[int]) -> List[Dict]:
        """记录用户选择的卡片"""
        today_cards = self.store.read_cards(status="pending")

        selected = []
        for idx in indices:
            if 1 <= idx <= len(today_cards):
                card = today_cards[idx - 1]
                self.store.update_status(card["id"], "selected")
                selected.append(card)

        return selected

    def get_selected_cards(self) -> List[Dict]:
        """获取已选择的卡片"""
        return self.store.get_cards_by_status("selected")

    # === 创意确认 ===

    def confirm_top1(self, idea_index: int = 1) -> Optional[Dict]:
        """确认 Top1 创意"""
        ideas = self._get_today_ideas(status="top3")

        if 1 <= idea_index <= len(ideas):
            idea = ideas[idea_index - 1]
            self.store.update_status(idea["id"], "confirmed")
            return idea
        return None

    def get_confirmed_idea(self) -> Optional[Dict]:
        """获取已确认的创意"""
        ideas = self._get_today_ideas(status="confirmed")
        return ideas[0] if ideas else None

    # === 实验管理 ===

    def has_active_experiment(self) -> bool:
        """是否有活跃实验（WIP=1）"""
        return self.store.get_active_experiment() is not None

    def create_experiment(self, idea: Dict, tasks: Dict) -> Dict:
        """创建实验"""
        experiment = {
            "idea_id": idea["id"],
            "idea_title": idea["title"],
            "downgrade_level": "normal",
            "estimated_time": tasks.get("estimated_time", 45),
            "tasks": tasks.get("tasks", []),
            "status": "pending",
            "wip_slot": True,
        }
        self.store.write_experiment(experiment)
        return experiment

    def get_active_experiment(self) -> Optional[Dict]:
        """获取活跃实验"""
        return self.store.get_active_experiment()

    def set_awaiting_evidence(self, exp_id: str) -> bool:
        """设置等待证据状态"""
        return self.store.update_status(exp_id, "awaiting_evidence")

    # === 证据与降级 ===

    def record_evidence(self, evidence: str) -> bool:
        """记录证据"""
        exp = self.store.get_active_experiment()
        if not exp:
            return False

        # 更新实验文件，添加证据
        # TODO: 实现证据追加逻辑
        self.store.update_status(exp["id"], "completed")
        return True

    def trigger_downgrade(self, exp_id: str = None) -> bool:
        """触发降级"""
        exp = self.store.get_active_experiment() if not exp_id else None
        if not exp:
            return False

        # 更新降级状态
        # TODO: 实现降级逻辑
        return True

    # === 辅助方法 ===

    def _get_today_ideas(self, status: str = None) -> List[Dict]:
        """获取今日创意"""
        today = datetime.now().strftime("%Y-%m-%d")
        ideas = []

        for file_path in self.store.ideas_dir.glob(f"idea-{today}*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = self.store._parse_frontmatter(f.read())
                if status is None or frontmatter.get("status") == status:
                    ideas.append({**frontmatter, "body": body})

        return ideas

    def record_morning_push(self, cards: List, ideas: List):
        """记录早间推送"""
        # TODO: 记录推送历史
        pass
```

```python
# src/scheduler/daily_scheduler.py

import asyncio
from datetime import datetime, time
from typing import Callable, Awaitable

class DailyScheduler:
    """每日调度器 - 3次触达"""

    TOUCH_POINTS = {
        "morning": time(9, 0),    # 09:00
        "afternoon": time(14, 0), # 14:00
        "evening": time(21, 30),  # 21:30
    }

    def __init__(
        self,
        morning_handler: Callable[[], Awaitable[None]],
        afternoon_handler: Callable[[], Awaitable[None]],
        evening_handler: Callable[[], Awaitable[None]],
    ):
        self.handlers = {
            "morning": morning_handler,
            "afternoon": afternoon_handler,
            "evening": evening_handler,
        }
        self._running = False

    async def run_touch_point(self, name: str):
        """执行指定触达点"""
        handler = self.handlers.get(name)
        if handler:
            try:
                await handler()
            except Exception as e:
                print(f"[{name}] Error: {e}")

    async def check_and_run(self):
        """检查并执行到期的触达点"""
        now = datetime.now().time()

        for name, target_time in self.TOUCH_POINTS.items():
            # 检查是否在触达时间的1分钟窗口内
            if self._is_within_window(now, target_time, minutes=1):
                print(f"[Scheduler] Triggering {name} push")
                await self.run_touch_point(name)

    def _is_within_window(self, current: time, target: time, minutes: int = 1) -> bool:
        """检查当前时间是否在目标时间窗口内"""
        current_minutes = current.hour * 60 + current.minute
        target_minutes = target.hour * 60 + target.minute
        return abs(current_minutes - target_minutes) < minutes

    async def start(self):
        """启动调度器"""
        self._running = True
        print("[Scheduler] Started")

        while self._running:
            await self.check_and_run()
            await asyncio.sleep(60)  # 每分钟检查一次

    def stop(self):
        """停止调度器"""
        self._running = False
```

#### 对外接口

```python
# ObsidianStore
class ObsidianStore:
    def read_cards(self, date: str, status: str) -> List[Dict]
    def write_card(self, card: dict) -> str
    def write_idea(self, idea: dict) -> str
    def write_experiment(self, experiment: dict) -> str
    def update_status(self, id: str, status: str) -> bool
    def get_active_experiment(self) -> Optional[Dict]
    def get_cards_by_status(self, status: str) -> List[Dict]

# StateMachine
class PipelineStateMachine:
    def record_selection(self, indices: List[int]) -> List[Dict]
    def confirm_top1(self, index: int) -> Optional[Dict]
    def create_experiment(self, idea: Dict, tasks: Dict) -> Dict
    def record_evidence(self, evidence: str) -> bool
    def trigger_downgrade(self, exp_id: str) -> bool
    def has_active_experiment(self) -> bool

# Scheduler
class DailyScheduler:
    async def run_touch_point(self, name: str)
    async def start()
    def stop()
```

#### 交付检查清单
- [ ] ObsidianStore 能正确读写 Markdown + frontmatter
- [ ] StateMachine 状态流转正确
- [ ] DailyScheduler 定时触发正常
- [ ] Docker 配置完整可用
- [ ] 数据源能获取多平台新闻

---

## 13. 集成与联调

### 集成顺序

1. **C 完成后** → B 可以开始（使用 ObsidianStore）
2. **B 完成后** → A 可以集成（调用 Agents）
3. **A 完成后** → 联调 main.py 入口

### 联调检查点

| 检查点 | 负责人 | 验证内容 |
|--------|--------|----------|
| CP1 | C | Obsidian 文件读写正常 |
| CP2 | B + C | Agent 能通过 MCP 工具操作 Obsidian |
| CP3 | A + C | 钉钉消息能触发状态变更 |
| CP4 | A + B | 钉钉能展示 Agent 生成的内容 |
| CP5 | All | 完整流程：早间→选择→下午→执行→晚间→证据 |

### main.py 入口（集成后）

```python
# src/main.py

import asyncio
import os

from dingtalk.stream_client import DingTalkStreamManager
from dingtalk.pipeline_handler import PipelineCallbackHandler
from agents.input_feeder import InputFeederAgent
from agents.idea_factory import IdeaFactoryAgent
from agents.mvp_runner import MVPRunnerAgent
from state.state_machine import PipelineStateMachine
from state.obsidian_store import obsidian_store
from scheduler.daily_scheduler import DailyScheduler
from data_sources.newsnow_adapter import fetch_all_sources

# 初始化
state_machine = PipelineStateMachine()
agents = {
    "input_feeder": InputFeederAgent(),
    "idea_factory": IdeaFactoryAgent(),
    "mvp_runner": MVPRunnerAgent(),
}

# 3次触达处理器
async def morning_push():
    """09:00 早间推送"""
    # 1. 抓取新闻
    raw_news = await fetch_all_sources()

    # 2. 生成卡片
    await agents["input_feeder"].generate_daily_cards(raw_news)

    # 3. 生成创意（基于昨日选择）
    await agents["idea_factory"].generate_ideas()

    # 4. 发送钉钉消息
    cards = obsidian_store.read_cards(status="pending")
    ideas = obsidian_store.get_today_ideas(status="top3")
    await dingtalk_service.send_morning_push(cards, ideas)

async def afternoon_push():
    """14:00 下午推送"""
    confirmed_idea = state_machine.get_confirmed_idea()

    if confirmed_idea:
        tasks = await agents["mvp_runner"].generate_tasks(confirmed_idea)
        experiment = state_machine.create_experiment(confirmed_idea, tasks)
        await dingtalk_service.send_afternoon_push(experiment)
    else:
        await dingtalk_service.send_message("请先在早间消息中选择一个创意")

async def evening_push():
    """21:30 晚间推送"""
    experiment = state_machine.get_active_experiment()

    if experiment:
        state_machine.set_awaiting_evidence(experiment["id"])
        await dingtalk_service.send_evening_push(experiment)

# 启动
async def main():
    # 初始化钉钉
    handler = PipelineCallbackHandler(state_machine, agents)
    stream_manager = DingTalkStreamManager(handler)
    stream_manager.start_async()

    # 初始化调度器
    scheduler = DailyScheduler(
        morning_handler=morning_push,
        afternoon_handler=afternoon_push,
        evening_handler=evening_push,
    )

    # 启动调度
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 14. 里程碑与时间线

| 里程碑 | 交付内容 | 负责人 |
|--------|----------|--------|
| M1 | 项目结构 + 基础框架 | All |
| M2 | ObsidianStore + Schema | C |
| M3 | StateMachine + Scheduler | C |
| M4 | BaseAgent + MCP Tools | B |
| M5 | 3 Agents 完成 | B |
| M6 | 钉钉模块复制适配 | A |
| M7 | PipelineHandler | A |
| M8 | 联调 + Docker | All |
| M9 | 部署 + 测试 | All |

---

## 15. 开发环境准备

### 所有开发者

```bash
# 克隆项目
git clone <repo>
cd creativity-pipeline

# 安装依赖
pip install -r requirements.txt
pip install claude-agent-sdk

# 安装 Claude Code CLI
npm install -g @anthropic-ai/claude-code

# 环境变量
cp .env.example .env
# 编辑 .env 填入 API keys
```

### 开发者A

```bash
# 复制钉钉模块
cp -r /path/to/lippi-code-agent/src/dingtalk ./src/

# 测试钉钉连接
python -m src.dingtalk.test_connection
```

### 开发者B

```bash
# 测试 Claude SDK
python -c "from claude_agent_sdk import query; print('SDK OK')"

# 运行 Agent 测试
python -m pytest tests/agents/
```

### 开发者C

```bash
# 创建 vault 目录
mkdir -p vault/{cards,ideas,experiments,archive}

# 测试 Obsidian 读写
python -m src.state.test_obsidian
```
