"""NewsNow data source adapter for creativity pipeline.

Adapts the TrendRadar DataFetcher for use in the creativity pipeline,
fetching news from multiple platforms via the NewsNow API.
"""

import json
import random
import time
import requests
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsItem:
    """Represents a single news item."""
    title: str
    url: str
    mobile_url: str
    source: str
    industry: str
    rank: int
    heat_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "mobile_url": self.mobile_url,
            "source": self.source,
            "industry": self.industry,
            "rank": self.rank,
            "heat_score": self.heat_score,
        }


# Industry to source mapping
INDUSTRY_SOURCES = {
    "tech/ai": [
        ("zhihu", "知乎"),
        ("v2ex", "V2EX"),
        ("36kr", "36氪"),
        ("hackernews", "Hacker News"),
        ("producthunt", "Product Hunt"),
        ("github-trending-today", "GitHub Trending"),
        ("sspai", "少数派"),
    ],
    "finance": [
        ("wallstreetcn-hot", "华尔街见闻"),
        ("cls-hot", "财联社"),
        ("eastmoney", "东方财富"),
        ("xueqiu", "雪球"),
    ],
    "social": [
        ("weibo", "微博"),
        ("douyin", "抖音"),
        ("toutiao", "今日头条"),
        ("baidu", "百度热搜"),
        ("bilibili-hot-search", "B站热搜"),
    ],
}

# All sources flattened
ALL_SOURCES = []
for industry, sources in INDUSTRY_SOURCES.items():
    for source_id, source_name in sources:
        ALL_SOURCES.append((source_id, source_name, industry))


