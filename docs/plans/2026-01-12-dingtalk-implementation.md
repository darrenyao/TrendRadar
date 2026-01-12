# 钉钉集成层实现计划（开发者A）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现创意流水线的钉钉集成层，支持消息收发和三次定时推送

**Architecture:** 精简复制 lippi-code-agent 钉钉模块核心文件，移除特定依赖改用标准库，新增 PipelineHandler 和 DingTalkService 处理创意流水线专用逻辑

**Tech Stack:** Python 3.10+, dingtalk_stream, alibabacloud_dingtalk SDK, pytest

---

## Task 1: 创建项目基础结构

**Files:**
- Create: `creativity-pipeline/src/__init__.py`
- Create: `creativity-pipeline/src/dingtalk/__init__.py`
- Create: `creativity-pipeline/tests/__init__.py`
- Create: `creativity-pipeline/tests/dingtalk/__init__.py`
- Create: `creativity-pipeline/requirements.txt`

**Step 1: 创建 __init__.py 文件**

```bash
touch creativity-pipeline/src/__init__.py
touch creativity-pipeline/src/dingtalk/__init__.py
touch creativity-pipeline/tests/__init__.py
touch creativity-pipeline/tests/dingtalk/__init__.py
```

**Step 2: 创建 requirements.txt**

```
dingtalk-stream>=1.0.0
alibabacloud-dingtalk>=2.0.0
alibabacloud-tea-openapi>=0.3.0
alibabacloud-tea-util>=0.3.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

**Step 3: Commit**

```bash
git add creativity-pipeline/
git commit -m "chore: 创建 creativity-pipeline 项目基础结构"
```

---

## Task 2: 实现 dingtalk_auth.py（精简版）

**Files:**
- Create: `creativity-pipeline/src/dingtalk/dingtalk_auth.py`
- Create: `creativity-pipeline/tests/dingtalk/test_dingtalk_auth.py`

**Step 1: 写测试文件**

```python
# creativity-pipeline/tests/dingtalk/test_dingtalk_auth.py
import pytest
from unittest.mock import Mock, patch
import os

# 设置测试环境变量
os.environ.setdefault("DINGTALK_CLIENT_ID", "test_client_id")
os.environ.setdefault("DINGTALK_CLIENT_SECRET", "test_client_secret")


class TestDingtalkAuth:
    """测试钉钉认证模块"""

    def test_get_auth_returns_singleton(self):
        """测试 get_auth 返回单例"""
        from src.dingtalk.dingtalk_auth import get_auth, _reset_auth
        _reset_auth()

        auth1 = get_auth()
        auth2 = get_auth()

        assert auth1 is auth2

    def test_auth_uses_env_variables(self):
        """测试认证使用环境变量"""
        from src.dingtalk.dingtalk_auth import DingtalkAuth, _reset_auth
        _reset_auth()

        auth = DingtalkAuth()

        assert auth._client_id == "test_client_id"
        assert auth._client_secret == "test_client_secret"

    def test_is_app_token_valid_returns_false_when_no_token(self):
        """测试无 token 时返回 False"""
        from src.dingtalk.dingtalk_auth import DingtalkAuth, _reset_auth
        _reset_auth()

        auth = DingtalkAuth()

        assert auth._is_app_token_valid() is False
```

**Step 2: 运行测试验证失败**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_dingtalk_auth.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: 实现 dingtalk_auth.py**

```python
# creativity-pipeline/src/dingtalk/dingtalk_auth.py
"""
钉钉认证模块（精简版）
"""
import os
import time
import logging
from typing import Optional

from alibabacloud_dingtalk.oauth2_1_0.client import Client as DingTalkOAuth2Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalk_oauth_models

logger = logging.getLogger(__name__)


