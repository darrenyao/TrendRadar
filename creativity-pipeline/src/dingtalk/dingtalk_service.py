"""
钉钉服务 - 三次推送接口

支持两种模式:
- 单聊模式: 使用 DINGTALK_USER_ID (工号)，通过 prepare_card + finish_card 流程
- 群聊模式: 使用 DINGTALK_CONVERSATION_ID，通过 prepare_card + finish_card 流程
"""
import logging
import os
from typing import List, Dict, Optional

from .reply_service import CardData

logger = logging.getLogger(__name__)

# 默认卡片模板 ID (AI Card 推送模板)
DEFAULT_CARD_TEMPLATE_ID = "227f187c-d4bb-4926-b028-9d2f1c2ab6be.schema"


class DingTalkService:
    def __init__(self, reply_service, target: str, is_single_chat: bool = None):
        """
        初始化钉钉服务

        Args:
            reply_service: DingTalkReplyService 实例
            target: 目标标识符（union_id 或 conversation_id）
            is_single_chat: 是否单聊模式，None 时自动检测（群聊ID以cid开头）
        """
        self.reply = reply_service
        self.target = target

        # 检测模式：群聊 conversation_id 通常以 "cid" 开头
        if is_single_chat is not None:
            self.is_single_chat = is_single_chat
        else:
            self.is_single_chat = not target.startswith("cid")

        # 获取卡片模板 ID
        self.card_template_id = os.environ.get(
            "DINGTALK_CARD_TEMPLATE_ID",
            DEFAULT_CARD_TEMPLATE_ID
        )

        mode = "单聊" if self.is_single_chat else "群聊"
        logger.info(f"DingTalkService 初始化: {mode} -> {target[:20]}...")

    async def _send_card(self, content: str) -> bool:
        """
        发送卡片消息（核心方法）

        使用 prepare_card + update_card + finish_card 流程
        """
        # 1. 初始卡片数据（loading 状态）
        init_card_data = {
            "result": "",
            "lastMessage": "正在加载...",
            "config": {"autoLayout": True},
        }
        init_card = CardData(
            card_data=init_card_data,
            template_id=self.card_template_id,
        )

        if self.is_single_chat:
            conversation_token = await self.reply.prepare_card(
                card_data=init_card,
                union_id=self.target,
            )
        else:
            conversation_token = await self.reply.prepare_card(
                card_data=init_card,
                open_conversation_id=self.target,
            )

        if not conversation_token:
            logger.error("prepare_card 失败，无法获取 conversation_token")
            return False

        # 2. 更新卡片内容（使用 streamingComponent 格式）
        final_card = CardData(
            card_data={
                "key": "result",
                "value": content,
                "isFinalize": True,
            },
            template_id=self.card_template_id,
            options={
                "componentTag": "streamingComponent"
            },
        )
        update_success = await self.reply.update_card(
            conversation_token=conversation_token,
            card_data=final_card,
        )

        if not update_success:
            logger.error("update_card 失败")

        # 3. 完结卡片
        return await self.reply.finish_card(conversation_token)

    async def send_morning_push(self, cards: List[Dict], ideas: List[Dict]) -> bool:
        """发送早间推送（09:00）"""
        content = self._format_morning_message(cards, ideas)
        return await self._send_card(content)

    async def send_afternoon_push(self, experiment: Dict) -> bool:
        """发送下午推送（14:00）"""
        content = self._format_afternoon_message(experiment)
        return await self._send_card(content)

    async def send_evening_push(self, experiment: Dict) -> bool:
        """发送晚间推送（21:30）"""
        content = self._format_evening_message(experiment)
        return await self._send_card(content)

    async def send_message(self, content: str) -> bool:
        """发送普通文本消息"""
        return await self._send_card(content)

    async def send_confirmation(self, action: str, detail: str = "") -> bool:
        """发送确认消息（主动推送，创建新卡片）"""
        content = f"✅ {action}"
        if detail:
            content += f"\n{detail}"
        return await self.send_message(content)

    # ========== 被动回复方法（回复用户消息，使用现有会话） ==========

    async def reply_to_message(
        self,
        conversation_token: str,
        content: str,
    ) -> bool:
        """
        被动回复：在现有会话中回复用户消息

        Args:
            conversation_token: 用户消息中的 conversation_token
            content: 回复内容（Markdown 格式）

        Returns:
            是否发送成功
        """
        card_data = CardData(
            card_data={
                "key": "result",
                "value": content,
                "isFinalize": True,
            },
            template_id=self.card_template_id,
            options={"componentTag": "streamingComponent"},
        )
        return await self.reply.reply_card(conversation_token, card_data)

    async def reply_confirmation(
        self,
        conversation_token: str,
        action: str,
        detail: str = "",
    ) -> bool:
        """
        被动回复：发送确认消息

        Args:
            conversation_token: 用户消息中的 conversation_token
            action: 确认动作描述
            detail: 详细信息（可选）
        """
        content = f"✅ {action}"
        if detail:
            content += f"\n{detail}"
        return await self.reply_to_message(conversation_token, content)

    async def reply_error(
        self,
        conversation_token: str,
        message: str,
    ) -> bool:
        """
        被动回复：发送错误消息

        Args:
            conversation_token: 用户消息中的 conversation_token
            message: 错误信息
        """
        return await self.reply_to_message(conversation_token, f"❌ {message}")

    def _format_morning_message(self, cards: List[Dict], ideas: List[Dict]) -> str:
        """格式化早间消息

        核心设计：
        - 有创意时：展示 Top 3 创意供选择（回复 1/2/3）
        - 无创意时：展示素材卡片供选择（回复 1/2/3 选择感兴趣的素材）
        """
        sections = []

        if ideas:
            # ===== 有创意：展示 Top 3 创意供选择 =====
            sections.append("# 📊 今日创意候选")

            # 显示 Top 3 创意（带编号，用于选择）
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

            # 素材来源（简略展示）
            if cards:
                source_count = len(cards)
                cross_platform = sum(1 for c in cards if c.get("is_cross_platform"))
                sections.append(f"---\n📰 基于 {source_count} 条热点素材生成（{cross_platform} 条跨平台）")

            # 操作提示
            sections.append("---")
            sections.append("💡 **回复 1/2/3 选择要验证的创意** | 回复「刷新」重新生成")

        else:
            # ===== 无创意：展示素材卡片供选择 =====
            sections.append("# 📰 今日热点素材")

            if cards:
                sections.append(f"已收集 **{len(cards)}** 条热点，请选择感兴趣的方向：")

                # 显示带编号的素材卡片（最多5条）
                for i, card in enumerate(cards[:5], 1):
                    title = card.get("title", "未命名")
                    # 提取来源信息 - 优先用 related_sources，fallback 到 source/source_platform
                    sources = card.get("related_sources", [])
                    if sources:
                        source_str = "/".join(sources[:2])
                        platform_count = len(sources)
                    else:
                        source_str = card.get("source") or card.get("source_platform", "")
                        # 简化来源显示（截断过长内容）
                        if len(source_str) > 20:
                            source_str = source_str[:20] + "..."
                        platform_count = 1

                    # 热度和跨平台标识
                    heat = card.get("aggregated_heat") or card.get("heat_score") or card.get("heat", 0)
                    is_cross = card.get("is_cross_platform", False) or platform_count > 1

                    # 构建卡片行
                    card_line = f"**{i}.** {title}"
                    if source_str:
                        card_line += f" `{source_str}`"
                    if is_cross:
                        card_line += f" 🔥{platform_count}平台" if platform_count > 1 else " 🔥"

                    sections.append(card_line)

                if len(cards) > 5:
                    sections.append(f"*...还有 {len(cards) - 5} 条*")

                # 操作提示
                sections.append("---")
                sections.append("💡 **回复数字选择素材** (如 `1` 或 `1,2,3`)")
                sections.append("📋 回复「更多」查看完整列表")
                sections.append("选择后系统将基于素材生成创意方案")
            else:
                sections.append("*暂无热点素材，请稍后再试*")
                sections.append("---")
                sections.append("💡 回复「刷新」重新获取")

        return "\n\n".join(sections)

    def _format_afternoon_message(self, experiment: Dict) -> str:
        """格式化下午消息"""
        sections = []

        # 标题
        sections.append("# 🔧 今日实验任务包")

        # 选中创意
        idea_title = experiment.get("idea_title", "未命名创意")
        sections.append(f"**选中创意：** {idea_title}")

        # 任务清单
        tasks = experiment.get("tasks", [])
        if tasks:
            task_lines = ["## 任务清单"]
            for task in tasks:
                time_est = task.get("time_estimate", 10)
                desc = task.get("description", "")
                task_lines.append(f"- [ ] `{time_est}分钟` {desc}")
            sections.append("\n".join(task_lines))

        # 三人法则
        three_person = experiment.get("three_person_rule", {})
        profiles = three_person.get("target_profiles", [])
        if profiles:
            profile_lines = ["## 三人法则候选"]
            for i, profile in enumerate(profiles[:3], 1):
                ptype = profile.get("type", "")
                where = profile.get("where_to_find", "")
                profile_lines.append(f"{i}. **{ptype}** - {where}")
            sections.append("\n".join(profile_lines))

        # 操作提示
        sections.append("---")
        sections.append("💡 回复「开始」启动 | 回复「降级」切换5分钟任务")

        return "\n\n".join(sections)

    def _format_evening_message(self, experiment: Dict) -> str:
        """格式化晚间消息"""
        sections = []

        # 标题
        sections.append("# 🌙 证据收集时间")

        # 实验信息
        idea_title = experiment.get("idea_title", "未命名创意")
        status = experiment.get("status", "进行中")
        sections.append(f"**今日实验：** {idea_title}\n**状态：** {status}")

        # 提交要求
        submit_lines = [
            "## 请提交",
            "1. 截图/链接（发送图片或URL）",
            "2. 用户反馈（至少1条原话）",
            "3. 一句话复盘"
        ]
        sections.append("\n".join(submit_lines))

        # 操作提示
        sections.append("---")
        sections.append("💡 直接回复内容即可 | 回复「跳过」标记未完成")

        return "\n\n".join(sections)
