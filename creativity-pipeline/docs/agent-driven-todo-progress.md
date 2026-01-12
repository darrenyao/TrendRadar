# Agent-Driven Analysis - TODO & 落地进展

> 创建时间: 2026-01-12
> 最后更新: 2026-01-12

## 一、方案演进历程

最初制定了 **InputFeeder Enhancement** 方案（硬编码预处理），后根据用户反馈调整为 **Agent-Driven Analysis** 方案（动态分析）。

```
第一版方案 (input-feeder-enhancement.md)    第二版方案 (agent-driven-analysis.md)
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│ 硬编码预处理逻辑                   │  →   │ 保存完整上下文到本地文件           │
│ - NewsPreprocessor (N-gram聚类)  │       │ - 让 Agent 读取并动态分析          │
│ - NewsRanker (多维度评分)         │       │ - NewsRanker 提供优先级标记        │
│ - PreferenceLearner (偏好学习)   │       │ - 更灵活、可扩展                   │
└─────────────────────────────────┘       └─────────────────────────────────┘
```

---

## 二、Agent-Driven 方案实施进度

| 阶段 | 任务 | 优先级 | 状态 | 说明 |
|------|------|--------|------|------|
| **P1** | NewsStore: 本地数据存储 | 高 | ✅ 完成 | `src/data_sources/news_store.py` |
| **P2** | 新增 MCP 工具 | 高 | ✅ 完成 | `src/agents/tools/data_tools.py` |
| **P3** | 重构 InputFeederAgent | 中 | ✅ 完成 | 新增 `analyze_news()` 方法 |
| **P4** | 更新 main.py 流程 | 中 | ✅ 完成 | 集成 NewsStore |
| **P5** | NewsRanker: 优先级评分 | 中 | ✅ 完成 | `src/data_sources/news_ranker.py` |
| P6 | 增强 fetcher: 批量预获取摘要 | 低 | ⏸️ 暂缓 | Agent 按需获取更灵活 |

---

## 三、已完成的核心组件

### 3.1 NewsStore (`src/data_sources/news_store.py`)

```python
class NewsStore:
    """本地数据存储服务"""

    def save_fetch_result(items, time_slot) -> Path:
        # 保存到 vault/raw_data/{date}/{time_slot}_fetch.json
        # 自动增强: ID生成、跨平台检测、优先级评分、统计计算

    def load_latest() -> Dict                    # 读取最新数据
    def load_by_date(date, time_slot) -> Dict    # 按日期读取
    def search_items(query, limit) -> List       # 搜索
    def update_item_summary(item_id, summary)    # 更新摘要
```

### 3.2 NewsRanker (`src/data_sources/news_ranker.py`) - 新增

多维度优先级评分系统，帮助 Agent 快速识别最重要的内容：

```python
class NewsRanker:
    """多维度新闻排序器"""

    # 评分维度
    # 1. heat_score: 原始热度 (0-100)
    # 2. cross_platform_bonus: 跨平台加成 (0-50)
    # 3. source_weight: 来源权重 (0.5-1.5)
    # 4. recency_score: 时效性 (0-20)

    # 优先级分级
    # - critical (90+): 行业重大事件，必须分析
    # - high (70-89): 重要趋势，优先分析
    # - medium (50-69): 值得关注，选择性分析
    # - low (<50): 一般信息，可跳过

    def score_item(item, cross_platform_info) -> NewsScore
    def rank_items(items) -> List[Dict]  # 返回带优先级的排序列表
    def get_statistics(items) -> Dict    # 优先级分布统计
```

**来源权重配置**：
| 来源 | 权重 | 说明 |
|------|------|------|
| hackernews, producthunt | 1.5 | 科技前沿 |
| 36kr, wallstreetcn-hot | 1.4 | 商业洞察 |
| github-trending, cls-hot, xueqiu | 1.3 | 技术/金融 |
| zhihu, v2ex, sspai | 1.2 | 深度讨论 |
| weibo, bilibili | 1.0 | 大众热点 |
| douyin, baidu | 0.9 | 娱乐倾向 |

### 3.3 MCP 数据工具 (`src/agents/tools/data_tools.py`)

| 工具 | 功能 | 参数 |
|------|------|------|
| `read_raw_news` | 读取本地新闻数据 | date, time_slot |
| `search_news` | 按关键词搜索 | query, limit |
| `get_news_item` | 获取单条详情 | item_id |
| `fetch_article_summary` | 抓取文章摘要 | url, item_id |

### 3.4 InputFeederAgent 重构

```python
# 新方法: Agent-Driven 分析
async def analyze_news(self) -> List[str]:
    """Agent 读取本地文件并动态分析"""
    # 1. 使用 read_raw_news 读取数据
    # 2. 查看 statistics.by_priority 了解优先级分布
    # 3. 优先处理 critical/high 优先级条目
    # 4. 按需使用 fetch_article_summary 获取摘要
    # 5. 创建洞察卡片

# 保留: 向后兼容
async def process_news(self, news_items) -> List[str]:
    """传统方法，接收预处理数据"""
```

### 3.5 main.py 集成

