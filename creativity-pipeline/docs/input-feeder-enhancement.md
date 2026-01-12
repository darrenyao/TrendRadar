# InputFeederAgent 功能增强设计文档

## 1. 当前实现分析

### 1.1 现有功能

**文件位置**: `src/agents/input_feeder.py`

```python
class InputFeederAgent(BaseAgent):
    """当前实现的核心方法"""

    def get_system_prompt(self) -> str:
        # 定义分析框架和卡片创建规范

    async def process_news(self, news_items: List[Dict]) -> List[str]:
        # 处理新闻列表，返回创建的卡片ID

    def _group_by_industry(self, news_items: List[Dict]) -> Dict[str, List[Dict]]:
        # 按行业分组（tech_ai, finance, social, other）

    def _parse_card_ids(self, response: str) -> List[str]:
        # 从响应中提取卡片ID
```

### 1.2 当前调用流程

```
main.py:107-115
├── get_top_items(limit=50)        # 从 TrendRadar 获取50条新闻
├── top_items = raw_news[:10]      # 硬编码取前10条
└── InputFeederAgent.process_news(top_items)
    └── _parse_card_ids(response)  # 正则提取卡片ID
```

### 1.3 存在的问题

| 问题 | 影响 | 严重程度 |
|------|------|----------|
| 无新闻去重/聚类 | 同一话题多来源产生重复卡片 | 高 |
| 无智能筛选 | 固定取前10条，忽略热度权重 | 高 |
| 无用户偏好学习 | 每次推送内容与用户兴趣无关 | 中 |
| 无跨天主题追踪 | 持续热点无法累积分析 | 中 |
| 无质量评估反馈 | Agent 无法从用户选择中学习 | 低 |

---

## 2. 功能增强设计

### 2.1 新闻去重与聚类模块

#### 2.1.1 设计目标

- 识别相同/相似话题的新闻
- 合并同一话题的多源信息
- 保留最有价值的信息来源

#### 2.1.2 实现方案

```python
# 新增文件: src/agents/news_preprocessor.py

from dataclasses import dataclass
from typing import List, Dict, Set
import re
from collections import defaultdict

@dataclass
class NewsCluster:
    """新闻聚类结果"""
    cluster_id: str
    topic: str                    # 话题主题
    news_items: List[Dict]        # 聚类内的新闻
    sources: Set[str]             # 涉及的平台
    total_heat: int               # 累计热度
    cross_platform: bool          # 是否跨平台
    representative: Dict          # 代表性新闻

class NewsPreprocessor:
    """新闻预处理器：去重、聚类、排序"""

    def __init__(self):
        # 停用词列表
        self.stopwords = {"的", "是", "在", "了", "和", "与", "为", "被", "将"}
        # 相似度阈值
        self.similarity_threshold = 0.6

    def preprocess(self, news_items: List[Dict]) -> List[NewsCluster]:
        """预处理新闻列表

        流程:
        1. 提取关键词
        2. 计算相似度矩阵
        3. 聚类合并
        4. 排序输出
        """
        # Step 1: 关键词提取
        for item in news_items:
            item['keywords'] = self._extract_keywords(item.get('title', ''))

        # Step 2: 聚类
        clusters = self._cluster_by_similarity(news_items)

        # Step 3: 排序（跨平台优先 + 热度）
        clusters.sort(key=lambda c: (c.cross_platform, c.total_heat), reverse=True)

        return clusters

    def _extract_keywords(self, title: str) -> Set[str]:
        """从标题提取关键词"""
        # 移除标点和停用词
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', title)
        return {w for w in words if w not in self.stopwords and len(w) > 1}

    def _calculate_similarity(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """Jaccard 相似度"""
        if not keywords1 or not keywords2:
            return 0.0
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        return intersection / union if union > 0 else 0.0

    def _cluster_by_similarity(self, news_items: List[Dict]) -> List[NewsCluster]:
        """基于相似度聚类"""
        clusters = []
        used = set()

        for i, item in enumerate(news_items):
            if i in used:
                continue

            # 创建新聚类
            cluster_items = [item]
            sources = {item.get('source_platform', 'unknown')}

            # 查找相似新闻
            for j, other in enumerate(news_items[i+1:], start=i+1):
                if j in used:
                    continue
                similarity = self._calculate_similarity(
                    item.get('keywords', set()),
                    other.get('keywords', set())
                )
                if similarity >= self.similarity_threshold:
                    cluster_items.append(other)
                    sources.add(other.get('source_platform', 'unknown'))
                    used.add(j)

            used.add(i)

            # 计算聚类属性
            total_heat = sum(n.get('heat', 0) for n in cluster_items)
            cross_platform = len(sources) > 1

            # 选择代表性新闻（热度最高的）
            representative = max(cluster_items, key=lambda x: x.get('heat', 0))

            clusters.append(NewsCluster(
                cluster_id=f"cluster-{len(clusters)+1}",
                topic=representative.get('title', '')[:50],
                news_items=cluster_items,
                sources=sources,
                total_heat=total_heat,
                cross_platform=cross_platform,
                representative=representative
            ))

        return clusters

    def to_agent_input(self, clusters: List[NewsCluster], limit: int = 10) -> List[Dict]:
        """转换为 Agent 输入格式

        增强信息:
        - 标记跨平台话题
        - 附加来源平台列表
        - 包含聚合热度
        """
        result = []
        for cluster in clusters[:limit]:
            enriched = {
                **cluster.representative,
                'is_cross_platform': cluster.cross_platform,
                'related_sources': list(cluster.sources),
                'aggregated_heat': cluster.total_heat,
                'related_news_count': len(cluster.news_items),
                'related_titles': [n.get('title') for n in cluster.news_items[:3]]
            }
            result.append(enriched)
        return result
```

