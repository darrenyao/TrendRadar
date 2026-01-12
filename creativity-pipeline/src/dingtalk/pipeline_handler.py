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
                "more": self._handle_more,
                "refresh": self._handle_refresh,
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
            "更多": "more", "全部": "more", "查看更多": "more",
            "刷新": "refresh",
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
        try:
            if self.state_machine:
                indices = value if isinstance(value, list) else [value]
                selected = self.state_machine.record_selection(indices)

                if not selected:
                    if self.dingtalk_service and context.conversation_token:
                        await self.dingtalk_service.reply_to_message(
                            context.conversation_token, "选择无效，请检查序号是否正确"
                        )
                    return

                # 构建选中素材的摘要
                selected_titles = [c.get("title", "未命名")[:20] for c in selected]
                titles_str = "、".join(selected_titles)

                # 发送确认消息
                if self.dingtalk_service and context.conversation_token:
                    await self.dingtalk_service.reply_to_message(
                        context.conversation_token,
                        f"✅ 已选择 {len(selected)} 条素材：{titles_str}\n\n⏳ 正在基于素材生成创意方案..."
                    )

                # 触发创意生成
                if self.agents and "idea_factory" in self.agents:
                    logger.info("触发 IdeaFactoryAgent 生成创意...")
                    try:
                        card_ids = [c.get("id") for c in selected if c.get("id")]
                        idea_ids = await self.agents["idea_factory"].generate_ideas(card_ids, count=3)
                        logger.info(f"生成了 {len(idea_ids)} 个创意: {idea_ids}")

                        # 标记为 top3
                        if idea_ids:
                            self.state_machine.set_top3(idea_ids)

                        # 获取并发送生成的创意
                        top3_ideas = self.state_machine.get_top3_ideas()
                        if top3_ideas and self.dingtalk_service:
                            await self._send_generated_ideas(context, top3_ideas)
                        elif self.dingtalk_service and context.conversation_token:
                            await self.dingtalk_service.reply_to_message(
                                context.conversation_token,
                                "创意生成完成，但没有找到合适的创意。请尝试选择其他素材。"
                            )
                    except Exception as e:
                        logger.error(f"创意生成失败: {e}", exc_info=True)
                        if self.dingtalk_service and context.conversation_token:
                            await self.dingtalk_service.reply_error(
                                context.conversation_token, f"创意生成失败: {e}"
                            )
                else:
                    # 没有 Agent 时，提示用户下一步
                    if self.dingtalk_service and context.conversation_token:
                        await self.dingtalk_service.reply_to_message(
                            context.conversation_token,
                            f"✅ 素材已选择\n\n下一步：等待明日早间推送，系统将基于所选素材生成创意方案。"
                        )

            elif self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_confirmation(
                    context.conversation_token, f"已选择: {value}"
                )
        except Exception as e:
            logger.error(f"处理选择时出错: {e}", exc_info=True)
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_error(
                    context.conversation_token, f"选择处理失败: {e}"
                )

    async def _send_generated_ideas(self, context: MessageContext, ideas: list):
        """发送生成的创意给用户"""
        if not self.dingtalk_service:
            return

        sections = ["# 🎯 为您生成了 Top 3 创意"]

        for i, idea in enumerate(ideas[:3], 1):
            title = idea.get("title", "未命名")
            one_liner = idea.get("one_liner", "")
            target_user = idea.get("target_user", "")
            mvp_time = idea.get("mvp_time", 30)

            idea_block = [
                f"## {i}️⃣ {title}",
                f"> {one_liner}" if one_liner else "",
                f"**目标用户**: {target_user}" if target_user else "",
                f"**验证时间**: {mvp_time}分钟",
            ]
            sections.append("\n".join(line for line in idea_block if line))

        sections.append("---")
        sections.append("💡 **回复 1/2/3 选择要验证的创意**")

        content = "\n\n".join(sections)
        await self.dingtalk_service.send_message(content)

    async def _handle_confirm(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 确认了选择")
        try:
            if self.state_machine:
                idea = self.state_machine.confirm_top1()
                if not idea:
                    if self.dingtalk_service and context.conversation_token:
                        await self.dingtalk_service.reply_to_message(
                            context.conversation_token,
                            "没有找到可确认的创意，请先选择一个创意"
                        )
                    return
                if self.agents and "mvp_runner" in self.agents:
                    tasks = await self.agents["mvp_runner"].generate_tasks(idea)
                    self.state_machine.create_experiment(idea, tasks)
                    if self.dingtalk_service and context.conversation_token:
                        await self.dingtalk_service.reply_confirmation(
                            context.conversation_token, "已确认，任务包已生成"
                        )
                else:
                    if self.dingtalk_service and context.conversation_token:
                        await self.dingtalk_service.reply_confirmation(
                            context.conversation_token,
                            f"已确认创意: {idea.get('title', '未命名')}"
                        )
            elif self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_confirmation(
                    context.conversation_token, "已确认"
                )
        except Exception as e:
            logger.error(f"确认操作失败: {e}", exc_info=True)
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_error(
                    context.conversation_token, f"确认操作失败: {e}"
                )

    async def _handle_start(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 开始实验")
        try:
            if self.state_machine:
                exp = self.state_machine.get_active_experiment()
                if exp:
                    self.state_machine.update_status(exp.get("id"), "in_progress")
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_confirmation(
                    context.conversation_token, "实验已开始，加油！"
                )
        except Exception as e:
            logger.error(f"开始实验失败: {e}", exc_info=True)
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_error(
                    context.conversation_token, f"开始实验失败: {e}"
                )

    async def _handle_downgrade(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 请求降级")
        try:
            if self.state_machine:
                result = self.state_machine.trigger_downgrade()
                if self.dingtalk_service and context.conversation_token:
                    if result:
                        await self.dingtalk_service.reply_confirmation(
                            context.conversation_token, "已切换到简单模式"
                        )
                    else:
                        await self.dingtalk_service.reply_to_message(
                            context.conversation_token, "当前没有可降级的实验"
                        )
            elif self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_confirmation(
                    context.conversation_token, "已切换到简单模式"
                )
        except Exception as e:
            logger.error(f"降级操作失败: {e}", exc_info=True)
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_error(
                    context.conversation_token, f"降级操作失败: {e}"
                )

    async def _handle_skip(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 跳过当前任务")
        try:
            if self.state_machine:
                exp = self.state_machine.get_active_experiment()
                if exp:
                    self.state_machine.update_status(exp.get("id"), "skipped")
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_confirmation(
                    context.conversation_token, "已跳过，明天继续"
                )
        except Exception as e:
            logger.error(f"跳过操作失败: {e}", exc_info=True)
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_error(
                    context.conversation_token, f"跳过操作失败: {e}"
                )

    async def _handle_evidence(self, context: MessageContext, value):
        logger.info(f"用户 {context.user_name} 提交证据: {value[:50]}...")
        try:
            if self.state_machine:
                result = self.state_machine.record_evidence(value)
                if self.dingtalk_service and context.conversation_token:
                    if result:
                        await self.dingtalk_service.reply_confirmation(
                            context.conversation_token, "证据已记录，感谢提交！"
                        )
                    else:
                        await self.dingtalk_service.reply_to_message(
                            context.conversation_token,
                            "当前没有进行中的实验，无法记录证据"
                        )
            elif self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_confirmation(
                    context.conversation_token, "证据已记录"
                )
        except Exception as e:
            logger.error(f"记录证据失败: {e}", exc_info=True)
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_error(
                    context.conversation_token, f"记录证据失败: {e}"
                )

    async def _handle_more(self, context: MessageContext, value):
        """显示所有素材卡片"""
        logger.info(f"用户 {context.user_name} 请求查看更多")
        try:
            if self.state_machine:
                cards = self.state_machine.get_pending_cards()

                if not cards:
                    if self.dingtalk_service and context.conversation_token:
                        await self.dingtalk_service.reply_to_message(
                            context.conversation_token, "当前没有可用的素材卡片"
                        )
                    return

                # 分批显示，每次最多10条
                sections = [f"# 📋 全部素材列表（共 {len(cards)} 条）"]

                for i, card in enumerate(cards, 1):
                    title = card.get("title", "未命名")
                    source = card.get("source") or card.get("source_platform", "")
                    if len(source) > 15:
                        source = source[:15] + "..."

                    card_line = f"**{i}.** {title}"
                    if source:
                        card_line += f" `{source}`"
                    sections.append(card_line)

                sections.append("---")
                sections.append("💡 回复数字选择（如 `1` 或 `1,2,3`）")

                content = "\n\n".join(sections)

                if self.dingtalk_service:
                    await self.dingtalk_service.send_message(content)

        except Exception as e:
            logger.error(f"查看更多失败: {e}", exc_info=True)
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_error(
                    context.conversation_token, f"查看更多失败: {e}"
                )

    async def _handle_refresh(self, context: MessageContext, value):
        """刷新数据"""
        logger.info(f"用户 {context.user_name} 请求刷新")
        try:
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_to_message(
                    context.conversation_token,
                    "⏳ 正在刷新数据...\n\n刷新功能需要一些时间，请稍后查看新的推送消息。"
                )
            # TODO: 触发重新抓取数据
            # 这里可以调用 morning_push 的部分逻辑
        except Exception as e:
            logger.error(f"刷新失败: {e}", exc_info=True)
            if self.dingtalk_service and context.conversation_token:
                await self.dingtalk_service.reply_error(
                    context.conversation_token, f"刷新失败: {e}"
                )

    async def _handle_unknown(self, context: MessageContext, value):
        logger.warning(f"未知输入: {value}")
        if self.dingtalk_service and context.conversation_token:
            await self.dingtalk_service.reply_to_message(
                context.conversation_token,
                "抱歉，我没有理解您的意思。\n\n可用命令：\n- 回复数字选择素材（如 `1` 或 `1,2,3`）\n- 回复「更多」查看全部列表\n- 回复「确认/降级/跳过」"
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
