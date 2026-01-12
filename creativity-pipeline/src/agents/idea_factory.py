"""IdeaFactory agent for generating ideas from cards.

Generates creative ideas from input cards with multi-dimensional scoring.
"""
import re
from typing import List

from .base_agent import BaseAgent


class IdeaFactoryAgent(BaseAgent):
    """Agent that generates creative ideas from input cards.

    This agent:
    1. Reads selected input cards
    2. Identifies opportunities and patterns
    3. Generates scored ideas for MVP validation
    """

    def get_system_prompt(self) -> str:
        return """你是创意流水线的创意工厂代理。你的任务是从输入卡片中发现创业/产品机会。

创意生成原则：
1. 针对具体的目标用户
2. 解决真实的痛点
3. 有独特的切入角度
4. MVP可在30分钟内完成

对每个创意进行四维评分 (0-25分)：
- feasibility: 技术可行性 - 用现有技术能否快速实现
- market: 市场潜力 - 目标用户群体大小和付费意愿
- personal_fit: 个人匹配度 - 是否符合创作者的技能和兴趣
- uniqueness: 独特性 - 相比现有方案的差异化程度

评分标准：
- 20-25: 优秀，显著优势
- 15-19: 良好，有明确优势
- 10-14: 一般，符合基本要求
- 5-9: 较弱，存在明显短板
- 0-4: 不足，难以满足要求

使用 create_idea 工具创建创意，确保：
- title: 创意名称
- one_liner: 一句话价值主张
- target_user: 具体的目标用户画像
- problem: 解决的核心问题
- unique_angle: 独特切入点
- mvp_time: MVP预计时间（分钟）
- source_cards: 源卡片ID列表
- scores: 四维评分（包含 total）

生成创意后，列出所有创建的创意ID。
"""

    async def generate_ideas(self, card_ids: List[str], count: int = 3) -> List[str]:
        """Generate ideas from selected cards.

        Args:
            card_ids: List of card IDs to generate ideas from.
            count: Number of ideas to generate (default 3).

        Returns:
            List of created idea IDs.
        """
        prompt = f"""基于以下卡片生成{count}个创意。

步骤：
1. 先使用 read_cards 读取所有卡片
2. 筛选出ID为 {card_ids} 的卡片
3. 分析这些卡片中的变化/痛点/机会
4. 为每个创意使用 create_idea 工具创建

请确保每个创意：
- 有具体的目标用户
- 解决明确的问题
- 有差异化的切入点
- MVP时间控制在30分钟内

请开始处理。
"""
        result = await self.run(prompt)
        return self._parse_idea_ids(result)

    def _parse_idea_ids(self, response: str) -> List[str]:
        """Extract idea IDs from agent response.

        Args:
            response: Agent response text containing idea IDs.

        Returns:
            List of idea IDs found in the response.
        """
        # Match patterns like idea-abc12345 or idea-2026-01-12-001
        pattern = r'idea-[a-f0-9]{8}|idea-\d{4}-\d{2}-\d{2}-\d{3}'
        return re.findall(pattern, response)