class NewsNowAdapter:
    """Adapter for NewsNow API, based on TrendRadar DataFetcher.

    Fetches trending news from multiple platforms and formats them
    for the creativity pipeline input.
    """

    API_BASE = "https://newsnow.busiyi.world/api/s"

    def __init__(self, proxy_url: Optional[str] = None):
        """Initialize the adapter.

        Args:
            proxy_url: Optional proxy URL for requests.
        """
        self.proxy_url = proxy_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    def fetch_source(
        self,
        source_id: str,
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """Fetch data from a single source.

        Args:
            source_id: NewsNow source identifier.
            max_retries: Maximum retry attempts.
            min_retry_wait: Minimum wait between retries.
            max_retry_wait: Maximum wait between retries.

        Returns:
            Parsed JSON response or None on failure.
        """
        url = f"{self.API_BASE}?id={source_id}&latest"

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    url,
                    proxies=proxies,
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()

                data = response.json()
                status = data.get("status", "unknown")

                if status not in ["success", "cache"]:
                    raise ValueError(f"Response status: {status}")

                return data

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    wait_time = random.uniform(min_retry_wait, max_retry_wait) + (retries - 1)
                    print(f"Fetch {source_id} failed: {e}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Fetch {source_id} failed after {max_retries} retries: {e}")
                    return None

        return None

    def fetch_platform(self, source_id: str, limit: int = 20):
        """Fetch from a specific platform (for unified_fetcher compatibility).

        Args:
            source_id: NewsNow source identifier.
            limit: Maximum items to return.

        Returns:
            List of RawNewsItem-like objects with to_dict() method.
        """
        from .base import RawNewsItem, SourceType, ContentType

        # Find industry for this source
        industry = None
        source_name = source_id
        for ind, sources in INDUSTRY_SOURCES.items():
            for sid, sname in sources:
                if sid == source_id:
                    industry = ind
                    source_name = sname
                    break
            if industry:
                break

        if not industry:
            return []

        data = self.fetch_source(source_id)
        if not data:
            return []

        items = []
        for rank, item in enumerate(data.get("items", [])[:limit], 1):
            news_item = RawNewsItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source_platform=source_id,
                source_type=SourceType.NEWSNOW,
                content_type=ContentType.HOT_SEARCH,
                rank=rank,
                heat_score=self._calculate_heat_score(rank, source_name),
            )
            items.append(news_item)

        return items

    def fetch_industry(
        self,
        industry: str,
        request_interval_ms: int = 100,
    ) -> List[NewsItem]:
        """Fetch all sources for an industry.

        Args:
            industry: Industry key (tech/ai, finance, social).
            request_interval_ms: Milliseconds between requests.

        Returns:
            List of NewsItem objects.
        """
        sources = INDUSTRY_SOURCES.get(industry, [])
        items = []

        for i, (source_id, source_name) in enumerate(sources):
            data = self.fetch_source(source_id)

            if data:
                for rank, item in enumerate(data.get("items", [])[:20], 1):
                    news_item = NewsItem(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        mobile_url=item.get("mobileUrl", ""),
                        source=source_name,
                        industry=industry,
                        rank=rank,
                        heat_score=self._calculate_heat_score(rank, source_name)
                    )
                    items.append(news_item)

            # Rate limiting
            if i < len(sources) - 1:
                actual_interval = request_interval_ms + random.randint(-20, 50)
                actual_interval = max(50, actual_interval)
                time.sleep(actual_interval / 1000)

        return items

    def fetch_all(
        self,
        industries: List[str] = None,
        request_interval_ms: int = 100,
    ) -> Dict[str, List[NewsItem]]:
        """Fetch news from all configured industries.

        Args:
            industries: List of industries to fetch. Defaults to all.
            request_interval_ms: Milliseconds between requests.

        Returns:
            Dictionary mapping industry to list of NewsItems.
        """
        industries = industries or list(INDUSTRY_SOURCES.keys())
        results = {}

        for industry in industries:
            print(f"Fetching {industry} sources...")
            results[industry] = self.fetch_industry(industry, request_interval_ms)
            print(f"  Got {len(results[industry])} items from {industry}")

        return results

    def _calculate_heat_score(self, rank: int, source: str) -> int:
        """Calculate a heat score based on rank and source.

        Args:
            rank: Position in the source's list.
            source: Source name.

        Returns:
            Heat score (0-10000).
        """
        # Base score from rank (higher rank = lower score)
        rank_score = max(0, 100 - (rank - 1) * 5)

        # Source weight multiplier
        source_weights = {
            "微博": 1.5,
            "知乎": 1.3,
            "百度热搜": 1.4,
            "抖音": 1.5,
            "今日头条": 1.2,
            "B站热搜": 1.2,
            "华尔街见闻": 1.1,
            "36氪": 1.1,
        }
        weight = source_weights.get(source, 1.0)

        return int(rank_score * weight * 100)

    def get_cross_platform_items(
        self,
        all_items: Dict[str, List[NewsItem]],
        min_platforms: int = 2,
    ) -> List[Dict[str, Any]]:
        """Find items that appear across multiple platforms.

        Args:
            all_items: Dictionary of items by industry.
            min_platforms: Minimum number of platforms for inclusion.

        Returns:
            List of cross-platform items with aggregated data.
        """
        # Group by similar titles
        title_map: Dict[str, List[NewsItem]] = {}

        for industry, items in all_items.items():
            for item in items:
                # Normalize title for matching
                normalized = self._normalize_title(item.title)
                if normalized not in title_map:
                    title_map[normalized] = []
                title_map[normalized].append(item)

        # Filter to cross-platform items
        cross_platform = []
        for normalized, items in title_map.items():
            sources = set(item.source for item in items)
            if len(sources) >= min_platforms:
                # Aggregate data
                total_heat = sum(item.heat_score for item in items)
                best_item = max(items, key=lambda x: x.heat_score)

                cross_platform.append({
                    "title": best_item.title,
                    "url": best_item.url,
                    "sources": list(sources),
                    "platform_count": len(sources),
                    "total_heat_score": total_heat,
                    "industries": list(set(item.industry for item in items)),
                    "best_rank": min(item.rank for item in items),
                })

        # Sort by platform count and heat score
        cross_platform.sort(key=lambda x: (-x["platform_count"], -x["total_heat_score"]))

        return cross_platform

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison.

        Args:
            title: Raw title string.

        Returns:
            Normalized title.
        """
        # Remove common punctuation and whitespace
        import re
        normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', title.lower())
        return normalized[:50]  # Limit length for matching


async def fetch_all_sources(
    industries: List[str] = None,
    proxy_url: str = None,
) -> List[Dict[str, Any]]:
    """Async wrapper for fetching all sources.

    Args:
        industries: Industries to fetch.
        proxy_url: Optional proxy URL.

    Returns:
        List of raw news items.
    """
    adapter = NewsNowAdapter(proxy_url)
    all_items = adapter.fetch_all(industries)

    # Flatten to list of dicts
    result = []
    for industry, items in all_items.items():
        for item in items:
            result.append(item.to_dict())

    return result


def get_top_items(
    limit: int = 50,
    industries: List[str] = None,
    cross_platform_only: bool = False,
) -> List[Dict[str, Any]]:
    """Get top news items for creativity pipeline input.

    Args:
        limit: Maximum number of items to return.
        industries: Industries to include.
        cross_platform_only: Only return cross-platform items.

    Returns:
        List of top news items.
    """
    adapter = NewsNowAdapter()
    all_items = adapter.fetch_all(industries)

    if cross_platform_only:
        items = adapter.get_cross_platform_items(all_items, min_platforms=2)
    else:
        # Flatten and sort by heat score
        items = []
        for industry, news_items in all_items.items():
            for item in news_items:
                items.append(item.to_dict())

        items.sort(key=lambda x: -x.get("heat_score", 0))

    return items[:limit]
