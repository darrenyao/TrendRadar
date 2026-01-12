"""
钉钉服务 - 三次推送接口
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class DingTalkService:
    def __init__(self, reply_service, target_conversation_id: str):
        self.reply = reply_service
        self.conversation_id = target_conversation_id

    async def send_morning_push(self, cards: List[Dict], ideas: List[Dict]) -> bool:
        content = self._format_morning_message(cards, ideas)
        return await self.reply.reply_markdown(self.conversation_id, content)

    async def send_afternoon_push(self, experiment: Dict) -> bool:
        content = self._format_afternoon_message(experiment)
        return await self.reply.reply_markdown(self.conversation_id, content)

    async def send_evening_push(self, experiment: Dict) -> bool:
        content = self._format_evening_message(experiment)
        return await self.reply.reply_markdown(self.conversation_id, content)

    async def send_message(self, content: str) -> bool:
        return await self.reply.reply_text(self.conversation_id, content)

    async def send_confirmation(self, action: str, detail: str = "") -> bool:
        content = f"✅ {action}"
        if detail:
            content += f"\n{detail}"
        return await self.reply.reply_text(self.conversation_id, content)

    def _format_morning_message(self, cards: List[Dict], ideas: List[Dict]) -> str:
        lines = ["📊 **今日创意候选**", ""]

        # 显示今日输入卡片摘要
        if cards:
            lines.append(f"**今日素材：** 已收集 {len(cards)} 张输入卡片")
            # 显示前3张卡片的标题
            for card in cards[:3]:
                title = card.get("title", "未命名")
                industry = card.get("industry", "")
                lines.append(f"  • {title} [{industry}]")
            if len(cards) > 3:
                lines.append(f"  • ...还有 {len(cards) - 3} 张")
            lines.append("")

        # 显示 Top 3 创意
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
