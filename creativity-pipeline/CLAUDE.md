# CLAUDE.md

This file provides guidance to Claude Code when working with the creativity-pipeline project.

## Project Overview

Creativity Pipeline is an automated creative idea generation system that operates through three daily touchpoints (09:00, 14:00, 21:30). It fetches trending news, generates input cards, creates ideas via AI agents, and manages experiments with evidence collection.

**Core Principle**: "System pushes the person forward" - users only need to "click once / select one / reply once".

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Creativity Pipeline                       │
├─────────────────────────────────────────────────────────────┤
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
│  │           DingTalk Streaming Gateway                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
creativity-pipeline/
├── src/
│   ├── main.py                 # Entry point + scheduler integration
│   ├── agents/                 # 3 AI Agents (Claude Agent SDK)
│   │   ├── base_agent.py       # BaseAgent with MCP server
│   │   ├── input_feeder.py     # News → Cards
│   │   ├── idea_factory.py     # Cards → Ideas (Top 3)
│   │   ├── mvp_runner.py       # Idea → Experiment tasks
│   │   └── obsidian_tools.py   # MCP tools for Obsidian
│   ├── state/                  # State management
│   │   ├── state_machine.py    # Pipeline state transitions
│   │   ├── obsidian_store.py   # Markdown + YAML frontmatter
│   │   └── schemas.py          # Status enums
│   ├── dingtalk/               # DingTalk integration
│   │   ├── dingtalk_service.py # Message formatting & sending
│   │   ├── pipeline_handler.py # Message parsing (1/2/3, 确认, 降级)
│   │   └── reply_service.py    # Reply utilities
│   ├── scheduler/              # Daily scheduling
│   │   └── daily_scheduler.py  # 3 touchpoints + crontab
│   └── data_sources/           # News fetching
│       └── newsnow_adapter.py  # TrendRadar integration
├── vault/                      # Obsidian storage
│   ├── cards/                  # Input cards
│   ├── ideas/                  # Generated ideas
│   ├── experiments/            # Active experiments
│   └── archive/                # Completed items
├── tests/                      # 110 tests (all passing)
├── docker/                     # Docker deployment
└── requirements.txt
```

## Commands

### Run Pipeline
```bash
# Activate virtual environment
source .venv/bin/activate

# Check status
python -m src.main --status

# Run single touchpoint
python -m src.main --mode once --touch-point morning
python -m src.main --mode once --touch-point afternoon
python -m src.main --mode once --touch-point evening

# Run scheduler (continuous mode)
python -m src.main --mode scheduler

# Utility commands
python -m src.main --check-timeout   # Check experiment timeouts
python -m src.main --archive         # Archive completed items
```

### Testing
```bash
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific module tests
python -m pytest tests/state/ -v      # Obsidian/state tests
python -m pytest tests/agents/ -v     # Agent tests
python -m pytest tests/dingtalk/ -v   # DingTalk tests
python -m pytest tests/scheduler/ -v  # Scheduler tests

# Run integration tests
python -m pytest tests/test_integration.py -v
```

### Docker
```bash
cd docker
docker-compose up -d
```

## Environment Variables

### AI Agents (Claude Agent SDK)

**No API Key Required** - Claude Agent SDK uses Claude Code CLI with local authentication.

Prerequisites:
1. Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
2. Login via CLI: `claude login`
3. Install SDK: `pip install claude-agent-sdk`

### DingTalk Integration (Required for Notifications)

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `DINGTALK_CLIENT_ID` | DingTalk app client ID | DingTalk Developer Portal |
| `DINGTALK_CLIENT_SECRET` | DingTalk app secret | DingTalk Developer Portal |
| `DINGTALK_CONVERSATION_ID` | Target group conversation ID | DingTalk API |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | `./vault` | Obsidian vault location |
| `MORNING_PUSH_TIME` | `09:00` | Morning touchpoint time |
| `AFTERNOON_PUSH_TIME` | `14:00` | Afternoon touchpoint time |
| `EVENING_PUSH_TIME` | `21:30` | Evening touchpoint time |
| `TIKHUB_API_KEY` | (empty) | For Twitter/Reddit data |
| `TZ` | `Asia/Shanghai` | Timezone |

### Demo Mode

The pipeline runs in **demo mode** without DingTalk:

```bash
# No environment variables needed for testing
python -m src.main --status

# Output shows:
# Claude SDK:        Enabled (if claude-agent-sdk installed)
# DingTalk SDK:      Disabled
```

## Key Concepts

### State Machine Flow
```
Input → Cards Selected → Ideas Generated → Top1 Confirmed → Experiment → Evidence → Archive
```

### WIP=1 Rule
Only one active experiment at a time. New experiments cannot be created until current one completes.

### Three Daily Touchpoints

| Time | Action | User Interaction |
|------|--------|------------------|
| 09:00 | Morning push: cards + top 3 ideas | Reply `1/2/3` to select |
| 14:00 | Afternoon push: experiment tasks | Reply `开始` or `降级` |
| 21:30 | Evening push: evidence collection | Submit screenshots/feedback |

### Downgrade Mechanism
If user cannot complete normal tasks, reply `降级` to switch to 5-minute lite version.

## Design Document

Full design specification: `docs/creativity-pipeline-design.md`

Or view the plan file: `/Users/yixuan.yhl/.claude/plans/crystalline-jumping-hammock.md`

## Dependencies

- **Claude Agent SDK**: For AI agents (optional, graceful degradation)
- **DingTalk Stream SDK**: For notifications (optional, graceful degradation)
- **TrendRadar**: For news data sources (via newsnow_adapter)

## Testing Status

- **110 tests passing**
- All 5 integration checkpoints verified (CP1-CP5)
- Ready for Docker deployment (Phase 3)
