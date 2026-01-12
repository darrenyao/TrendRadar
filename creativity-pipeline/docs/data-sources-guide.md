# 数据源适配器开发指南

本文档说明 Creativity Pipeline 的数据源架构、TikHub API 使用方式，以及如何扩展自定义数据源。

## 目录

- [架构概览](#架构概览)
- [TikHub API 使用](#tikhub-api-使用)
- [扩展方案：自定义爬虫](#扩展方案自定义爬虫)
- [配置说明](#配置说明)
- [注意事项](#注意事项)

---

## 架构概览

### 目录结构

```
src/data_sources/
├── base.py              # 抽象基类 BaseDataSourceAdapter, RawNewsItem
├── tikhub_adapter.py    # TikHub API 适配器 (Twitter/Reddit/小红书/微博)
├── newsnow_adapter.py   # NewsNow 适配器 (国内平台热搜)
├── unified_fetcher.py   # 统一数据获取器
└── __init__.py
```

### 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedDataFetcher                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   NewsNow    │  │   TikHub     │  │   Custom     │       │
│  │   Adapter    │  │   Adapter    │  │   Adapter    │       │
│  │  (国内热搜)  │  │ (国际平台)   │  │  (方案C)     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                 │                │
│         ▼                 ▼                 ▼                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              RawNewsItem (统一数据格式)               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 基类定义

```python
# base.py
class RawNewsItem:
    """统一的新闻数据结构"""
    title: str              # 标题
    url: str                # 链接
    source_platform: str    # 来源平台 (twitter/weibo/xiaohongshu等)
    source_type: SourceType # 数据源类型 (NEWSNOW/TIKHUB/CUSTOM)
    content_type: ContentType # 内容类型 (TRENDING/DISCUSSION/HOT_SEARCH等)
    content: str            # 内容摘要
    author: str             # 作者
    rank: int               # 排名
    heat_score: int         # 热度分数 (0-10000)
    engagement: dict        # 互动数据 (likes/comments/shares等)
    tags: List[str]         # 标签
    raw_data: dict          # 原始数据

class BaseDataSourceAdapter(ABC):
    """数据源适配器基类"""

    @abstractmethod
    def get_supported_platforms(self) -> List[str]:
        """返回支持的平台列表"""
        pass

    @abstractmethod
    def fetch_platform(self, platform: str, limit: int = 20) -> List[RawNewsItem]:
        """获取指定平台的数据"""
        pass
```

---

## TikHub API 使用

### 认证方式

```python
# 环境变量
TIKHUB_API_KEY=your_api_key

# 请求头
headers = {
    "Authorization": f"Bearer {TIKHUB_API_KEY}",
    "Content-Type": "application/json",
}
```

### 已验证的端点

| 平台 | 端点 | 数据路径 | 单次价格 |
|------|------|----------|----------|
| **Twitter** | `/api/v1/twitter/web/fetch_trending` | `data.trends[]` | ~$0.01 |
| **Reddit** | `/api/v1/reddit/app/fetch_popular_feed` | `data.popularfeed.postsInfoByIds[]` | ~$0.01 |
| **小红书** | `/api/v1/xiaohongshu/web_v2/fetch_hot_list` | `data.data.items[]` | ~$0.01 |
| **微博** | `/api/v1/weibo/web_v2/fetch_hot_search` | `data.realtime[]` | ~$0.01 |

### 响应数据结构

#### Twitter Trending

```json
{
  "data": {
    "trends": [
      {
        "name": "#话题名",
        "description": "话题描述",
        "url": "https://twitter.com/search?q=..."
      }
    ]
  }
}
```

#### Reddit Popular

```json
{
  "data": {
    "popularfeed": {
      "postsInfoByIds": [
        {
          "postTitle": "帖子标题",
          "subreddit": {
            "name": "technology",
            "prefixedName": "r/technology"
          },
          "upvoteCount": 1234,
          "commentCount": 56,
          "url": "/r/technology/comments/xxx"
        }
      ]
    }
  }
}
```

#### 小红书热榜

```json
{
  "data": {
    "data": {
      "items": [
        {
          "title": "热搜标题",
          "score": "923.7万",
          "id": "dora_xxx",
          "word_type": "新",
          "type": "normal"
        }
      ]
    }
  }
}
```

#### 微博热搜

```json
{
  "data": {
    "realtime": [
      {
        "word": "热搜话题",
        "num": 1080845,
        "rank": 0,
        "note": "话题备注",
        "label_name": "热/新/沸"
      }
    ]
  }
}
```

### 缓存机制

TikHub 返回的响应包含 `cache_url` 字段，24小时内访问缓存不计费：

```json
{
  "cache_url": "https://cache.tikhub.io/api/v1/cache/public/xxx?sign=yyy",
  "cache_message": "有效期24小时，访问缓存不产生额外费用"
}
```

### 错误码说明

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 200 | 成功 | - |
| 400 | 参数错误 | 检查请求参数 |
| 402 | 余额不足 | 在 tikhub.io 充值 |
| 403 | Token 权限不足 | 在 user.tikhub.io 添加端点权限 |
| 404 | 端点不存在 | 检查 API 路径 |
| 422 | 缺少必需参数 | 补充必需的查询参数 |
| 429 | 请求过于频繁 | 降低请求频率 |

---

## 扩展方案：自定义爬虫

当 TikHub 不支持某些平台，或需要降低成本时，可以使用自定义爬虫（方案C）。

### 创建自定义适配器

```python
# src/data_sources/custom_adapter.py

from typing import List, Dict, Any
import requests
import time

from .base import (
    BaseDataSourceAdapter,
    RawNewsItem,
    SourceType,
    ContentType,
)

class CustomAdapter(BaseDataSourceAdapter):
    """自定义爬虫适配器"""

    source_type = SourceType.CUSTOM

    # 平台配置
    PLATFORM_CONFIG = {
        "v2ex": {
            "name": "V2EX",
            "url": "https://www.v2ex.com/api/topics/hot.json",
            "content_type": ContentType.DISCUSSION,
            "weight": 1.2,
        },
        "sspai": {
            "name": "少数派",
            "url": "https://sspai.com/api/v1/article/index/page/get",
            "params": {"limit": 20, "offset": 0},
            "content_type": ContentType.NEWS,
            "weight": 1.0,
        },
        "juejin": {
            "name": "掘金",
            "url": "https://api.juejin.cn/content_api/v1/content/article_rank",
            "method": "POST",
            "body": {"category_id": "1", "type": "hot"},
            "content_type": ContentType.DISCUSSION,
            "weight": 1.1,
        },
    }

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        })

        # 请求限速
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 秒

    def _rate_limit(self):
        """请求限速"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _request(self, url: str, method: str = "GET",
                 params: dict = None, json: dict = None) -> Dict:
        """发起请求（带重试）"""
        self._rate_limit()

        for attempt in range(3):
            try:
                if method.upper() == "POST":
                    resp = self.session.post(url, params=params, json=json, timeout=10)
                else:
                    resp = self.session.get(url, params=params, timeout=10)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        return {}

    def get_supported_platforms(self) -> List[str]:
        return list(self.PLATFORM_CONFIG.keys())

    def fetch_platform(self, platform: str, limit: int = 20) -> List[RawNewsItem]:
        if platform not in self.PLATFORM_CONFIG:
            return []

        config = self.PLATFORM_CONFIG[platform]

        # 根据平台调用对应的解析器
        parser = getattr(self, f"_parse_{platform}", None)
        if not parser:
            return []

        try:
            data = self._request(
                config["url"],
                method=config.get("method", "GET"),
                params=config.get("params"),
                json=config.get("body"),
            )
            return parser(data, limit, config)
        except Exception as e:
            logger.error(f"Failed to fetch {platform}: {e}")
            return []

    # ==================== 平台解析器 ====================

    def _parse_v2ex(self, data: List, limit: int, config: dict) -> List[RawNewsItem]:
        """解析 V2EX 热门话题"""
        items = []
        for rank, topic in enumerate(data[:limit], 1):
            item = RawNewsItem(
                title=topic.get("title", ""),
                url=topic.get("url", ""),
                source_platform="v2ex",
                source_type=SourceType.CUSTOM,
                content_type=config["content_type"],
                content=topic.get("content", "")[:500],
                author=topic.get("member", {}).get("username", ""),
                rank=rank,
                engagement={
                    "replies": topic.get("replies", 0),
                },
                tags=[topic.get("node", {}).get("title", "")],
                raw_data=topic,
            )
            item.heat_score = self._calculate_score(item)
            items.append(item)
        return items

    def _parse_sspai(self, data: dict, limit: int, config: dict) -> List[RawNewsItem]:
        """解析少数派文章"""
        items = []
        articles = data.get("data", [])
        for rank, article in enumerate(articles[:limit], 1):
            item = RawNewsItem(
                title=article.get("title", ""),
                url=f"https://sspai.com/post/{article.get('id', '')}",
                source_platform="sspai",
                source_type=SourceType.CUSTOM,
                content_type=config["content_type"],
                content=article.get("summary", ""),
                author=article.get("author", {}).get("nickname", ""),
                rank=rank,
                engagement={
                    "likes": article.get("like_count", 0),
                    "comments": article.get("comment_count", 0),
                },
                tags=article.get("tags", []),
                raw_data=article,
            )
            item.heat_score = self._calculate_score(item)
            items.append(item)
        return items

    def _parse_juejin(self, data: dict, limit: int, config: dict) -> List[RawNewsItem]:
        """解析掘金热门"""
        items = []
        articles = data.get("data", [])
        for rank, article in enumerate(articles[:limit], 1):
            content = article.get("content", {})
            item = RawNewsItem(
                title=content.get("title", ""),
                url=f"https://juejin.cn/post/{article.get('content_id', '')}",
                source_platform="juejin",
                source_type=SourceType.CUSTOM,
                content_type=config["content_type"],
                content=content.get("brief_content", ""),
                author=article.get("author", {}).get("name", ""),
                rank=rank,
                engagement={
                    "views": content.get("view_count", 0),
                    "likes": content.get("digg_count", 0),
                    "comments": content.get("comment_count", 0),
                },
                tags=[t.get("tag_name", "") for t in content.get("tags", [])],
                raw_data=article,
            )
            item.heat_score = self._calculate_score(item)
            items.append(item)
        return items

    def _calculate_score(self, item: RawNewsItem) -> int:
        """计算热度分数"""
        engagement = item.engagement
        score = (
            engagement.get("likes", 0) * 1 +
            engagement.get("comments", 0) * 3 +
            engagement.get("replies", 0) * 3 +
            engagement.get("views", 0) * 0.01
        )
        # 排名权重
        rank_bonus = max(0, 100 - (item.rank - 1) * 5)
        return min(10000, int(score + rank_bonus))
```

### 添加新平台的步骤

1. **在 `PLATFORM_CONFIG` 添加配置**

```python
"new_platform": {
    "name": "平台显示名",
    "url": "https://api.example.com/hot",
    "method": "GET",  # 或 "POST"
    "params": {},     # URL 参数
    "body": {},       # POST 请求体
    "headers": {},    # 额外请求头
    "content_type": ContentType.DISCUSSION,
    "weight": 1.0,
}
```

2. **实现解析器方法**

```python
def _parse_new_platform(self, data: dict, limit: int, config: dict) -> List[RawNewsItem]:
    """解析新平台数据"""
    items = []
    # 根据 API 响应结构提取列表
    raw_items = data.get("data", {}).get("list", [])

    for rank, raw in enumerate(raw_items[:limit], 1):
        item = RawNewsItem(
            title=raw.get("title", ""),
            url=raw.get("url", ""),
            source_platform="new_platform",
            source_type=SourceType.CUSTOM,
            content_type=config["content_type"],
            engagement={
                "likes": raw.get("like_count", 0),
            },
            raw_data=raw,
        )
        item.heat_score = self._calculate_score(item)
        items.append(item)

    return items
```

3. **在配置文件中启用**

```yaml
# config/industries.yaml
providers:
  custom:
    enabled: true
    description: 自定义爬虫模块

industries:
  tech/ai:
    sources:
      - id: new_platform
        name: 新平台
        provider: custom
        weight: 1.0
        category: discussion
```

4. **在 unified_fetcher.py 中注册**

```python
# 在 _init_adapters 方法中添加
if providers.get("custom", {}).get("enabled", False):
    from .custom_adapter import CustomAdapter
    self.adapters["custom"] = CustomAdapter()
    logger.info("Custom adapter initialized")
```

### 防反爬策略

```python
class CustomAdapter(BaseDataSourceAdapter):
    def __init__(self):
        # 随机 User-Agent
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
        ]

        # 代理池（可选）
        self.proxies = [
            {"http": "http://proxy1:port", "https": "http://proxy1:port"},
            {"http": "http://proxy2:port", "https": "http://proxy2:port"},
        ]
        self._proxy_index = 0

    def _get_headers(self) -> dict:
        """获取随机请求头"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def _get_proxy(self) -> dict:
        """轮询获取代理"""
        if not self.proxies:
            return {}
        proxy = self.proxies[self._proxy_index % len(self.proxies)]
        self._proxy_index += 1
        return proxy

    def _request(self, url: str, **kwargs) -> dict:
        """带防反爬的请求"""
        self._rate_limit()

        headers = self._get_headers()
        headers.update(kwargs.pop("headers", {}))

        for attempt in range(3):
            try:
                resp = self.session.get(
                    url,
                    headers=headers,
                    proxies=self._get_proxy(),
                    timeout=10,
                    **kwargs
                )

                # 检测反爬
                if resp.status_code == 403 or "验证" in resp.text:
                    logger.warning(f"Anti-crawler detected for {url}")
                    time.sleep(5)
                    continue

                resp.raise_for_status()
                return resp.json()

            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

        return {}
```

---

## 配置说明

### 环境变量 (.env)

```bash
# TikHub API (国际平台)
TIKHUB_API_KEY=your_api_key

# 代理配置（可选，用于自定义爬虫）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 数据源配置 (config/industries.yaml)

```yaml
# 数据源提供商
providers:
  newsnow:
    enabled: true
    api_base: https://newsnow.busiyi.world/api/s
    description: 国内平台热搜聚合

  tikhub:
    enabled: true
    api_base: https://api.tikhub.io
    description: Twitter/Reddit/小红书等国际平台

  custom:
    enabled: false  # 启用自定义爬虫
    description: 自定义爬虫模块

# 行业分类及数据源
industries:
  tech/ai:
    name: 科技/AI
    sources:
      # NewsNow 数据源
      - id: zhihu
        provider: newsnow
        weight: 1.3
        pain_point_value: high

      # TikHub 数据源
      - id: twitter
        provider: tikhub
        weight: 1.3
        pain_point_value: high

      # 自定义数据源
      - id: v2ex
        provider: custom
        weight: 1.2
```

---

## 测试模式 (Mock Data)

在开发和测试时，可以使用 `--mock-data` 参数避免消耗 TikHub API 额度。

### 使用方法

```bash
# 使用 mock 数据运行测试
python -m src.main --mode once --touch-point morning --mock-data

# 或设置环境变量
export MOCK_DATA_SOURCES=1
python -m src.main --mode once --touch-point morning
```

### Mock 数据覆盖的平台

| 平台 | 数据量 | 内容主题 |
|------|--------|----------|
| Twitter | 10 条 | AI、编程、创业相关热门话题 |
| Reddit | 8 条 | SaaS、独立开发、效率工具讨论 |
| 小红书 | 10 条 | 程序员、远程办公、工具推荐 |
| 微博 | 10 条 | AI、创业、技术热搜 |
| 知乎 | 8 条 | 程序员职业发展、创业问题 |

### 扩展 Mock 数据

如需添加新平台的 mock 数据，编辑 `src/data_sources/mock_data.py`：

```python
def get_mock_new_platform_data(limit: int = 20) -> List[RawNewsItem]:
    """Generate mock data for new platform."""
    mock_items = [
        {"title": "话题1", ...},
        {"title": "话题2", ...},
    ]
    # 转换为 RawNewsItem 列表
    ...

# 注册到 MOCK_DATA_FUNCTIONS
MOCK_DATA_FUNCTIONS["new_platform"] = get_mock_new_platform_data
```

---

## 注意事项

### TikHub 使用注意

1. **Token 权限管理**: 在 https://user.tikhub.io/ 为 API Token 添加所需平台的权限
2. **利用缓存**: 相同请求 24 小时内访问 `cache_url` 不计费
3. **响应结构差异**: 每个平台的数据嵌套层级不同，需要灵活处理
4. **错误处理**: 402=充值，403=添加权限，404=端点错误

### 自定义爬虫注意

1. **请求频率**: 建议间隔 1-2 秒，避免触发反爬
2. **User-Agent**: 使用真实浏览器 UA，定期更换
3. **错误重试**: 实现指数退避重试机制
4. **数据校验**: 验证返回数据结构，处理空值和异常
5. **日志记录**: 记录请求失败原因，便于排查问题

### 性能优化

1. **并发请求**: 使用 `asyncio` 或线程池并发获取多个平台
2. **本地缓存**: 对热门数据做短期缓存（如 5-10 分钟）
3. **增量更新**: 只拉取新增数据，避免重复处理

---

## 文件参考

| 文件 | 说明 |
|------|------|
| `src/data_sources/base.py` | 基类定义 |
| `src/data_sources/tikhub_adapter.py` | TikHub 适配器实现 |
| `src/data_sources/newsnow_adapter.py` | NewsNow 适配器实现 |
| `src/data_sources/unified_fetcher.py` | 统一数据获取器 |
| `config/industries.yaml` | 数据源配置 |
| `.env.example` | 环境变量模板 |
