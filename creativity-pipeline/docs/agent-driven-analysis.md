# Agent-Driven News Analysis 设计方案

## 核心理念

**放弃硬编码预处理逻辑，让 Agent 拥有完整上下文并动态分析**

```
传统方案:                          Agent-Driven 方案:
┌─────────┐                       ┌─────────┐
│ Raw News│                       │ Raw News│
└────┬────┘                       └────┬────┘
     │                                 │
     ▼                                 ▼
┌─────────┐                       ┌─────────────────┐
│ 硬编码   │  ← 无法适应变化       │ 保存到本地文件    │
│ 预处理   │                       │ (丰富的上下文)    │
└────┬────┘                       └────────┬────────┘
     │                                      │
     ▼                                      ▼
┌─────────┐                       ┌─────────────────┐
│ Agent   │                       │ Agent 读取文件   │
│ (有限   │                       │ + WebFetch 补充  │
│  上下文)│                       │ + 动态写代码分析  │
└─────────┘                       └─────────────────┘
```

## 1. 数据存储设计

### 1.1 目录结构

```
vault/
├── raw_data/                    # 原始抓取数据
│   ├── 2026-01-12/             # 按日期组织
│   │   ├── morning_fetch.json   # 早间抓取
│   │   ├── afternoon_fetch.json # 下午抓取
│   │   └── summaries/           # 抓取的摘要内容
│   │       ├── item_001.md
│   │       └── item_002.md
│   └── latest.json              # 最新一次抓取
├── cards/                       # 生成的卡片
├── ideas/                       # 生成的创意
└── experiments/                 # 实验记录
```

### 1.2 丰富的数据格式

```json
// vault/raw_data/2026-01-12/morning_fetch.json
{
  "fetch_time": "2026-01-12T09:00:00+08:00",
  "total_items": 150,
  "industries": ["tech/ai", "finance", "social"],
  "items": [
    {
      "id": "news-2026-01-12-001",
      "title": "苹果发布Vision Pro 2，售价下调至2499美元",
      "url": "https://...",
      "source_platform": "36kr",
      "source_name": "36氪",
      "industry": "tech/ai",
      "rank": 1,
      "heat_score": 9500,
      "fetch_time": "2026-01-12T08:55:00+08:00",

      // 新增: 丰富的上下文
      "summary": "苹果在今日发布会上推出Vision Pro 2...(自动抓取或AI生成)",
      "summary_source": "webfetch|ai_generated|manual",
      "keywords": ["苹果", "Vision Pro", "VR", "AR"],
      "related_urls": ["https://..."],

      // 新增: 跨平台信息
      "cross_platform": {
        "is_trending": true,
        "platforms": ["36kr", "weibo", "zhihu"],
        "total_mentions": 3
      }
    }
  ],

  // 新增: 聚合统计
  "statistics": {
    "by_industry": {
      "tech/ai": 50,
      "finance": 40,
      "social": 60
    },
    "cross_platform_topics": 12,
    "top_keywords": ["苹果", "AI", "比特币"]
  }
}
```

### 1.3 摘要获取策略

```python
class SummaryStrategy:
    """摘要获取策略"""

    STRATEGIES = [
        "api_provided",    # 1. API 直接返回摘要
        "webfetch",        # 2. WebFetch 抓取正文前300字
        "ai_generated",    # 3. 基于标题 AI 生成摘要
        "title_only"       # 4. 仅使用标题
    ]
```

## 2. Agent 增强设计

### 2.1 新增 MCP 工具

```python
# src/agents/tools/data_tools.py

@tool("read_raw_news", "读取原始新闻数据文件", {"date": str, "time_slot": str})
async def read_raw_news(args: dict) -> dict:
    """读取指定日期和时段的原始新闻数据

    Args:
        date: 日期 (YYYY-MM-DD)，默认今天
        time_slot: morning|afternoon|evening，默认 latest

    Returns:
        完整的新闻数据 JSON
    """
    pass

@tool("fetch_article_summary", "获取文章摘要", {"url": str, "max_length": int})
async def fetch_article_summary(args: dict) -> dict:
    """使用 WebFetch 获取文章正文摘要

    Args:
        url: 文章 URL
        max_length: 摘要最大长度，默认 300

    Returns:
        文章摘要内容
    """
    pass

@tool("analyze_news_patterns", "分析新闻模式", {"analysis_type": str})
async def analyze_news_patterns(args: dict) -> dict:
    """动态分析新闻数据模式

    Args:
        analysis_type: clustering|trending|cross_platform|sentiment

    Returns:
        分析结果
    """
    pass

@tool("save_analysis_result", "保存分析结果", {"result_type": str, "data": dict})
async def save_analysis_result(args: dict) -> dict:
    """保存分析结果到本地文件

    用于 Agent 动态写代码分析后保存结果
    """
    pass
```