class DingtalkAuth:
    """钉钉认证类"""

    def __init__(self):
        """初始化认证对象，从环境变量读取配置"""
        self._client_id = os.environ.get("DINGTALK_CLIENT_ID", "")
        self._client_secret = os.environ.get("DINGTALK_CLIENT_SECRET", "")

        # 应用级 token
        self.app_access_token: Optional[str] = None
        self.app_expires_in: int = 0
        self.app_last_refresh_time: float = 0

        self.client = self._create_client()

        logger.info(f"DingtalkAuth 初始化完成, client_id 前缀: {self._client_id[:4] if self._client_id else 'None'}")

    def _create_client(self) -> DingTalkOAuth2Client:
        """创建钉钉 OAuth2 客户端"""
        config = open_api_models.Config()
        config.protocol = 'https'
        config.region_id = 'central'
        return DingTalkOAuth2Client(config)

    def get_app_access_token(self) -> str:
        """获取企业应用访问令牌"""
        if self.app_access_token and self._is_app_token_valid():
            return self.app_access_token
        return self._refresh_app_token()

    def _is_app_token_valid(self) -> bool:
        """检查应用令牌是否有效"""
        if not self.app_access_token or not self.app_expires_in or not self.app_last_refresh_time:
            return False
        # 提前 5 分钟刷新
        current_time = time.time()
        return current_time < (self.app_last_refresh_time + self.app_expires_in - 300)

    def _refresh_app_token(self) -> str:
        """刷新应用访问令牌"""
        try:
            request = dingtalk_oauth_models.GetAccessTokenRequest(
                app_key=self._client_id,
                app_secret=self._client_secret
            )
            response = self.client.get_access_token(request)
            if response.body:
                self.app_access_token = response.body.access_token
                self.app_expires_in = response.body.expire_in
                self.app_last_refresh_time = time.time()
                logger.debug("刷新应用访问令牌成功")
                return self.app_access_token
        except Exception as e:
            logger.error(f"获取应用访问令牌失败: {e}")
        return ""


# 全局单例
_auth_instance: Optional[DingtalkAuth] = None


