"""
创意流水线消息处理器
"""
import json
import logging
from typing import Dict, Any, Tuple, Optional

try:
    from dingtalk_stream import CallbackMessage, AckMessage
    from dingtalk_stream.graph import GraphHandler
    from dingtalk_stream.frames import Headers
    HAS_DINGTALK_STREAM = True
except ImportError:
    # For testing without dingtalk_stream installed
    CallbackMessage = Any
    AckMessage = None
    GraphHandler = object
    Headers = None
    HAS_DINGTALK_STREAM = False

from .message_context import MessageContext

logger = logging.getLogger(__name__)


class PipelineCallbackHandler(GraphHandler):
    """创意流水线专用消息处理器"""

    def __init__(self, state_machine, agents):
        if HAS_DINGTALK_STREAM:
            super().__init__()
        self.state_machine = state_machine
        self.agents = agents
        self.dingtalk_service = None

    def set_dingtalk_service(self, service):
        self.dingtalk_service = service

    async def process(self, callback: CallbackMessage) -> Tuple[int, Dict]:
        try:
            context = self._parse_context(callback)
            if not context.content:
                logger.info("收到空消息，跳过处理")
                status_ok = AckMessage.STATUS_OK if HAS_DINGTALK_STREAM else 200
                return status_ok, {"status": "empty_message"}

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
            status_ok = AckMessage.STATUS_OK if HAS_DINGTALK_STREAM else 200
            return status_ok, {"status": "processed"}

        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            status_err = AckMessage.STATUS_SYSTEM_EXCEPTION if HAS_DINGTALK_STREAM else 500
            return status_err, {"error": str(e)}

    def parse_selection(self, content: str) -> Dict[str, Any]:
        content = content.strip().lower()

        if content.isdigit():
            return {"type": "select", "value": int(content)}

        if "," in content:
            nums = [int(x) for x in content.split(",") if x.strip().isdigit()]
            if nums:
                return {"type": "select", "value": nums}

        keywords = {
            "确认": "confirm", "ok": "confirm", "好": "confirm",
            "开始": "start", "start": "start",
            "降级": "downgrade", "lite": "downgrade", "简单模式": "downgrade",
            "跳过": "skip", "skip": "skip",
        }

        for kw, action in keywords.items():
            if kw in content:
                return {"type": action, "value": None}

        return {"type": "evidence", "value": content}

    def _parse_context(self, callback: CallbackMessage) -> MessageContext:
        data = callback.data
        if isinstance(data, str):
            data = json.loads(data)
        body = data.get("body", {})
        if isinstance(body, str):
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

    async def _handle_selection(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 选择了: {value}")
        if self.state_machine:
            indices = value if isinstance(value, list) else [value]
            self.state_machine.record_selection(indices)
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation(f"已选择: {value}")

    async def _handle_confirm(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 确认了选择")
        if self.state_machine:
            idea = self.state_machine.confirm_top1()
            if idea and self.agents and "mvp_runner" in self.agents:
                tasks = await self.agents["mvp_runner"].generate_tasks(idea)
                self.state_machine.create_experiment(idea, tasks)
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("已确认，任务包已生成")

    async def _handle_start(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 开始实验")
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("实验已开始，加油！")

    async def _handle_downgrade(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 请求降级")
        if self.state_machine:
            self.state_machine.trigger_downgrade()
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("已切换到简单模式")

    async def _handle_skip(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 跳过当前任务")
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("已跳过，明天继续")

    async def _handle_evidence(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 提交证据: {value[:50]}...")
        if self.state_machine:
            self.state_machine.record_evidence(value)
        if self.dingtalk_service:
            await self.dingtalk_service.send_confirmation("证据已记录")

    async def _handle_unknown(self, context: MessageContext, value):
        logger.warning(f"未知输入: {value}")
        if self.dingtalk_service:
            await self.dingtalk_service.send_message(
                "抱歉，我没有理解您的意思。请回复数字选择，或使用关键词（确认/降级/跳过）"
            )

    async def raw_process(self, callback: CallbackMessage):
        if not HAS_DINGTALK_STREAM:
            raise RuntimeError("dingtalk_stream not installed")
        code, response_dict = await self.process(callback)
        ack_message = AckMessage()
        ack_message.code = code
        ack_message.headers.message_id = callback.headers.message_id
        ack_message.headers.content_type = Headers.CONTENT_TYPE_APPLICATION_JSON
        ack_message.data = response_dict
        return ack_message