### 2.2 增强的 System Prompt

```python
ENHANCED_SYSTEM_PROMPT = """你是一个专业的趋势洞察分析师，拥有强大的分析工具和完整的数据访问权限。

## 可用工具

### 数据读取
- `read_raw_news`: 读取原始新闻数据 (包含标题、摘要、来源、热度等)
- `fetch_article_summary`: 获取任意文章的正文摘要

### 分析工具
- `analyze_news_patterns`: 执行预定义分析 (聚类/趋势/跨平台/情感)
- `Bash`: 你可以编写 Python 脚本进行自定义分析

### 输出工具
- `create_card`: 创建洞察卡片
- `save_analysis_result`: 保存分析结果

## 分析流程

### 第一步: 数据加载
```
1. 调用 read_raw_news 获取今日新闻数据
2. 浏览数据概览 (统计信息、跨平台话题)
3. 识别需要深入了解的话题
```

### 第二步: 深度挖掘
```
对于重要话题:
1. 如果摘要不足，使用 fetch_article_summary 获取更多内容
2. 对比不同平台的讨论角度
3. 寻找独特的洞察点
```

### 第三步: 动态分析 (可选)
```
如果需要自定义分析，你可以:
1. 使用 Bash 工具执行 Python 脚本
2. 读取 vault/raw_data/latest.json
3. 进行聚类、NLP 分析等
4. 保存结果到 vault/raw_data/analysis/
```

### 第四步: 生成洞察
```
为每个有价值的发现创建卡片，确保:
- 标题是你的洞察，不是新闻复述
- 包含具体数据和证据
- 明确指出商业机会
```

## 数据格式参考

新闻数据包含以下字段:
- title: 新闻标题
- summary: 摘要 (可能为空，需要时请获取)
- url: 原文链接
- source_platform: 来源平台 ID
- source_name: 来源平台名称
- industry: 行业分类
- heat_score: 热度分数 (0-10000)
- cross_platform: 跨平台信息 (如果有)

## 质量要求

1. **不要遗漏重要话题**: 先看统计和跨平台信息，确保覆盖热点
2. **深度优于广度**: 宁可深入分析5个话题，不要浅尝辄止10个
3. **数据支撑**: 每个洞察都要有具体数据
4. **差异化视角**: 从创业者/产品经理角度思考
"""
```

### 2.3 数据获取与存储服务

```python
# src/data_sources/news_store.py

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NewsStore:
    """新闻数据本地存储服务

    负责:
    1. 保存抓取的原始数据
    2. 管理摘要获取
    3. 提供数据查询接口
    """

    def __init__(self, vault_path: str = "./vault"):
        self.vault_path = Path(vault_path)
        self.raw_data_path = self.vault_path / "raw_data"
        self.raw_data_path.mkdir(parents=True, exist_ok=True)

    def save_fetch_result(
        self,
        items: List[Dict[str, Any]],
        time_slot: str = "morning"
    ) -> Path:
        """保存抓取结果

        Args:
            items: 新闻列表
            time_slot: morning|afternoon|evening

        Returns:
            保存的文件路径
        """
        today = datetime.now().strftime("%Y-%m-%d")
        day_path = self.raw_data_path / today
        day_path.mkdir(exist_ok=True)

        # 增强数据
        enriched_items = self._enrich_items(items)

        # 计算统计信息
        statistics = self._calculate_statistics(enriched_items)

        # 构建完整数据
        data = {
            "fetch_time": datetime.now().isoformat(),
            "time_slot": time_slot,
            "total_items": len(enriched_items),
            "items": enriched_items,
            "statistics": statistics
        }

        # 保存到日期目录
        file_path = day_path / f"{time_slot}_fetch.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新 latest.json
        latest_path = self.raw_data_path / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(items)} items to {file_path}")
        return file_path

    def _enrich_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """增强新闻数据

        添加:
        - 唯一 ID
        - 跨平台检测
        - 关键词提取 (简单版)
        """
        # 按标题分组检测跨平台
        from collections import defaultdict
        import re

        title_map = defaultdict(list)
        for item in items:
            # 简单归一化
            normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', item.get('title', '').lower())[:30]
            title_map[normalized].append(item)

        # 标记跨平台
        enriched = []
        today = datetime.now().strftime("%Y-%m-%d")

        for i, item in enumerate(items):
            normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', item.get('title', '').lower())[:30]
            related = title_map.get(normalized, [])
            platforms = list(set(r.get('source_platform', '') for r in related))

            enriched_item = {
                **item,
                "id": f"news-{today}-{i+1:03d}",
                "summary": item.get("summary", ""),  # 可能为空
                "cross_platform": {
                    "is_trending": len(platforms) > 1,
                    "platforms": platforms,
                    "total_mentions": len(related)
                }
            }
            enriched.append(enriched_item)

        return enriched

    def _calculate_statistics(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算统计信息"""
        from collections import Counter

        industries = Counter(item.get('industry', 'unknown') for item in items)
        sources = Counter(item.get('source_platform', 'unknown') for item in items)
        cross_platform = sum(1 for item in items if item.get('cross_platform', {}).get('is_trending'))

        return {
            "by_industry": dict(industries),
            "by_source": dict(sources),
            "cross_platform_topics": cross_platform,
        }

    def load_latest(self) -> Optional[Dict[str, Any]]:
        """加载最新数据"""
        latest_path = self.raw_data_path / "latest.json"
        if latest_path.exists():
            with open(latest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def load_by_date(self, date: str, time_slot: str = "morning") -> Optional[Dict[str, Any]]:
        """按日期加载数据"""
        file_path = self.raw_data_path / date / f"{time_slot}_fetch.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
```