#### 2.1.3 集成到 InputFeederAgent

```python
# 修改 input_feeder.py

from .news_preprocessor import NewsPreprocessor

class InputFeederAgent(BaseAgent):
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        self.preprocessor = NewsPreprocessor()

    async def process_news(self, news_items: List[Dict]) -> List[str]:
        # 预处理：去重聚类
        clusters = self.preprocessor.preprocess(news_items)

        # 转换为增强输入
        enriched_items = self.preprocessor.to_agent_input(clusters, limit=10)

        # 构建 prompt（包含聚类信息）
        prompt = self._build_enhanced_prompt(enriched_items, clusters)

        result = await self.run(prompt)
        return self._parse_card_ids(result)
```

---

### 2.2 智能筛选与热度排序

#### 2.2.1 设计目标

- 基于多维度评分筛选新闻
- 支持自定义权重配置
- 提供筛选原因追溯

#### 2.2.2 评分维度

```python
@dataclass
class NewsScore:
    """新闻评分详情"""
    news_id: str
    heat_score: float        # 原始热度 (0-100)
    cross_platform_bonus: float  # 跨平台加成 (0-30)
    recency_score: float     # 时效性 (0-20)
    source_weight: float     # 来源权重 (0.5-1.5)
    preference_match: float  # 偏好匹配 (0-50)
    total_score: float       # 综合得分

class NewsRanker:
    """新闻智能排序器"""

    # 来源权重配置
    SOURCE_WEIGHTS = {
        # 科技/AI 高权重
        "36kr": 1.3,
        "hackernews": 1.4,
        "producthunt": 1.4,
        "github-trending-today": 1.2,
        "v2ex": 1.1,
        # 财经中等权重
        "wallstreetcn-hot": 1.2,
        "xueqiu": 1.1,
        # 社交平台基础权重
        "weibo": 1.0,
        "zhihu": 1.1,
        "douyin": 0.9,
        "bilibili-hot-search": 1.0,
    }

    def __init__(self, user_preferences: Dict = None):
        self.user_preferences = user_preferences or {}

    def rank(self, clusters: List[NewsCluster]) -> List[NewsScore]:
        """对聚类结果评分排序"""
        scores = []
        for cluster in clusters:
            score = self._calculate_score(cluster)
            scores.append(score)

        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores

    def _calculate_score(self, cluster: NewsCluster) -> NewsScore:
        """计算单个聚类的综合得分"""
        rep = cluster.representative

        # 1. 原始热度 (归一化到 0-100)
        heat = min(cluster.total_heat, 100)

        # 2. 跨平台加成
        cross_bonus = 30 if cluster.cross_platform else 0
        if len(cluster.sources) >= 3:
            cross_bonus = 50  # 三平台以上额外加成

        # 3. 时效性评分（假设有时间戳）
        recency = 20  # 默认值，可根据时间戳计算

        # 4. 来源权重
        source = rep.get('source_platform', 'unknown')
        source_weight = self.SOURCE_WEIGHTS.get(source, 1.0)

        # 5. 用户偏好匹配
        preference_match = self._match_preferences(cluster)

        # 综合得分
        total = (heat + cross_bonus + recency + preference_match) * source_weight

        return NewsScore(
            news_id=rep.get('id', ''),
            heat_score=heat,
            cross_platform_bonus=cross_bonus,
            recency_score=recency,
            source_weight=source_weight,
            preference_match=preference_match,
            total_score=total
        )

    def _match_preferences(self, cluster: NewsCluster) -> float:
        """计算与用户偏好的匹配度"""
        if not self.user_preferences:
            return 0

        score = 0
        keywords = set()
        for item in cluster.news_items:
            keywords.update(item.get('keywords', set()))

        # 匹配用户关注的关键词
        for kw, weight in self.user_preferences.get('keywords', {}).items():
            if kw in keywords:
                score += weight

        # 匹配用户偏好的行业
        industries = self.user_preferences.get('industries', [])
        for item in cluster.news_items:
            if item.get('source_platform') in industries:
                score += 10

        return min(score, 50)  # 上限 50
```

