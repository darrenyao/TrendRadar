# 创意流水线项目进展总结

> 更新日期: 2026-01-12
> 设计方案: `~/.claude/plans/crystalline-jumping-hammock.md`

---

## 项目背景

AI 已能完成大量编码、分析工作，执行不再是瓶颈。**想法和创意以及快速迭代**成为当下时代更重要的能力。

**目标**: 打造一套「不靠意志力」的系统，人只做"点一下/选一个/回一句"。

**核心原则**: "系统推着人走"

---

## 系统架构

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

---

## 实施阶段进展

### Phase 1: 基础搭建 ✅ 完成

| 任务 | 状态 | 说明 |
|------|------|------|
| 项目结构创建 | ✅ | `src/agents/`, `src/state/`, `src/dingtalk/`, `src/scheduler/` |
| 复制钉钉模块 | ✅ | 从 lippi-code-agent 复制并适配 |
| Obsidian 读写 | ✅ | `obsidian_store.py` 支持 cards/ideas/experiments 的 CRUD |
| Docker 配置 | ✅ | `docker/` 目录包含 Dockerfile 和 docker-compose.yml |

### Phase 2: Agent 实现 ✅ 完成

| 任务 | 状态 | 说明 |
|------|------|------|
| BaseAgent | ✅ | 使用 Claude Agent SDK，支持 MCP 工具 |
| InputFeederAgent | ✅ | 从新闻生成输入卡片 |
| IdeaFactoryAgent | ✅ | 从卡片生成创意，筛选 Top 3 |
| MVPRunnerAgent | ✅ | 将创意拆解为任务包 |
| Obsidian MCP Tools | ✅ | `obsidian_tools.py` 定义工具装饰器 |

### Phase 3: 流水线集成 🔄 进行中

| 任务 | 状态 | 说明 |
|------|------|------|
| 状态机实现 | ✅ | `PipelineStateMachine` 支持状态流转 |
| PipelineCallbackHandler | ✅ | 支持数字选择、确认、降级、刷新、更多 |
| DingTalkService | ✅ | 三次推送接口 + 被动回复 |
| 定时调度 | ✅ | `DailyScheduler` 09:00/14:00/21:30 |
| 早间推送流程 | ✅ | 推送卡片/创意，接收用户选择 |
| 选择后生成创意 | ✅ | 选择卡片后触发 IdeaFactoryAgent |
| 下午推送流程 | 🔄 | 框架存在，需验证完整链路 |
| 晚间推送流程 | 🔄 | 框架存在，需验证完整链路 |
| 降级机制 | 🔄 | Handler 存在，完整逻辑待实现 |

### Phase 4: 部署测试 📋 待开始

| 任务 | 状态 | 说明 |
|------|------|------|
| Docker 构建测试 | 📋 | 待执行 |
| 钉钉流式连接测试 | ✅ | WebSocket 连接正常 |
| Agent 输出质量测试 | 🔄 | 基本可用，需优化提示词 |
| 端到端流程验证 | 🔄 | 早间部分验证，完整周期待测 |
| VPS 部署 | 📋 | 待执行 |

---

## 测试覆盖

```
110 tests passing
├── tests/state/        # Obsidian/状态机测试
├── tests/agents/       # Agent 测试
├── tests/dingtalk/     # 钉钉消息格式测试
├── tests/scheduler/    # 调度器测试
└── tests/test_integration.py  # 集成测试 (CP1-CP5)
```

---

## 2026-01-12 修复记录

### 问题 1: 早间卡片显示不清晰
- **现象**: 推送的卡片没有编号，用户不知道"回复 1/2/3"是什么
- **修复**:
  - 添加编号 (1. 2. 3.)
  - 显示来源平台信息
  - 显示跨平台指标 (🔥N平台)

### 问题 2: 用户选择后无后续处理
- **现象**: 用户回复数字后，只打印日志没有后续
- **修复**:
  - 选择后触发 IdeaFactoryAgent 生成创意
  - 生成的创意发送回用户

### 问题 3: 进程推送后退出
- **现象**: `--mode once` 推送后进程退出，无法接收回复
- **修复**:
  - 推送后保持 Stream 运行
  - 添加 `--no-wait` 选项跳过等待

### 问题 4: 无法查看更多卡片
- **现象**: 只显示 5 条，无法查看其他 34 条
- **修复**:
  - 添加 `更多` / `全部` 命令
  - 添加 `刷新` 命令

### 问题 5: 创意排序报错
- **现象**: `'str' object has no attribute 'get'` 在排序时
- **修复**:
  - 添加 `_get_idea_score()` 方法安全提取分数

---

## 三次触达设计

| 时间 | 触达点 | 用户操作 | 系统响应 |
|------|--------|----------|----------|
| 09:00 | 早间推送 | 回复 `1/2/3` 选择卡片 | 生成 Top 3 创意 |
| 09:00+ | 确认创意 | 回复 `1/2/3` 选择创意 | 记录确认的 Top1 |
| 14:00 | 下午推送 | 回复 `开始` 或 `降级` | 生成任务包 / 5分钟任务 |
| 21:30 | 晚间推送 | 提交截图/反馈/复盘 | 记录证据，归档实验 |

---

## 接下来的 Action

### P0 高优先级

1. **完善下午推送流程**
   - 验证用户确认 Top1 后创建实验的流程
   - 测试 MVPRunnerAgent 生成任务包
   - 实现 `开始` / `降级` 命令处理

2. **完善晚间推送流程**
   - 验证证据收集流程
   - 实现证据记录到 Obsidian
   - 实现 `跳过` 命令处理

3. **完整端到端测试**
   - 跑完整个日周期
   - 验证状态机流转

### P1 中优先级

4. **Agent 输出质量优化**
   - 优化提示词
   - 添加更多数据源

5. **降级机制完善**
   - 5 分钟降级任务生成
   - 超时自动降级逻辑

### P2 低优先级

6. **Docker 部署**
7. **文档完善**

---

## 测试命令

```bash
# 激活虚拟环境
source .venv/bin/activate

# 检查状态
python -m src.main --status

# 早间推送（等待回复）
python -m src.main --mode once --touch-point morning

# 早间推送（不等待）
python -m src.main --mode once --touch-point morning --no-wait

# 下午推送
python -m src.main --mode once --touch-point afternoon

# 晚间推送
python -m src.main --mode once --touch-point evening

# 运行测试
python -m pytest tests/ -v
```

---

## 关键文件

| 文件 | 用途 |
|------|------|
| `src/main.py` | 入口 + 调度集成 |
| `src/dingtalk/dingtalk_service.py` | 消息格式化 + 发送 |
| `src/dingtalk/pipeline_handler.py` | 用户消息解析 + 处理 |
| `src/state/state_machine.py` | 状态流转 |
| `src/state/obsidian_store.py` | Markdown 读写 |
| `src/agents/input_feeder.py` | Agent 1: 新闻 → 卡片 |
| `src/agents/idea_factory.py` | Agent 2: 卡片 → 创意 |
| `src/agents/mvp_runner.py` | Agent 3: 创意 → 任务 |
