"""InputFeeder agent for processing news into insight cards.

This agent leverages Claude Agent SDK's full capabilities to:
1. Read local news data with full context (summaries, cross-platform info)
2. Dynamically analyze patterns and trends
3. Fetch additional article content when needed
4. Generate structured cards with actionable analysis
"""
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class InputFeederAgent(BaseAgent):
    """Agent that transforms trending news into deep insight cards.

    Uses Agent-driven analysis approach:
    - read_raw_news: Read pre-fetched news data with full context
    - search_news: Search for specific topics
    - fetch_article_summary: Get full article content when needed
    - create_card: Create insight cards in Obsidian vault
    """

    def get_system_prompt(self) -> str:
        return """你是一个专业的趋势洞察分析师。你的任务是分析本地存储的热点新闻数据，并转化为深度洞察卡片。

## 可用工具

### 数据读取工具
- **read_raw_news**: 读取本地存储的新闻数据。返回完整的新闻列表，包含：
  - title: 标题
  - summary: 摘要（如有）
  - url: 原文链接
  - source_platform: 来源平台
  - industry: 行业分类
  - heat_score: 热度分数
  - cross_platform: 跨平台信息（是否多平台热门、出现在哪些平台）
  - **priority**: 优先级评分（系统自动计算）
    - total_score: 综合得分
    - priority_level: critical | high | medium | low
    - breakdown: 评分细节（heat, cross_platform, source_weight, recency）

- **search_news**: 按关键词搜索新闻
  - query: 搜索关键词
  - limit: 返回数量限制

- **get_news_item**: 获取单条新闻详情
  - item_id: 新闻ID

### 内容获取工具
- **fetch_article_summary**: 抓取文章原文摘要
  - url: 文章URL
  - item_id: 可选，更新对应新闻的摘要

### 卡片创建工具
- **create_card**: 创建洞察卡片
  - title, content, source, category, keywords, heat_score, analysis

## 优先级说明

每条新闻都有系统计算的优先级分数，帮助你识别最重要的内容：

| 优先级 | 分数 | 含义 | 处理建议 |
|--------|------|------|----------|
| **critical** | 90+ | 行业重大事件 | 必须分析，创建卡片 |
| **high** | 70-89 | 重要趋势 | 优先分析 |
| **medium** | 50-69 | 值得关注 | 选择性分析 |
| **low** | <50 | 一般信息 | 可跳过 |

统计信息中包含 `by_priority` 字段，显示各优先级的新闻数量分布。

## 分析流程

### 第一步：读取数据并了解优先级分布
1. 使用 read_raw_news 获取今日新闻数据
2. 查看 statistics.by_priority 了解优先级分布
3. 查看 statistics.priority_top_items 获取最高优先级条目
4. **优先处理 priority_level = "critical" 或 "high" 的条目**

### 第二步：深度分析（按优先级顺序）
对于 critical 和 high 优先级话题：
1. 如果 summary 为空或不够详细，使用 fetch_article_summary 获取更多内容
2. 分析跨平台出现的话题，不同平台的讨论角度
3. 识别趋势模式：行业变化、用户痛点、新兴机会

### 第三步：洞察提炼
对每个有商业价值的话题：
1. **变化分析**：具体发生了什么变化？有哪些数据支撑？
2. **影响群体**：谁受影响？程度如何？
3. **机会识别**：创造了什么产品/服务机会？
4. **可操作性**：独立开发者能做什么？

### 第四步：创建卡片
使用 create_card 工具创建卡片，每张卡片必须包含：

```
title: 简洁有力的洞察标题（体现核心变化，非新闻标题的复述）
content: 详细的洞察内容，包括：
  - 核心事实：具体的数据和变化
  - 影响分析：谁受影响、如何影响
  - 机会要点：潜在的产品/服务机会
source: 来源平台
industry: tech/ai | finance | social
category: change（变化）| pain_point（痛点）| opportunity（机会）
keywords: 3-5个精准关键词
heat_score: 热度分数 (0-100)，参考 priority.total_score
analysis: {
  change: "具体发生的变化",
  affected_groups: "受影响的群体",
  opportunity: "潜在机会描述",
  evidence: "支撑洞察的证据"
}
```

## 质量要求
1. **按优先级处理**：critical > high > medium，忽略 low
2. **跨平台验证**：cross_platform.is_trending = true 的条目更可靠
3. **避免标题复述**：卡片标题是你的洞察总结，不是原新闻标题
4. **提供证据**：每个洞察都要有数据/事实支撑
5. **可操作性**：机会点要具体到可以想象出产品形态
6. **差异化视角**：从创业者/产品经理角度思考，而非普通读者

## 输出要求
1. 为每个有价值的洞察创建一张卡片（通常5-10张）
2. 确保覆盖所有 critical 优先级的话题
3. 合并多条关于同一话题的新闻为一张更深度的卡片
4. 跳过纯娱乐/八卦/无商业价值的新闻
5. 最后汇总所有创建的卡片ID
"""

    async def analyze_news(self) -> List[str]:
        """Analyze news from local storage and create insight cards.

        This is the new Agent-driven approach where:
        1. Agent reads pre-fetched news from local JSON storage
        2. Agent dynamically analyzes with full context (summaries, cross-platform info)
        3. Agent fetches additional content as needed
        4. Agent creates insight cards based on analysis

        Returns:
            List of created card IDs.
        """
        logger.info("Starting Agent-driven news analysis...")
        prompt = """# 今日热点分析任务

## 第一步：读取数据
请使用 read_raw_news 工具读取今日的新闻数据。

## 第二步：分析数据
读取数据后，重点关注：
1. **统计概览**：总条数、各行业分布、跨平台热点数量
2. **跨平台热点**：关注 cross_platform.is_trending = true 的条目
3. **高热度新闻**：heat_score 较高的条目

## 第三步：深度分析
对于重要话题：
1. 如果 summary 为空，使用 fetch_article_summary 获取更多内容
2. 分析跨平台出现的话题，不同平台的讨论角度
3. 识别趋势模式：行业变化、用户痛点、新兴机会

分析维度：
- **科技/AI (tech/ai)**: 技术趋势、产品发布、行业动态
- **金融 (finance)**: 市场变化、投资热点、经济信号
- **社交 (social)**: 用户情绪、生活痛点、消费趋势

## 第四步：创建卡片
使用 create_card 工具为每个洞察创建卡片（通常5-10张）。

**重要提醒**：
- 卡片标题是你的洞察，不是新闻标题的复述
- 好的标题示例："外卖平台用户争夺战升级，配送时效成新战场"
- 差的标题示例："美团饿了么竞争加剧"

请开始分析。完成后，列出所有创建的卡片ID。
"""
        result = await self.run(prompt)
        return self._parse_card_ids(result)

    async def process_news(self, news_items: List[Dict[str, Any]]) -> List[str]:
        """Process news items into deep insight cards (legacy method).

        This method is kept for backwards compatibility.
        New code should use analyze_news() instead.

        Args:
            news_items: List of news items with title, url, source fields.

        Returns:
            List of created card IDs.
        """
        # Group by industry for better analysis
        grouped = self._group_by_industry(news_items)

        prompt = f"""# 今日热点分析任务

## 待分析数据
以下是从多个平台收集的 {len(news_items)} 条热点新闻：

{json.dumps(news_items, ensure_ascii=False, indent=2)}

## 分析任务

### 阶段1: 内容理解
1. 浏览所有新闻标题，快速识别主要话题
2. 对于重要/复杂的话题，使用 fetch_article_summary 获取原文深入理解
3. 记录关键事实和数据

### 阶段2: 跨平台分析
分析不同平台的热点：
- **科技/AI平台**: 技术趋势、产品发布、行业动态
- **金融平台**: 市场变化、投资热点、经济信号
- **社交平台**: 用户情绪、生活痛点、消费趋势

识别：
1. 哪些话题跨平台出现？（高关注度信号）
2. 各平台讨论角度有何不同？（机会点线索）
3. 哪些是突发热点，哪些是持续趋势？

### 阶段3: 洞察提炼
对每个有商业价值的话题，思考：
1. 这个变化背后的驱动力是什么？
2. 谁正在面临痛点？痛点有多强烈？
3. 现有解决方案的缺陷是什么？
4. 一个独立开发者能做什么来抓住这个机会？

### 阶段4: 创建卡片
使用 create_card 工具为每个洞察创建卡片。

**重要提醒**：
- 卡片标题是你的洞察，不是新闻标题的复述
- 好的标题示例："外卖平台用户争夺战升级，配送时效成新战场"
- 差的标题示例："美团饿了么竞争加剧"

请开始分析，完成后列出所有创建的卡片ID。
"""
        result = await self.run(prompt)
        return self._parse_card_ids(result)

    def _group_by_industry(self, news_items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group news items by industry for analysis."""
        grouped = {
            "tech_ai": [],
            "finance": [],
            "social": [],
            "other": []
        }

        tech_sources = {"zhihu", "v2ex", "36kr", "hackernews", "producthunt",
                       "github-trending-today", "sspai"}
        finance_sources = {"wallstreetcn-hot", "cls-hot", "eastmoney", "xueqiu"}
        social_sources = {"weibo", "douyin", "toutiao", "baidu", "bilibili-hot-search"}

        for item in news_items:
            source = item.get("source_platform", "").lower()
            if source in tech_sources:
                grouped["tech_ai"].append(item)
            elif source in finance_sources:
                grouped["finance"].append(item)
            elif source in social_sources:
                grouped["social"].append(item)
            else:
                grouped["other"].append(item)

        return grouped

    def _parse_card_ids(self, response: str) -> List[str]:
        """Extract card IDs from agent response.

        Args:
            response: Agent response text containing card IDs.

        Returns:
            List of card IDs found in the response.
        """
        # Match patterns like card-abc12345 or card-2026-01-12-001
        pattern = r'card-[a-f0-9]{8}|card-\d{4}-\d{2}-\d{2}-\d{3}'
        card_ids = re.findall(pattern, response)

        # Log parsing results for debugging
        logger.info(f"Parsing card IDs from response (length={len(response)})")
        if card_ids:
            logger.info(f"Found {len(card_ids)} card IDs: {card_ids}")
        else:
            logger.warning(f"No card IDs found in response. Response sample: {response[:300]}...")

        return card_ids