---

### 2.3 用户偏好学习模块

#### 2.3.1 设计目标

- 从用户选择行为中学习偏好
- 持久化存储偏好数据
- 动态调整推荐权重

#### 2.3.2 数据结构

```python
# 新增文件: src/state/user_preferences.py

from dataclasses import dataclass, field
from typing import Dict, List, Set
from datetime import datetime
import json
from pathlib import Path

@dataclass
class UserPreferences:
    """用户偏好数据"""

    # 关键词偏好 {keyword: weight}
    keyword_weights: Dict[str, float] = field(default_factory=dict)

    # 行业偏好 {industry: weight}
    industry_weights: Dict[str, float] = field(default_factory=dict)

    # 来源偏好 {source: weight}
    source_weights: Dict[str, float] = field(default_factory=dict)

    # 历史选择记录
    selection_history: List[Dict] = field(default_factory=list)

    # 最后更新时间
    last_updated: str = ""

class PreferenceLearner:
    """用户偏好学习器"""

    DECAY_FACTOR = 0.95  # 历史权重衰减因子
    LEARNING_RATE = 0.1  # 学习率

    def __init__(self, vault_path: str = "./vault"):
        self.vault_path = Path(vault_path)
        self.prefs_file = self.vault_path / "user_preferences.json"
        self.preferences = self._load_preferences()

    def _load_preferences(self) -> UserPreferences:
        """加载已有偏好数据"""
        if self.prefs_file.exists():
            with open(self.prefs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return UserPreferences(**data)
        return UserPreferences()

    def _save_preferences(self):
        """保存偏好数据"""
        self.preferences.last_updated = datetime.now().isoformat()
        with open(self.prefs_file, 'w', encoding='utf-8') as f:
            json.dump(self.preferences.__dict__, f, ensure_ascii=False, indent=2)

    def learn_from_selection(self, selected_cards: List[Dict], all_cards: List[Dict]):
        """从用户选择中学习

        Args:
            selected_cards: 用户选中的卡片
            all_cards: 所有候选卡片
        """
        # 衰减历史权重
        self._decay_weights()

        # 从选中卡片中学习正向偏好
        for card in selected_cards:
            self._learn_positive(card)

        # 从未选中卡片中学习负向偏好（可选）
        selected_ids = {c.get('id') for c in selected_cards}
        for card in all_cards:
            if card.get('id') not in selected_ids:
                self._learn_negative(card)

        # 记录选择历史
        self.preferences.selection_history.append({
            'timestamp': datetime.now().isoformat(),
            'selected_count': len(selected_cards),
            'total_count': len(all_cards),
            'selected_ids': list(selected_ids)
        })

        # 保持历史记录在合理范围
        if len(self.preferences.selection_history) > 100:
            self.preferences.selection_history = self.preferences.selection_history[-100:]

        self._save_preferences()

    def _decay_weights(self):
        """衰减历史权重，让近期选择更重要"""
        for kw in self.preferences.keyword_weights:
            self.preferences.keyword_weights[kw] *= self.DECAY_FACTOR
        for ind in self.preferences.industry_weights:
            self.preferences.industry_weights[ind] *= self.DECAY_FACTOR
        for src in self.preferences.source_weights:
            self.preferences.source_weights[src] *= self.DECAY_FACTOR

    def _learn_positive(self, card: Dict):
        """从正向选择中学习"""
        # 学习关键词偏好
        for kw in card.get('keywords', []):
            current = self.preferences.keyword_weights.get(kw, 0)
            self.preferences.keyword_weights[kw] = current + self.LEARNING_RATE * 10

        # 学习行业偏好
        industry = card.get('industry', 'other')
        current = self.preferences.industry_weights.get(industry, 0)
        self.preferences.industry_weights[industry] = current + self.LEARNING_RATE * 5

        # 学习来源偏好
        source = card.get('source', 'unknown')
        current = self.preferences.source_weights.get(source, 0)
        self.preferences.source_weights[source] = current + self.LEARNING_RATE * 3

    def _learn_negative(self, card: Dict):
        """从负向选择中学习（轻微降权）"""
        for kw in card.get('keywords', []):
            current = self.preferences.keyword_weights.get(kw, 0)
            self.preferences.keyword_weights[kw] = max(0, current - self.LEARNING_RATE * 2)

    def get_preference_dict(self) -> Dict:
        """获取偏好字典，用于 NewsRanker"""
        return {
            'keywords': self.preferences.keyword_weights,
            'industries': list(self.preferences.industry_weights.keys()),
            'sources': self.preferences.source_weights
        }

    def get_top_preferences(self, n: int = 10) -> Dict:
        """获取 Top N 偏好，用于日志/调试"""
        return {
            'top_keywords': sorted(
                self.preferences.keyword_weights.items(),
                key=lambda x: x[1], reverse=True
            )[:n],
            'top_industries': sorted(
                self.preferences.industry_weights.items(),
                key=lambda x: x[1], reverse=True
            )[:n],
            'top_sources': sorted(
                self.preferences.source_weights.items(),
                key=lambda x: x[1], reverse=True
            )[:n]
        }
```