def get_auth() -> DingtalkAuth:
    """获取认证对象单例"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = DingtalkAuth()
    return _auth_instance


def _reset_auth() -> None:
    """重置认证对象（仅用于测试）"""
    global _auth_instance
    _auth_instance = None
```

**Step 4: 运行测试验证通过**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_dingtalk_auth.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add creativity-pipeline/src/dingtalk/dingtalk_auth.py creativity-pipeline/tests/dingtalk/test_dingtalk_auth.py
git commit -m "feat: 实现钉钉认证模块（精简版）"
```

---

## Task 3: 实现 message_context.py（精简版）

**Files:**
- Create: `creativity-pipeline/src/dingtalk/message_context.py`
- Create: `creativity-pipeline/tests/dingtalk/test_message_context.py`

**Step 1: 写测试文件**

```python
# creativity-pipeline/tests/dingtalk/test_message_context.py
import pytest
from src.dingtalk.message_context import MessageContext


class TestMessageContext:
    """测试消息上下文"""

    def test_create_from_dict(self):
        """测试从字典创建上下文"""
        data = {
            "senderId": "user123",
            "uid": 12345,
            "orgId": 67890,
            "text": {"content": "hello"},
            "senderNick": "张三",
            "conversationType": "2",
            "conversationId": "conv123",
            "conversationToken": "token123",
        }

        context = MessageContext.from_dingtalk_message(data)

        assert context.user_id == "user123"
        assert context.uid == 12345
        assert context.content == "hello"
        assert context.user_name == "张三"
        assert context.is_group_chat is True

    def test_create_with_minimal_data(self):
        """测试使用最小数据创建"""
        data = {}

        context = MessageContext.from_dingtalk_message(data)

        assert context.user_id == ""
        assert context.uid == 0
        assert context.content == ""

    def test_to_dict(self):
        """测试转换为字典"""
        context = MessageContext(
            user_id="user123",
            uid=12345,
            org_id=67890,
            content="hello"
        )

        result = context.to_dict()

        assert result["user_id"] == "user123"
        assert result["content"] == "hello"
```

**Step 2: 运行测试验证失败**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_message_context.py -v
```

Expected: FAIL

**Step 3: 实现 message_context.py**

```python
# creativity-pipeline/src/dingtalk/message_context.py
"""
消息上下文模块（精简版）
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MessageContext:
    """消息上下文数据类"""

    # 必填字段
    user_id: str
    uid: int
    org_id: int
    content: str

    # 可选字段
    user_name: Optional[str] = None
    sender_union_id: Optional[str] = None
    is_group_chat: bool = False
    group_name: Optional[str] = None
    conversation_id: Optional[str] = None
    conversation_token: Optional[str] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_dingtalk_message(cls, message: Dict[str, Any]) -> 'MessageContext':
        """从钉钉消息字典创建上下文"""
        user_id = message.get("senderId", "")
        uid = int(message.get("uid", 0))
        org_id = int(message.get("orgId", 0))

        # 提取文本内容
        text_obj = message.get("text", {})
        content = text_obj.get("content", "") if isinstance(text_obj, dict) else ""

        return cls(
            user_id=user_id,
            uid=uid,
            org_id=org_id,
            content=content,
            user_name=message.get("senderNick", "Unknown"),
            sender_union_id=message.get("senderUnionId"),
            is_group_chat=message.get("conversationType") == "2",
            group_name=message.get("conversationTitle"),
            conversation_id=message.get("conversationId"),
            conversation_token=message.get("conversationToken"),
            timestamp=message.get("createAt"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "user_id": self.user_id,
            "uid": self.uid,
            "org_id": self.org_id,
            "content": self.content,
            "user_name": self.user_name,
            "is_group_chat": self.is_group_chat,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
        }
        if self.is_group_chat and self.group_name:
            data["group_name"] = self.group_name
        if self.conversation_token:
            data["conversation_token"] = self.conversation_token
        return data
```

**Step 4: 运行测试验证通过**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_message_context.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add creativity-pipeline/src/dingtalk/message_context.py creativity-pipeline/tests/dingtalk/test_message_context.py
git commit -m "feat: 实现消息上下文模块（精简版）"
```

---

## Task 4: 实现 reply_service.py（精简版）

**Files:**
- Create: `creativity-pipeline/src/dingtalk/reply_service.py`
- Create: `creativity-pipeline/tests/dingtalk/test_reply_service.py`

**Step 1: 写测试文件**

```python
# creativity-pipeline/tests/dingtalk/test_reply_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.dingtalk.reply_service import DingTalkReplyService, ContentType


class TestContentType:
    """测试内容类型枚举"""

    def test_content_type_values(self):
        assert ContentType.TEXT.value == "text"
        assert ContentType.MARKDOWN.value == "markdown"


class TestDingTalkReplyService:
    """测试回复服务"""

    @pytest.mark.asyncio
    async def test_reply_text_calls_reply_with_text_type(self):
        """测试 reply_text 使用 TEXT 类型"""
        service = DingTalkReplyService()
        service.reply = AsyncMock(return_value=True)

        result = await service.reply_text("token123", "hello")

        service.reply.assert_called_once_with("token123", "hello", ContentType.TEXT)
        assert result is True

    @pytest.mark.asyncio
    async def test_reply_markdown_calls_reply_with_markdown_type(self):
        """测试 reply_markdown 使用 MARKDOWN 类型"""
        service = DingTalkReplyService()
        service.reply = AsyncMock(return_value=True)

        result = await service.reply_markdown("token123", "**bold**")

        service.reply.assert_called_once_with("token123", "**bold**", ContentType.MARKDOWN)
        assert result is True
```

**Step 2: 运行测试验证失败**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_reply_service.py -v
```

Expected: FAIL

**Step 3: 实现 reply_service.py**

```python
# creativity-pipeline/src/dingtalk/reply_service.py
"""
钉钉消息回复服务（精简版）
"""
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from alibabacloud_dingtalk.ai_interaction_1_0.client import Client as DingTalkAIClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.ai_interaction_1_0 import models as dingtalk_models
from alibabacloud_tea_util import models as util_models

from .dingtalk_auth import get_auth

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """消息内容类型"""
    TEXT = "text"
    MARKDOWN = "markdown"


class DingTalkReplyService:
    """钉钉消息回复服务"""

    def __init__(self):
        self.client = self._create_client()
        self.auth = get_auth()

    def _create_client(self) -> DingTalkAIClient:
        """创建钉钉 AI 客户端"""
        config = open_api_models.Config(
            protocol='https',
            region_id='central'
        )
        return DingTalkAIClient(config)

    async def reply(
        self,
        conversation_token: str,
        content: str,
        content_type: ContentType = ContentType.TEXT,
    ) -> bool:
        """
        发送回复消息

        Args:
            conversation_token: 会话 token
            content: 消息内容
            content_type: 内容类型

        Returns:
            是否发送成功
        """
        try:
            access_token = self.auth.get_app_access_token()
            if not access_token:
                logger.error("获取 access_token 失败")
                return False

            headers = dingtalk_models.ReplyHeaders()
            headers.x_acs_dingtalk_access_token = access_token

            request = dingtalk_models.ReplyRequest(
                conversation_token=conversation_token,
                content_type=content_type.value,
                content=content
            )

            await self.client.reply_with_options_async(
                request,
                headers,
                util_models.RuntimeOptions()
            )

            logger.info(f"发送 {content_type.value} 消息成功")
            return True

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    async def reply_text(self, conversation_token: str, text: str) -> bool:
        """发送文本消息"""
        return await self.reply(conversation_token, text, ContentType.TEXT)

    async def reply_markdown(self, conversation_token: str, markdown: str) -> bool:
        """发送 Markdown 消息"""
        return await self.reply(conversation_token, markdown, ContentType.MARKDOWN)


# 全局单例
reply_service = DingTalkReplyService()
```

**Step 4: 运行测试验证通过**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_reply_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add creativity-pipeline/src/dingtalk/reply_service.py creativity-pipeline/tests/dingtalk/test_reply_service.py
git commit -m "feat: 实现消息回复服务（精简版）"
```

---

## Task 5: 实现 pipeline_handler.py（核心）

**Files:**
- Create: `creativity-pipeline/src/dingtalk/pipeline_handler.py`
- Create: `creativity-pipeline/tests/dingtalk/test_pipeline_handler.py`

**Step 1: 写测试文件**

```python
# creativity-pipeline/tests/dingtalk/test_pipeline_handler.py
import pytest
from src.dingtalk.pipeline_handler import PipelineCallbackHandler


class TestParseSelection:
    """测试输入解析"""

    def setup_method(self):
        self.handler = PipelineCallbackHandler(
            state_machine=None,
            agents=None
        )

    def test_parse_single_digit(self):
        """测试单个数字选择"""
        result = self.handler.parse_selection("1")
        assert result == {"type": "select", "value": 1}

        result = self.handler.parse_selection("3")
        assert result == {"type": "select", "value": 3}

    def test_parse_multiple_digits(self):
        """测试多选"""
        result = self.handler.parse_selection("1,2")
        assert result == {"type": "select", "value": [1, 2]}

        result = self.handler.parse_selection("1,2,3")
        assert result == {"type": "select", "value": [1, 2, 3]}

    def test_parse_confirm_keywords(self):
        """测试确认关键词"""
        for kw in ["确认", "ok", "好", "OK"]:
            result = self.handler.parse_selection(kw)
            assert result == {"type": "confirm", "value": None}

    def test_parse_start_keywords(self):
        """测试开始关键词"""
        for kw in ["开始", "start", "START"]:
            result = self.handler.parse_selection(kw)
            assert result == {"type": "start", "value": None}

    def test_parse_downgrade_keywords(self):
        """测试降级关键词"""
        for kw in ["降级", "lite", "简单模式"]:
            result = self.handler.parse_selection(kw)
            assert result == {"type": "downgrade", "value": None}

    def test_parse_skip_keywords(self):
        """测试跳过关键词"""
        for kw in ["跳过", "skip"]:
            result = self.handler.parse_selection(kw)
            assert result == {"type": "skip", "value": None}

    def test_parse_evidence_default(self):
        """测试默认识别为证据"""
        result = self.handler.parse_selection("这是我的反馈")
        assert result == {"type": "evidence", "value": "这是我的反馈"}

        result = self.handler.parse_selection("http://example.com")
        assert result == {"type": "evidence", "value": "http://example.com"}

    def test_parse_strips_whitespace(self):
        """测试去除空白"""
        result = self.handler.parse_selection("  1  ")
        assert result == {"type": "select", "value": 1}

        result = self.handler.parse_selection("  确认  ")
        assert result == {"type": "confirm", "value": None}
```

**Step 2: 运行测试验证失败**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_pipeline_handler.py -v
```

Expected: FAIL

**Step 3: 实现 pipeline_handler.py**

```python
# creativity-pipeline/src/dingtalk/pipeline_handler.py
"""
创意流水线消息处理器
"""
import logging
from typing import Dict, Any, Optional, Tuple

from dingtalk_stream import CallbackMessage, AckMessage
from dingtalk_stream.graph import GraphHandler, GraphResponse
from dingtalk_stream.frames import Headers

from .message_context import MessageContext

logger = logging.getLogger(__name__)


class PipelineCallbackHandler(GraphHandler):
    """创意流水线专用消息处理器"""

    def __init__(self, state_machine, agents):
        """
        初始化处理器

        Args:
            state_machine: 状态机实例（由开发者C提供）
            agents: Agent 字典（由开发者B提供）
        """
        super().__init__()
        self.state_machine = state_machine
        self.agents = agents
        self.dingtalk_service = None  # 运行时注入

    def set_dingtalk_service(self, service):
        """注入钉钉服务"""
        self.dingtalk_service = service

    async def process(self, callback: CallbackMessage) -> Tuple[int, Dict]:
        """处理钉钉消息回调"""
        try:
            context = self._parse_context(callback)

            if not context.content:
                logger.info("收到空消息，跳过处理")
                return AckMessage.STATUS_OK, {"status": "empty_message"}

            selection = self.parse_selection(context.content.strip())
            logger.info(f"解析用户输入: {selection}")

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

            return AckMessage.STATUS_OK, {"status": "processed"}

        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            return AckMessage.STATUS_SYSTEM_EXCEPTION, {"error": str(e)}

    def parse_selection(self, content: str) -> Dict[str, Any]:
        """
        解析用户输入

        Args:
            content: 用户输入内容

        Returns:
            解析结果 {"type": str, "value": Any}
        """
        content = content.strip().lower()

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
            "确认": "confirm",
            "ok": "confirm",
            "好": "confirm",
            "开始": "start",
            "start": "start",
            "降级": "downgrade",
            "lite": "downgrade",
            "简单模式": "downgrade",
            "跳过": "skip",
            "skip": "skip",
        }

        for kw, action in keywords.items():
            if kw in content:
                return {"type": action, "value": None}

        # 默认视为证据提交
        return {"type": "evidence", "value": content}

    def _parse_context(self, callback: CallbackMessage) -> MessageContext:
        """从回调消息解析上下文"""
        data = callback.data
        if isinstance(data, str):
            import json
            data = json.loads(data)

        # 提取 body 中的内容
        body = data.get("body", {})
        if isinstance(body, str):
            import json
            body = json.loads(body)

        return MessageContext(
            user_id=body.get("sender_id", ""),
            uid=int(body.get("uid", 0)),
            org_id=int(body.get("org_id", 0)),
            content=body.get("input", ""),
            user_name=body.get("sender_nick", "Unknown"),
            conversation_id=body.get("conversation_id"),
            conversation_token=body.get("conversationToken"),
            is_group_chat=body.get("conversation_type") != "1",
        )

    # === 处理器方法 ===

    async def _handle_selection(self, context: MessageContext, value):
        """处理选择操作"""
        logger.info(f"用户 {context.user_name} 选择了: {value}")
        if self.state_machine:
            indices = value if isinstance(value, list) else [value]
            self.state_machine.record_selection(indices)
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation(f"已选择: {value}")

    async def _handle_confirm(self, context: MessageContext, value):
        """处理确认操作"""
        logger.info(f"用户 {context.user_name} 确认了选择")
        if self.state_machine:
            idea = self.state_machine.confirm_top1()
            if idea and self.agents and "mvp_runner" in self.agents:
                tasks = await self.agents["mvp_runner"].generate_tasks(idea)
                self.state_machine.create_experiment(idea, tasks)
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("已确认，任务包已生成")

    async def _handle_start(self, context: MessageContext, value):
        """处理开始操作"""
        logger.info(f"用户 {context.user_name} 开始实验")
        if self.state_machine:
            exp = self.state_machine.get_active_experiment()
            if exp:
                self.state_machine.update_status(exp["id"], "in_progress")
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("实验已开始，加油！")

    async def _handle_downgrade(self, context: MessageContext, value):
        """处理降级操作"""
        logger.info(f"用户 {context.user_name} 请求降级")
        if self.state_machine:
            self.state_machine.trigger_downgrade()
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("已切换到简单模式")

    async def _handle_skip(self, context: MessageContext, value):
        """处理跳过操作"""
        logger.info(f"用户 {context.user_name} 跳过当前任务")
        if self.state_machine:
            exp = self.state_machine.get_active_experiment()
            if exp:
                self.state_machine.update_status(exp["id"], "skipped")
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("已跳过，明天继续")

    async def _handle_evidence(self, context: MessageContext, value):
        """处理证据提交"""
        logger.info(f"用户 {context.user_name} 提交证据: {value[:50]}...")
        if self.state_machine:
            self.state_machine.record_evidence(value)
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("证据已记录")

    async def _handle_unknown(self, context: MessageContext, value):
        """处理未知输入"""
        logger.warning(f"未知输入: {value}")
        if self.dingtalk_service:
            await self.dingtalk_service.send_message(
                "抱歉，我没有理解您的意思。请回复数字选择，或使用关键词（确认/降级/跳过）"
            )

    async def raw_process(self, callback: CallbackMessage) -> AckMessage:
        """处理消息并返回 AckMessage"""
        code, response_dict = await self.process(callback)
        ack_message = AckMessage()
        ack_message.code = code
        ack_message.headers.message_id = callback.headers.message_id
        ack_message.headers.content_type = Headers.CONTENT_TYPE_APPLICATION_JSON
        ack_message.data = response_dict
        return ack_message