## 3. 抓取流程改进

### 3.1 带摘要的抓取

```python
# src/data_sources/enhanced_fetcher.py

import asyncio
from typing import List, Dict, Any
from .newsnow_adapter import NewsNowAdapter, get_top_items
from .news_store import NewsStore

async def fetch_with_summaries(
    limit: int = 100,
    fetch_summaries: bool = True,
    max_summary_fetch: int = 20
) -> List[Dict[str, Any]]:
    """抓取新闻并获取摘要

    Args:
        limit: 最大新闻数
        fetch_summaries: 是否获取摘要
        max_summary_fetch: 最多为多少条获取摘要 (按热度排序)

    Returns:
        带摘要的新闻列表
    """
    # 1. 基础抓取
    items = get_top_items(limit=limit)

    # 2. 为热门新闻获取摘要
    if fetch_summaries:
        # 按热度排序，取 top N
        sorted_items = sorted(items, key=lambda x: -x.get('heat_score', 0))
        top_items = sorted_items[:max_summary_fetch]

        # 并发获取摘要 (使用 WebFetch 或其他方式)
        summaries = await _batch_fetch_summaries([item['url'] for item in top_items])

        # 合并摘要
        url_to_summary = dict(zip([item['url'] for item in top_items], summaries))
        for item in items:
            item['summary'] = url_to_summary.get(item['url'], '')

    return items

async def _batch_fetch_summaries(urls: List[str], max_concurrent: int = 5) -> List[str]:
    """批量获取摘要

    使用信号量控制并发
    """
    import aiohttp
    from bs4 import BeautifulSoup

    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(url: str) -> str:
        async with semaphore:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        # 尝试提取正文前300字
                        # 常见的正文容器
                        for selector in ['article', '.article-content', '.post-content', 'main']:
                            content = soup.select_one(selector)
                            if content:
                                text = content.get_text(strip=True)[:300]
                                return text + '...' if len(text) == 300 else text

                        # 回退: 取 body 文本
                        body = soup.body
                        if body:
                            return body.get_text(strip=True)[:300] + '...'

                        return ''
            except Exception as e:
                return ''

    tasks = [fetch_one(url) for url in urls]
    return await asyncio.gather(*tasks)
```

### 3.2 集成到 main.py

```python
# main.py 修改

async def morning_push():
    """早间推送 - 增强版"""

    # 1. 抓取数据 (带摘要)
    from src.data_sources.enhanced_fetcher import fetch_with_summaries
    from src.data_sources.news_store import NewsStore

    items = await fetch_with_summaries(
        limit=100,
        fetch_summaries=True,
        max_summary_fetch=30  # 为 Top 30 获取摘要
    )

    # 2. 保存到本地
    store = NewsStore()
    store.save_fetch_result(items, time_slot="morning")

    # 3. Agent 读取本地文件进行分析
    # Agent 现在可以:
    #   - 读取完整数据 (包括摘要、跨平台信息)
    #   - 使用 WebFetch 获取更多内容
    #   - 动态写代码分析
    agents = get_agents()
    card_ids = await agents["input_feeder"].analyze_news()  # 新方法

    # 后续流程...
```

## 4. InputFeederAgent 重构

### 4.1 新的分析方法