```python
async def morning_push():
    # 1. 抓取数据 (增加到100条)
    raw_news = get_top_items(limit=100)

    # 2. 保存到 NewsStore (自动计算优先级)
    store = NewsStore()
    store.save_fetch_result(raw_news, time_slot="morning")

    # 3. Agent 读取本地数据分析 (按优先级处理)
    card_ids = await agents["input_feeder"].analyze_news()
```

---

## 四、数据格式示例

```json
// vault/raw_data/latest.json
{
  "fetch_time": "2026-01-12T09:00:00+08:00",
  "time_slot": "morning",
  "total_items": 100,
  "statistics": {
    "by_industry": {"tech/ai": 35, "finance": 25, "social": 40},
    "by_source": {"weibo": 15, "36kr": 12, "zhihu": 10},
    "cross_platform_count": 8,
    "top_items": [...],
    "by_priority": {
      "critical": 3,
      "high": 12,
      "medium": 35,
      "low": 50
    },
    "priority_top_items": [
      {"title": "苹果Vision Pro 2发布...", "score": 95.2, "level": "critical"},
      {"title": "比特币突破15万美元...", "score": 88.5, "level": "high"}
    ]
  },
  "items": [
    {
      "id": "news-2026-01-12-001",
      "title": "苹果Vision Pro 2发布",
      "url": "https://36kr.com/...",
      "source_platform": "36kr",
      "industry": "tech/ai",
      "heat_score": 9500,
      "summary": "",
      "cross_platform": {
        "is_trending": true,
        "platforms": ["36kr", "weibo", "zhihu"],
        "total_mentions": 3
      },
      "priority": {
        "total_score": 95.2,
        "priority_level": "critical",
        "breakdown": {
          "heat": 95.0,
          "cross_platform": 35.0,
          "source_weight": 1.4,
          "recency": 19.6
        }
      }
    }
  ]
}
```

---

## 五、测试覆盖

| 模块 | 测试文件 | 测试数 | 状态 |
|------|----------|--------|------|
| NewsStore | `tests/data_sources/test_news_store.py` | 21 | ✅ 全部通过 |
| NewsRanker | `tests/data_sources/test_news_ranker.py` | 17 | ✅ 全部通过 |
| NewsPreprocessor | `tests/agents/test_news_preprocessor.py` | 29 | ✅ 全部通过 |
| InputFeederAgent | `tests/agents/test_input_feeder.py` | 6 | ✅ 全部通过 |
| **总计** | | **179** | **178 passed** |

---

## 六、TODO: 待落地部分

### 6.1 高优先级

- [ ] **端到端验证**: 运行完整 morning_push 流程，验证 Agent 能正确读取数据并创建卡片
- [ ] **错误处理增强**: NewsStore 读写失败时的降级策略
- [ ] **Agent 日志增强**: 添加工具调用和响应详情日志（已完成部分）

### 6.2 中优先级

- [ ] **用户偏好学习 (PreferenceLearner)**
  - 从用户的卡片选择中学习偏好
  - 持久化到 `vault/user_preferences.json`
  - 在 Agent prompt 中注入偏好上下文
  - 动态调整 NewsRanker 的评分权重

- [ ] **历史数据分析**
  - 跨天主题追踪，识别持续热点
  - 对比昨日数据，标记"新出现"vs"持续热门"

### 6.3 低优先级

- [ ] **摘要预获取优化**
  - 对高热度 Top 30 预获取摘要
  - 使用 `enhanced_fetcher.py` 中的批量获取逻辑

- [ ] **质量评估反馈**
  - 记录 Agent 生成的卡片被用户选中的比例
  - 用于评估和优化 Agent prompt

---

## 七、组件状态总结

| 组件 | 原设计 | 现状 | 文件位置 |
|------|--------|------|----------|
| NewsStore | 本地数据存储 | ✅ 完成 | `src/data_sources/news_store.py` |
| NewsRanker | 多维度评分排序 | ✅ 完成 | `src/data_sources/news_ranker.py` |
| NewsPreprocessor | N-gram 关键词聚类 | ✅ 已实现但非主流程 | `src/agents/news_preprocessor.py` |
| PreferenceLearner | 用户偏好学习 | ❌ 待实现 | - |

---

## 八、方案优势对比

| 维度 | 硬编码预处理 | Agent-Driven (当前) |
|------|-------------|---------------------|
| 灵活性 | 固定算法 | ✅ 动态适应 |
| 上下文 | 丢失原始信息 | ✅ 完整保留 |
| 优先级 | 无 | ✅ 多维度评分 |
| 摘要获取 | 预先批量获取 | ✅ 按需获取 |
| 可扩展性 | 需改代码 | ✅ 改 Prompt 即可 |
| 调试 | 代码调试 | ✅ 日志+结果文件 |

---

## 九、相关文档

- 初版设计: `docs/input-feeder-enhancement.md`
- Agent-Driven 设计: `docs/agent-driven-analysis.md`
- 项目总体设计: `docs/creativity-pipeline-design.md`

---

## 十、变更日志

| 日期 | 变更内容 |
|------|----------|
| 2026-01-12 | 初始文档创建，记录 P1-P4 完成状态 |
| 2026-01-12 | 新增 NewsRanker 优先级评分系统 (P5)，集成到 NewsStore |
| 2026-01-12 | 更新 Agent prompt 支持优先级分析，添加 17 个测试用例 |