---

### 2.4 增强的 System Prompt

#### 2.4.1 新增指令

```python
def get_enhanced_system_prompt(self, user_preferences: Dict = None) -> str:
    """生成增强版系统提示"""

    base_prompt = self.get_system_prompt()  # 原有 prompt

    # 添加用户偏好上下文
    preference_context = ""
    if user_preferences:
        top_keywords = user_preferences.get('top_keywords', [])
        if top_keywords:
            preference_context = f"""
## 用户偏好参考

根据历史选择记录，用户特别关注以下话题：
{', '.join([kw for kw, _ in top_keywords[:5]])}

请在分析时优先关注这些领域的新闻，并尝试发现相关的新机会。
但不要完全忽略其他领域的重要变化。
"""

    # 添加聚类处理指令
    cluster_instruction = """
## 聚类新闻处理

输入的新闻已经过预处理，包含以下增强信息：
- `is_cross_platform`: 是否跨平台热点（跨平台话题通常更重要）
- `related_sources`: 相关来源平台列表
- `aggregated_heat`: 聚合后的热度值
- `related_news_count`: 相关新闻数量
- `related_titles`: 相关新闻标题（最多3条）

处理建议：
1. 对于跨平台话题，综合多个来源的视角进行深度分析
2. 参考 `related_titles` 了解同一话题的不同角度
3. 聚合热度高的话题优先处理
"""

    return base_prompt + preference_context + cluster_instruction
```

---

### 2.5 完整集成方案

#### 2.5.1 修改后的 InputFeederAgent