```python
# src/agents/input_feeder.py

class InputFeederAgent(BaseAgent):
    """重构后的 InputFeederAgent

    不再接收预处理的数据，而是:
    1. 读取本地原始数据文件
    2. 拥有完整上下文
    3. 动态分析和生成洞察
    """

    async def analyze_news(self) -> List[str]:
        """分析新闻并生成洞察卡片

        Agent 会:
        1. 读取 vault/raw_data/latest.json
        2. 分析跨平台话题、热度趋势
        3. 对重要话题获取更多摘要
        4. 生成洞察卡片

        Returns:
            创建的卡片 ID 列表
        """
        prompt = """# 今日新闻洞察分析

请执行以下分析流程:

## 第一步: 加载数据
使用 read_raw_news 工具读取今日新闻数据。

## 第二步: 快速扫描
1. 查看统计信息 (statistics)，了解数据分布
2. 识别跨平台热点 (cross_platform.is_trending=true)
3. 按热度排序，找出 Top 20

## 第三步: 深度分析
对于 Top 10 或跨平台话题:
1. 如果 summary 为空，使用 fetch_article_summary 获取
2. 分析不同平台的讨论角度差异
3. 挖掘底层变化和商业机会

## 第四步: 生成洞察
使用 create_card 为每个有价值的发现创建卡片。

要求:
- 优先处理跨平台话题 (多平台关注=更重要)
- 卡片标题必须是你的洞察，不是新闻复述
- 每个洞察需要数据支撑
- 关注创业者/产品经理视角的机会

请开始分析。
"""
        result = await self.run(prompt)
        return self._parse_card_ids(result)
```

## 5. 优势对比

| 维度 | 硬编码预处理 | Agent-Driven |
|------|-------------|--------------|
| 灵活性 | 固定算法 | 动态适应 |
| 上下文 | 丢失原始信息 | 完整保留 |
| 摘要获取 | 预先批量获取 | 按需获取 |
| 分析深度 | 浅层模式匹配 | 深度理解 |
| 可扩展性 | 需改代码 | 改 Prompt 即可 |
| 调试难度 | 代码调试 | 日志+结果文件 |

## 6. 实施计划

| 阶段 | 任务 | 优先级 |
|------|------|--------|
| P1 | NewsStore: 本地数据存储 | 高 |
| P2 | 增强 fetcher: 带摘要抓取 | 高 |
| P3 | 新增 MCP 工具: read_raw_news, fetch_article_summary | 高 |
| P4 | 重构 InputFeederAgent | 中 |
| P5 | 更新 main.py 流程 | 中 |

## 7. 数据文件示例

```json
// vault/raw_data/latest.json (实际示例)
{
  "fetch_time": "2026-01-12T09:00:00+08:00",
  "time_slot": "morning",
  "total_items": 150,
  "statistics": {
    "by_industry": {"tech/ai": 50, "finance": 40, "social": 60},
    "by_source": {"weibo": 20, "zhihu": 15, "36kr": 12, ...},
    "cross_platform_topics": 8
  },
  "items": [
    {
      "id": "news-2026-01-12-001",
      "title": "苹果Vision Pro 2发布：售价2499美元，性能提升40%",
      "url": "https://36kr.com/p/xxx",
      "source_platform": "36kr",
      "source_name": "36氪",
      "industry": "tech/ai",
      "rank": 1,
      "heat_score": 9500,
      "summary": "苹果今日在特别活动中发布了Vision Pro 2，新一代头显设备定价2499美元起，较前代下调40%。主要升级包括M3芯片、更轻的重量(降低30%)、以及8小时续航。库克表示这是'空间计算走向大众的关键一步'...",
      "cross_platform": {
        "is_trending": true,
        "platforms": ["36kr", "weibo", "zhihu", "v2ex"],
        "total_mentions": 4
      }
    },
    {
      "id": "news-2026-01-12-002",
      "title": "比特币突破15万美元创历史新高",
      "url": "https://wallstreetcn.com/xxx",
      "source_platform": "wallstreetcn-hot",
      "source_name": "华尔街见闻",
      "industry": "finance",
      "rank": 1,
      "heat_score": 9200,
      "summary": "",  // 摘要为空，Agent可按需获取
      "cross_platform": {
        "is_trending": true,
        "platforms": ["wallstreetcn-hot", "xueqiu", "weibo"],
        "total_mentions": 3
      }
    }
    // ... 更多新闻
  ]
}
```

这样 Agent 读取文件后就拥有了完整的上下文，可以智能决定:
- 哪些话题需要深入分析
- 是否需要获取更多摘要
- 如何跨平台综合分析
- 动态编写分析代码
