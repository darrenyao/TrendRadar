# 钉钉集成层设计方案（开发者A）

> **文档路径**: `docs/plans/2026-01-12-dingtalk-integration-design.md`
> **日期**: 2026-01-12
> **负责人**: 开发者A

---

## 1. 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 项目位置 | TrendRadar/creativity-pipeline/ | 复用数据抓取能力 |
| 复用方式 | 精简复制核心文件 | 移除特定依赖，保持独立 |
| 交互模式 | 纯文本回复 | 实现简单，与设计文档一致 |

---

## 2. 模块结构

```
creativity-pipeline/
└── src/
    └── dingtalk/
        ├── __init__.py
        ├── stream_client.py      # 流式连接管理（精简版）
        ├── message_context.py    # 消息上下文（精简版）
        ├── reply_service.py      # 消息发送服务（精简版）
        ├── dingtalk_auth.py      # 认证模块（精简版）
        ├── pipeline_handler.py   # 【新增】创意流水线消息处理器
        └── dingtalk_service.py   # 【新增】对外统一服务接口
```

### 文件来源

| 文件 | 来源 | 改动 |
|------|------|------|
| stream_client.py | lippi-code-agent | 移除 loguru，使用标准 logging |
| message_context.py | lippi-code-agent | 移除 Stopwatch 依赖 |
| reply_service.py | lippi-code-agent | 移除特定配置依赖 |
| dingtalk_auth.py | lippi-code-agent | 精简认证逻辑 |
| pipeline_handler.py | 新建 | 创意流水线专用处理器 |
| dingtalk_service.py | 新建 | 三次推送对外接口 |

---

## 3. 核心组件设计

### 3.1 PipelineCallbackHandler

创意流水线专用消息处理器，负责解析用户输入并路由到对应处理逻辑。

```python
class PipelineCallbackHandler(GraphHandler):
    """创意流水线消息处理器"""

    def __init__(self, state_machine, agents):
        super().__init__()
        self.state_machine = state_machine  # 由开发者C提供
        self.agents = agents                # 由开发者B提供
        self.dingtalk_service = None        # 初始化时注入

    async def process(self, callback: CallbackMessage):
        """处理钉钉消息回调"""
        context = self._parse_context(callback)
        selection = self.parse_selection(context.content.strip())

        handlers = {
            "select": self._handle_selection,
            "confirm": self._handle_confirm,
            "start": self._handle_start,
            "downgrade": self._handle_downgrade,
            "skip": self._handle_skip,
            "evidence": self._handle_evidence,
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
            if nums:
                return {"type": "select", "value": nums}

        # 关键词映射
        keywords = {
            "确认": "confirm", "ok": "confirm", "好": "confirm",
            "开始": "start", "start": "start",
            "降级": "downgrade", "lite": "downgrade", "简单模式": "downgrade",
            "跳过": "skip", "skip": "skip",
        }

        for kw, action in keywords.items():
            if kw in content:
                return {"type": action, "value": None}

        # 默认视为证据提交
        return {"type": "evidence", "value": content}
```

### 3.2 DingTalkService

对外统一服务接口，供调度器和其他模块调用。

```python
class DingTalkService:
    """钉钉服务 - 三次推送接口"""

    def __init__(self, reply_service, target_conversation_id: str):
        self.reply = reply_service
        self.conversation_id = target_conversation_id

    # === 三次推送接口 ===

    async def send_morning_push(self, cards: list, ideas: list) -> bool:
        """09:00 早间推送"""
        content = self._format_morning_message(cards, ideas)
        return await self.reply.reply_markdown(self.conversation_id, content)

    async def send_afternoon_push(self, experiment: dict) -> bool:
        """14:00 下午推送"""
        content = self._format_afternoon_message(experiment)
        return await self.reply.reply_markdown(self.conversation_id, content)

    async def send_evening_push(self, experiment: dict) -> bool:
        """21:30 晚间推送"""
        content = self._format_evening_message(experiment)
        return await self.reply.reply_markdown(self.conversation_id, content)

    # === 通用接口 ===

    async def send_message(self, content: str) -> bool:
        """发送普通消息"""
        return await self.reply.reply_text(self.conversation_id, content)

    async def send_confirmation(self, action: str, detail: str = "") -> bool:
        """发送确认消息"""
        content = f"✅ {action}"
        if detail:
            content += f"\n{detail}"
        return await self.reply.reply_text(self.conversation_id, content)
```

---

## 4. 消息卡片模板

### 4.1 早间推送 (09:00)

```markdown
📊 **今日创意候选**

**Top 3 创意：**

1️⃣ **{title_1}**
   {one_liner_1}
   验证：{mvp_time_1}分钟{mvp_desc_1}

2️⃣ **{title_2}**
   {one_liner_2}
   验证：{mvp_time_2}分钟{mvp_desc_2}

3️⃣ **{title_3}**
   {one_liner_3}
   验证：{mvp_time_3}分钟{mvp_desc_3}

━━━━━━━━━━━━━━━━━━━━
回复 **1/2/3** 选择 | 回复「降级」进入简单模式
```

### 4.2 下午推送 (14:00)

```markdown
🔧 **今日实验任务包**

**选中创意：** {idea_title}

**任务清单：**
☐ [{time_1}分钟] {task_1}
☐ [{time_2}分钟] {task_2}
☐ [{time_3}分钟] {task_3}

**三人法则候选：**
1. {profile_1} ({where_1})
2. {profile_2} ({where_2})
3. {profile_3} ({where_3})

━━━━━━━━━━━━━━━━━━━━
回复「开始」启动 | 回复「降级」切换5分钟任务
```

### 4.3 晚间推送 (21:30)

```markdown
🌙 **证据收集时间**

**今日实验：** {idea_title}
**状态：** {status}

**请提交：**
1. 截图/链接（发送图片或URL）
2. 用户反馈（至少1条原话）
3. 一句话复盘

━━━━━━━━━━━━━━━━━━━━
直接回复内容即可 | 回复「跳过」标记未完成
```

---

## 5. 依赖接口

### 5.1 需要开发者B提供

```python
# Agent 接口
class InputFeederAgent:
    async def generate_daily_cards(self, raw_news: list) -> list

class IdeaFactoryAgent:
    async def generate_ideas(self) -> list

class MVPRunnerAgent:
    async def generate_tasks(self, idea: dict) -> dict
```

### 5.2 需要开发者C提供

```python
# 状态机接口
class PipelineStateMachine:
    def record_selection(self, indices: list) -> list
    def confirm_top1(self, index: int) -> dict
    def create_experiment(self, idea: dict, tasks: dict) -> dict
    def record_evidence(self, evidence: str) -> bool
    def trigger_downgrade(self, exp_id: str) -> bool
    def has_active_experiment(self) -> bool
    def get_active_experiment(self) -> dict
```

---

## 6. 交付清单

- [ ] 复制并精简 stream_client.py
- [ ] 复制并精简 message_context.py
- [ ] 复制并精简 reply_service.py
- [ ] 复制并精简 dingtalk_auth.py
- [ ] 实现 pipeline_handler.py
- [ ] 实现 dingtalk_service.py
- [ ] 实现消息格式化模板
- [ ] 单元测试：parse_selection()
- [ ] 集成测试：钉钉消息收发

---

## 7. 环境变量

```bash
# 钉钉配置
DINGTALK_CLIENT_ID=xxx
DINGTALK_CLIENT_SECRET=xxx
DINGTALK_CORP_ID=xxx

# 可选
DINGTALK_TARGET_CONVERSATION_ID=xxx  # 目标群聊ID
```