```python
# src/agents/input_feeder.py (完整修改版)

import json
import re
import logging
from typing import List, Dict, Any

from .base_agent import BaseAgent
from .news_preprocessor import NewsPreprocessor, NewsCluster
from .news_ranker import NewsRanker
from ..state.user_preferences import PreferenceLearner

logger = logging.getLogger(__name__)

class InputFeederAgent(BaseAgent):
    """增强版 InputFeederAgent

    新增功能:
    1. 新闻去重聚类
    2. 智能热度排序
    3. 用户偏好学习
    4. 跨平台话题识别
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514", vault_path: str = "./vault"):
        super().__init__(model)
        self.preprocessor = NewsPreprocessor()
        self.preference_learner = PreferenceLearner(vault_path)
        self.ranker = NewsRanker(self.preference_learner.get_preference_dict())

    async def process_news(self, news_items: List[Dict[str, Any]], limit: int = 10) -> List[str]:
        """处理新闻为洞察卡片

        增强流程:
        1. 预处理：去重聚类
        2. 评分排序：智能筛选
        3. Agent分析：深度洞察
        4. 解析结果：提取卡片ID

        Args:
            news_items: 原始新闻列表
            limit: 最多处理的新闻数量

        Returns:
            创建的卡片ID列表
        """
        logger.info(f"Processing {len(news_items)} news items")

        # Step 1: 预处理 - 去重聚类
        clusters = self.preprocessor.preprocess(news_items)
        logger.info(f"Clustered into {len(clusters)} groups, "
                   f"{sum(1 for c in clusters if c.cross_platform)} cross-platform")

        # Step 2: 评分排序
        scores = self.ranker.rank(clusters)
        top_clusters = [c for c, s in zip(clusters, scores)][:limit]

        # Step 3: 转换为 Agent 输入
        enriched_items = self.preprocessor.to_agent_input(top_clusters, limit)

        # Step 4: 构建增强 prompt
        user_prefs = self.preference_learner.get_top_preferences()
        prompt = self._build_enhanced_prompt(enriched_items, user_prefs)

        # Step 5: 调用 Agent
        result = await self.run(prompt)

        # Step 6: 解析结果
        card_ids = self._parse_card_ids(result)
        logger.info(f"Created {len(card_ids)} insight cards")

        return card_ids

    def learn_from_selection(self, selected_cards: List[Dict], all_cards: List[Dict]):
        """从用户选择中学习偏好

        应在用户选择卡片后调用，用于持续优化推荐。
        """
        self.preference_learner.learn_from_selection(selected_cards, all_cards)
        # 更新 ranker 的偏好
        self.ranker = NewsRanker(self.preference_learner.get_preference_dict())
        logger.info(f"Updated preferences from {len(selected_cards)} selections")

    def _build_enhanced_prompt(self, items: List[Dict], user_prefs: Dict) -> str:
        """构建增强版 prompt"""

        # 统计跨平台话题
        cross_platform_count = sum(1 for i in items if i.get('is_cross_platform'))

        prompt = f"""# 今日热点深度分析

## 数据概览
- 总话题数: {len(items)}
- 跨平台热点: {cross_platform_count} 个
"""

        # 添加用户偏好提示
        if user_prefs.get('top_keywords'):
            keywords = [kw for kw, _ in user_prefs['top_keywords'][:5]]
            prompt += f"""
## 用户关注领域
根据历史记录，用户特别关注: {', '.join(keywords)}
请优先分析这些领域的相关新闻。
"""

        prompt += f"""
## 待分析话题

{json.dumps(items, ensure_ascii=False, indent=2)}

## 分析要求

### 对于跨平台话题 (is_cross_platform=true)
这些话题在多个平台同时出现，值得深入分析：
1. 综合 `related_titles` 中的不同视角
2. 分析不同平台讨论的差异
3. 寻找差异化的商业机会

### 对于单平台话题
评估其是否具有：
1. 重大变化信号
2. 明确的用户痛点
3. 可行的产品机会

### 输出要求
1. 为每个有价值的洞察创建卡片 (create_card)
2. 跳过纯娱乐/无商业价值的内容
3. 卡片标题必须是你的洞察，不是新闻标题复述
4. 完成后列出所有卡片ID

请开始分析。
"""
        return prompt

    def get_system_prompt(self) -> str:
        """返回增强版系统提示"""
        return """你是一个专业的趋势洞察分析师，具备以下核心能力：

## 核心能力

1. **跨平台模式识别**：识别在多个平台同时出现的话题，这些通常是更重要的信号
2. **深度洞察挖掘**：从表面新闻中挖掘底层变化、用户痛点和商业机会
3. **差异化视角**：从创业者/产品经理角度思考，而非普通读者

## 洞察卡片规范

每张卡片必须包含：
```
title: 你的洞察总结（非新闻标题复述）
content: 详细分析
  - 核心变化：具体发生了什么
  - 影响群体：谁受影响、如何影响
  - 机会要点：可能的产品/服务机会
