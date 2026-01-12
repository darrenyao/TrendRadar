"""InputFeeder agent for processing news into cards.

Transforms TrendRadar trending news into structured input cards.
"""
import json
import re
from typing import List, Dict, Any

from .base_agent import BaseAgent


class InputFeederAgent(BaseAgent):
    """Agent that transforms trending news into structured input cards.

    This agent:
    1. Receives news items from TrendRadar
    2. Analyzes each item for changes/pain points/opportunities
    3. Creates structured cards in the Obsidian vault
    """

    def get_system_prompt(self) -> str:
        return """你是创意流水线的输入代理。你的任务是将热点新闻转化为结构化的"变化卡片"。

对于每条新闻，你需要：
1. 提取核心变化点
2. 分析受影响的人群
3. 识别潜在机会
4. 评估热度分数 (0-100)

使用 create_card 工具创建卡片，确保：
- title: 简洁的变化描述（20字以内）
- content: 详细的变化内容
- source: 新闻来源
- category: change（变化）/ pain_point（痛点）/ opportunity（机会）
- keywords: 相关关键词列表
- heat_score: 基于关注度的热度分数

热度评分标准：
- 90-100: 重大行业变革，影响广泛
- 70-89: 热门趋势，引发讨论
- 50-69: 值得关注的发展
- 30-49: 小范围影响
- 0-29: 信息量较小

处理完所有新闻后，列出创建的所有卡片ID。
"""

    async def process_news(self, news_items: List[Dict[str, Any]]) -> List[str]:
        """Process news items into cards.

        Args:
            news_items: List of news items with title, content, source fields.

        Returns:
            List of created card IDs.
        """
        prompt = f"""请处理以下热点新闻，为每条创建一张卡片：

{json.dumps(news_items, ensure_ascii=False, indent=2)}

请依次处理每条新闻：
1. 分析变化/痛点/机会
2. 使用 create_card 工具创建卡片
3. 最后列出所有创建的卡片ID
"""
        result = await self.run(prompt)
        return self._parse_card_ids(result)

    def _parse_card_ids(self, response: str) -> List[str]:
        """Extract card IDs from agent response.

        Args:
            response: Agent response text containing card IDs.

        Returns:
            List of card IDs found in the response.
        """
        # Match patterns like card-abc12345 or card-2026-01-12-001
        pattern = r'card-[a-f0-9]{8}|card-\d{4}-\d{2}-\d{2}-\d{3}'
        return re.findall(pattern, response)