```

**Step 4: 运行测试验证通过**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_pipeline_handler.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add creativity-pipeline/src/dingtalk/pipeline_handler.py creativity-pipeline/tests/dingtalk/test_pipeline_handler.py
git commit -m "feat: 实现创意流水线消息处理器"
```

---

## Task 6: 实现 dingtalk_service.py（三次推送）

**Files:**
- Create: `creativity-pipeline/src/dingtalk/dingtalk_service.py`
- Create: `creativity-pipeline/tests/dingtalk/test_dingtalk_service.py`

**Step 1: 写测试文件**

```python
# creativity-pipeline/tests/dingtalk/test_dingtalk_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.dingtalk.dingtalk_service import DingTalkService


class TestMessageFormatting:
    """测试消息格式化"""

    def setup_method(self):
        mock_reply = Mock()
        mock_reply.reply_markdown = AsyncMock(return_value=True)
        mock_reply.reply_text = AsyncMock(return_value=True)
        self.service = DingTalkService(mock_reply, "test_conv_id")

    def test_format_morning_message_with_ideas(self):
        """测试早间消息格式化"""
        ideas = [
            {"title": "创意1", "one_liner": "描述1", "mvp_time": 30},
            {"title": "创意2", "one_liner": "描述2", "mvp_time": 45},
            {"title": "创意3", "one_liner": "描述3", "mvp_time": 60},
        ]

        result = self.service._format_morning_message([], ideas)

        assert "创意1" in result
        assert "创意2" in result
        assert "创意3" in result
        assert "1/2/3" in result

    def test_format_afternoon_message_with_experiment(self):
        """测试下午消息格式化"""
        experiment = {
            "idea_title": "测试创意",
            "tasks": [
                {"time_estimate": 10, "description": "任务1"},
                {"time_estimate": 20, "description": "任务2"},
            ]
        }

        result = self.service._format_afternoon_message(experiment)

        assert "测试创意" in result
        assert "任务1" in result
        assert "任务2" in result

    def test_format_evening_message(self):
        """测试晚间消息格式化"""
        experiment = {
            "idea_title": "测试创意",
            "status": "in_progress",
        }

        result = self.service._format_evening_message(experiment)

        assert "测试创意" in result
        assert "证据" in result


class TestSendMethods:
    """测试发送方法"""

    def setup_method(self):
        self.mock_reply = Mock()
        self.mock_reply.reply_markdown = AsyncMock(return_value=True)
        self.mock_reply.reply_text = AsyncMock(return_value=True)
        self.service = DingTalkService(self.mock_reply, "test_conv_id")

    @pytest.mark.asyncio
    async def test_send_morning_push(self):
        """测试早间推送"""
        result = await self.service.send_morning_push([], [])

        assert result is True
        self.mock_reply.reply_markdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_confirmation(self):
        """测试发送确认消息"""
        result = await self.service.send_confirmation("操作成功", "详情信息")

        assert result is True
        call_args = self.mock_reply.reply_text.call_args
        assert "操作成功" in call_args[0][1]
```