source: 来源平台
industry: tech/ai | finance | social | other
category: change | pain_point | opportunity
keywords: 3-5个关键词
heat_score: 0-100 (基于商业价值评估)
analysis: {
  change: "变化描述",
  affected_groups: "受影响群体",
  opportunity: "机会描述",
  evidence: "支撑证据"
}
```

## 热度评分标准
- 90-100: 行业重大变革，新品类/市场机会
- 70-89: 显著趋势，大量用户行为改变
- 50-69: 值得关注，明确机会点
- 30-49: 小范围影响，特定人群
- 0-29: 信息性新闻，机会不明确

## 质量红线
1. 禁止复述新闻标题作为卡片标题
2. 每个洞察必须有数据/事实支撑
3. 机会点必须具体到可想象产品形态
"""

    def _parse_card_ids(self, response: str) -> List[str]:
        """从响应中提取卡片ID"""
        pattern = r'card-[a-f0-9]{8}|card-\d{4}-\d{2}-\d{2}-\d{3}'
        return re.findall(pattern, response)
```

#### 2.5.2 main.py 集成修改

```python
# main.py 中的修改

async def morning_push():
    """早间推送 - 增强版"""
    agents = get_agents()

    # 获取更多新闻以供筛选
    raw_news = get_top_items(limit=100)  # 从50增加到100

    # 使用增强版处理（内部会去重聚类）
    card_ids = await agents["input_feeder"].process_news(raw_news, limit=15)

    # ... 后续流程不变 ...

async def handle_card_selection(selected_indices: List[int], all_cards: List[Dict]):
    """处理用户卡片选择 - 新增偏好学习"""
    agents = get_agents()

    # 获取选中的卡片
    selected_cards = [all_cards[i-1] for i in selected_indices if 0 < i <= len(all_cards)]

    # 学习用户偏好
    agents["input_feeder"].learn_from_selection(selected_cards, all_cards)

    # ... 后续流程 ...
```

---

## 3. 文件结构

```
src/agents/
├── __init__.py
├── base_agent.py           # 基础 Agent 类
├── input_feeder.py         # 增强版 InputFeederAgent
├── idea_factory.py         # IdeaFactoryAgent
├── mvp_runner.py           # MVPRunnerAgent
├── news_preprocessor.py    # 新增：新闻预处理器
├── news_ranker.py          # 新增：新闻排序器
└── tools/
    └── obsidian_tools.py   # MCP 工具

src/state/
├── __init__.py
├── state_machine.py        # 状态机
├── obsidian_store.py       # Obsidian 存储
├── schemas.py              # 状态枚举
└── user_preferences.py     # 新增：用户偏好
```

---

## 4. 测试用例

```python
# tests/agents/test_news_preprocessor.py

import pytest
from src.agents.news_preprocessor import NewsPreprocessor, NewsCluster

class TestNewsPreprocessor:

    def test_extract_keywords(self):
        preprocessor = NewsPreprocessor()
        keywords = preprocessor._extract_keywords("苹果发布新款iPhone 16 Pro")
        assert "苹果" in keywords
        assert "iPhone" in keywords
        assert "Pro" in keywords

    def test_cluster_similar_news(self):
        preprocessor = NewsPreprocessor()
        news = [
            {"title": "苹果iPhone 16发布", "source_platform": "36kr", "heat": 90},
            {"title": "iPhone 16 Pro上市", "source_platform": "weibo", "heat": 85},
            {"title": "比特币突破10万美元", "source_platform": "wallstreetcn-hot", "heat": 95},
        ]
        clusters = preprocessor.preprocess(news)

        # 应该聚类为2组
        assert len(clusters) == 2

        # iPhone相关应该是跨平台
        iphone_cluster = next(c for c in clusters if "iPhone" in c.topic)
        assert iphone_cluster.cross_platform == True
        assert len(iphone_cluster.sources) == 2

    def test_to_agent_input_enrichment(self):
        preprocessor = NewsPreprocessor()
        clusters = [
            NewsCluster(
                cluster_id="c1",
                topic="测试话题",
                news_items=[{"title": "新闻1"}, {"title": "新闻2"}],
                sources={"weibo", "zhihu"},
                total_heat=150,
                cross_platform=True,
                representative={"title": "新闻1", "heat": 80}
            )
        ]
        result = preprocessor.to_agent_input(clusters)

        assert len(result) == 1
        assert result[0]['is_cross_platform'] == True
        assert result[0]['aggregated_heat'] == 150
        assert len(result[0]['related_sources']) == 2


# tests/state/test_user_preferences.py

import pytest
import tempfile
from pathlib import Path
from src.state.user_preferences import PreferenceLearner

class TestPreferenceLearner:

    def test_learn_from_selection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = PreferenceLearner(tmpdir)

            selected = [
                {"id": "1", "keywords": ["AI", "创业"], "industry": "tech", "source": "36kr"}
            ]
            all_cards = selected + [
                {"id": "2", "keywords": ["娱乐", "明星"], "industry": "social", "source": "weibo"}
            ]

            learner.learn_from_selection(selected, all_cards)

            prefs = learner.get_preference_dict()
            assert prefs['keywords'].get('AI', 0) > 0
            assert prefs['keywords'].get('创业', 0) > 0

    def test_preference_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # 第一次学习
            learner1 = PreferenceLearner(tmpdir)
            learner1.learn_from_selection(
                [{"keywords": ["测试"], "industry": "tech", "source": "test"}],
                []
            )

            # 重新加载应该保留偏好
            learner2 = PreferenceLearner(tmpdir)
            assert learner2.preferences.keyword_weights.get('测试', 0) > 0
```

---

## 5. 配置项

```yaml
# config/agent_config.yaml

input_feeder:
  # 预处理配置
  preprocessor:
    similarity_threshold: 0.6    # 聚类相似度阈值
    min_cluster_size: 1          # 最小聚类大小

  # 排序配置
  ranker:
    cross_platform_bonus: 30     # 跨平台加成
    multi_platform_bonus: 50     # 3+平台额外加成
    recency_weight: 0.2          # 时效性权重

  # 偏好学习配置
  preference:
    decay_factor: 0.95           # 历史权重衰减
    learning_rate: 0.1           # 学习率
    max_history: 100             # 最大历史记录数

  # 处理限制
  limits:
    fetch_limit: 100             # 获取新闻数量
    process_limit: 15            # 处理新闻数量
    min_heat_threshold: 20       # 最低热度阈值
```

---

## 6. 实施计划

| 阶段 | 任务 | 依赖 |
|------|------|------|
| P1 | 实现 NewsPreprocessor (去重聚类) | 无 |
| P2 | 实现 NewsRanker (智能排序) | P1 |
| P3 | 实现 PreferenceLearner (偏好学习) | 无 |
| P4 | 修改 InputFeederAgent 集成新模块 | P1, P2, P3 |
| P5 | 修改 main.py 调用流程 | P4 |
| P6 | 添加测试用例 | P4 |
| P7 | 配置化参数 | P4 |

---

## 7. 预期效果

| 指标 | 当前 | 目标 |
|------|------|------|
| 重复卡片率 | ~30% | <5% |
| 用户选择命中率 | 未知 | 可追踪 |
| 跨平台话题识别 | 无 | 自动标记 |
| 个性化程度 | 0 | 基于历史偏好 |
| 热度排序准确性 | 随机前10 | 多维度评分 |