**Step 2: 运行测试验证失败**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_dingtalk_service.py -v
```

Expected: FAIL

**Step 3: 实现 dingtalk_service.py**

```python
# creativity-pipeline/src/dingtalk/dingtalk_service.py
"""
钉钉服务 - 三次推送接口
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class DingTalkService:
    """钉钉服务 - 供调度器和其他模块调用"""

    def __init__(self, reply_service, target_conversation_id: str):
        """
        初始化服务

        Args:
            reply_service: 回复服务实例
            target_conversation_id: 目标会话 ID
        """
        self.reply = reply_service
        self.conversation_id = target_conversation_id

    # === 三次推送接口 ===

    async def send_morning_push(self, cards: List[Dict], ideas: List[Dict]) -> bool:
        """
        09:00 早间推送 - 展示输入卡片 + Top3创意

        Args:
            cards: 输入卡片列表
            ideas: Top3 创意列表
        """
        content = self._format_morning_message(cards, ideas)
        return await self.reply.reply_markdown(self.conversation_id, content)

    async def send_afternoon_push(self, experiment: Dict) -> bool:
        """
        14:00 下午推送 - 展示任务包

        Args:
            experiment: 实验任务包
        """
        content = self._format_afternoon_message(experiment)
        return await self.reply.reply_markdown(self.conversation_id, content)

    async def send_evening_push(self, experiment: Dict) -> bool:
        """
        21:30 晚间推送 - 收集证据

        Args:
            experiment: 当前实验
        """
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

    # === 消息格式化 ===

    def _format_morning_message(self, cards: List[Dict], ideas: List[Dict]) -> str:
        """格式化早间消息"""
        lines = ["📊 **今日创意候选**", ""]

        if ideas:
            lines.append("**Top 3 创意：**")
            lines.append("")

            emojis = ["1️⃣", "2️⃣", "3️⃣"]
            for i, idea in enumerate(ideas[:3]):
                emoji = emojis[i] if i < len(emojis) else f"{i+1}."
                title = idea.get("title", "未命名")
                one_liner = idea.get("one_liner", "")
                mvp_time = idea.get("mvp_time", 30)

                lines.append(f"{emoji} **{title}**")
                lines.append(f"   {one_liner}")
                lines.append(f"   验证：{mvp_time}分钟")
                lines.append("")
        else:
            lines.append("暂无创意候选，请稍后再来")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("回复 **1/2/3** 选择 | 回复「降级」进入简单模式")

        return "\n".join(lines)

    def _format_afternoon_message(self, experiment: Dict) -> str:
        """格式化下午消息"""
        lines = ["🔧 **今日实验任务包**", ""]

        idea_title = experiment.get("idea_title", "未命名创意")
        lines.append(f"**选中创意：** {idea_title}")
        lines.append("")

        tasks = experiment.get("tasks", [])
        if tasks:
            lines.append("**任务清单：**")
            for task in tasks:
                time_est = task.get("time_estimate", 10)
                desc = task.get("description", "")
                lines.append(f"☐ [{time_est}分钟] {desc}")
            lines.append("")

        # 三人法则
        three_person = experiment.get("three_person_rule", {})
        profiles = three_person.get("target_profiles", [])
        if profiles:
            lines.append("**三人法则候选：**")
            for i, profile in enumerate(profiles[:3], 1):
                ptype = profile.get("type", "")
                where = profile.get("where_to_find", "")
                lines.append(f"{i}. {ptype} ({where})")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("回复「开始」启动 | 回复「降级」切换5分钟任务")

        return "\n".join(lines)

    def _format_evening_message(self, experiment: Dict) -> str:
        """格式化晚间消息"""
        lines = ["🌙 **证据收集时间**", ""]

        idea_title = experiment.get("idea_title", "未命名创意")
        status = experiment.get("status", "进行中")

        lines.append(f"**今日实验：** {idea_title}")
        lines.append(f"**状态：** {status}")
        lines.append("")

        lines.append("**请提交：**")
        lines.append("1. 截图/链接（发送图片或URL）")
        lines.append("2. 用户反馈（至少1条原话）")
        lines.append("3. 一句话复盘")
        lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("直接回复内容即可 | 回复「跳过」标记未完成")

        return "\n".join(lines)
```

**Step 4: 运行测试验证通过**

```bash
cd creativity-pipeline && python -m pytest tests/dingtalk/test_dingtalk_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add creativity-pipeline/src/dingtalk/dingtalk_service.py creativity-pipeline/tests/dingtalk/test_dingtalk_service.py
git commit -m "feat: 实现钉钉三次推送服务"
```

---

## Task 7: 实现 stream_client.py（精简版）

**Files:**
- Create: `creativity-pipeline/src/dingtalk/stream_client.py`

**Step 1: 实现 stream_client.py**

```python
# creativity-pipeline/src/dingtalk/stream_client.py
"""
钉钉流式客户端管理器（精简版）
"""
import os
import threading
import time
import atexit
import logging
from typing import Optional
from dataclasses import dataclass

from dingtalk_stream import DingTalkStreamClient, Credential

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """连接统计"""
    connection_attempts: int = 0
    successful_connections: int = 0
    last_connection_time: float = 0
    uptime: float = 0


class DingTalkStreamManager:
    """钉钉流式客户端管理器"""

    def __init__(self, handler):
        """
        初始化管理器

        Args:
            handler: 消息处理器（PipelineCallbackHandler）
        """
        self.handler = handler
        self.stream_client: Optional[DingTalkStreamClient] = None
        self.stop_event = threading.Event()
        self.stream_thread: Optional[threading.Thread] = None

        self.stats = ConnectionStats()

        # 从环境变量读取配置
        self.client_id = os.environ.get("DINGTALK_CLIENT_ID", "")
        self.client_secret = os.environ.get("DINGTALK_CLIENT_SECRET", "")
        self.stream_topic = os.environ.get("DINGTALK_STREAM_TOPIC", "/v1.0/graph/bot/message")

        atexit.register(self.stop)

    def start_async(self) -> None:
        """在后台线程中启动客户端（非阻塞）"""
        if self.stream_thread and self.stream_thread.is_alive():
            logger.warning("钉钉流客户端已经在运行中")
            return

        if not self.client_id or not self.client_secret:
            logger.error("缺少钉钉配置，请设置 DINGTALK_CLIENT_ID 和 DINGTALK_CLIENT_SECRET")
            return

        logger.info("正在后台启动钉钉流客户端...")

        self.stream_thread = threading.Thread(
            target=self._run_stream_client,
            name="DingTalkStreamThread",
            daemon=True
        )
        self.stream_thread.start()

        time.sleep(1)

        if self.stream_thread.is_alive():
            logger.info("✅ 钉钉流客户端已在后台启动")
        else:
            logger.error("❌ 钉钉流客户端启动失败")

    def _run_stream_client(self) -> None:
        """在线程中运行流客户端"""
        try:
            credential = Credential(self.client_id, self.client_secret)
            self.stream_client = DingTalkStreamClient(credential)
            self.stream_client.register_callback_handler(self.stream_topic, self.handler)

            self.stats.connection_attempts += 1
            self.stats.last_connection_time = time.time()

            logger.info("🔗 钉钉流客户端正在连接...")
            self.stream_client.start_forever()

        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭...")
        except Exception as e:
            logger.error(f"钉钉流客户端运行时出错: {e}", exc_info=True)
        finally:
            logger.info("钉钉流客户端已停止")

    def stop(self) -> None:
        """优雅关闭客户端"""
        if self.stop_event.is_set():
            return

        logger.info("正在关闭钉钉流客户端...")
        self.stop_event.set()

        if self.stream_client and hasattr(self.stream_client, 'close'):
            try:
                self.stream_client.close()
            except Exception as e:
                logger.warning(f"关闭流客户端时出错: {e}")

        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
            if self.stream_thread.is_alive():
                logger.warning("钉钉流客户端线程未能在5秒内结束")
            else:
                logger.info("✅ 钉钉流客户端已优雅关闭")

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return (
            self.stream_thread is not None
            and self.stream_thread.is_alive()
            and not self.stop_event.is_set()
        )

    def get_stats(self) -> ConnectionStats:
        """获取连接统计"""
        if self.is_running():
            self.stats.uptime = time.time() - self.stats.last_connection_time
        return self.stats
```

**Step 2: Commit**

```bash
git add creativity-pipeline/src/dingtalk/stream_client.py
git commit -m "feat: 实现钉钉流式客户端管理器（精简版）"
```

---

## Task 8: 更新 __init__.py 导出

**Files:**
- Modify: `creativity-pipeline/src/dingtalk/__init__.py`

**Step 1: 更新 __init__.py**

```python
# creativity-pipeline/src/dingtalk/__init__.py
"""
钉钉集成模块
"""
from .dingtalk_auth import DingtalkAuth, get_auth
from .message_context import MessageContext
from .reply_service import DingTalkReplyService, ContentType, reply_service
from .pipeline_handler import PipelineCallbackHandler
from .dingtalk_service import DingTalkService
from .stream_client import DingTalkStreamManager

__all__ = [
    "DingtalkAuth",
    "get_auth",
    "MessageContext",
    "DingTalkReplyService",
    "ContentType",
    "reply_service",
    "PipelineCallbackHandler",
    "DingTalkService",
    "DingTalkStreamManager",
]
```

**Step 2: Commit**

```bash
git add creativity-pipeline/src/dingtalk/__init__.py
git commit -m "chore: 更新 dingtalk 模块导出"
```

---

## Task 9: 运行所有测试验证

**Step 1: 运行所有测试**

```bash
cd creativity-pipeline && python -m pytest tests/ -v
```

Expected: All tests PASS

**Step 2: 最终提交**

```bash
git add -A creativity-pipeline/
git commit -m "feat: 完成钉钉集成层实现（开发者A）

- dingtalk_auth: 认证模块（精简版）
- message_context: 消息上下文
- reply_service: 消息回复服务
- pipeline_handler: 创意流水线消息处理器
- dingtalk_service: 三次推送服务
- stream_client: 流式客户端管理器

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## 交付检查清单

- [ ] Task 1: 项目基础结构
- [ ] Task 2: dingtalk_auth.py + 测试
- [ ] Task 3: message_context.py + 测试
- [ ] Task 4: reply_service.py + 测试
- [ ] Task 5: pipeline_handler.py + 测试（核心）
- [ ] Task 6: dingtalk_service.py + 测试
- [ ] Task 7: stream_client.py
- [ ] Task 8: __init__.py 导出
- [ ] Task 9: 全部测试通过
