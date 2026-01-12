"""TikHub API adapter for creativity pipeline.

Provides access to Twitter, Reddit, Xiaohongshu and other platforms
via the TikHub unified API.

API Documentation: https://api.tikhub.io/
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

from .base import (
    BaseDataSourceAdapter,
    RawNewsItem,
    SourceType,
    ContentType,
)

logger = logging.getLogger(__name__)


class TikHubAdapter(BaseDataSourceAdapter):
    """TikHub API adapter for Twitter, Reddit, Xiaohongshu.

    TikHub provides a unified API for accessing multiple social platforms.
    Requires API key from https://api.tikhub.io/

    Supported platforms:
    - Twitter/X: Trending topics, user tweets
    - Reddit: Hot posts from subreddits
    - Xiaohongshu (小红书): Trending notes, search results
    - Weibo: Hot search, trending topics
    """

    source_type = SourceType.TIKHUB
    API_BASE = "https://api.tikhub.io"

    # Platform configurations (from TikHub OpenAPI spec)
    # API Docs: https://api.tikhub.io/ and https://docs.tikhub.io/
    PLATFORM_CONFIG = {
        "twitter": {
            "name": "Twitter/X",
            "endpoints": {
                # From OpenAPI spec
                "trending": "/api/v1/twitter/web/fetch_trending",
                "search": "/api/v1/twitter/web/fetch_search_timeline",
            },
            "content_type": ContentType.TRENDING,
            "weight": 1.3,
        },
        "reddit": {
            "name": "Reddit",
            "endpoints": {
                # From OpenAPI spec - use app endpoints
                "popular": "/api/v1/reddit/app/fetch_popular_feed",
                "home": "/api/v1/reddit/app/fetch_home_feed",
                "trending_searches": "/api/v1/reddit/app/fetch_trending_searches",
                "search": "/api/v1/reddit/app/fetch_dynamic_search",
            },
            "content_type": ContentType.DISCUSSION,
            "weight": 1.2,
            "default_subreddits": ["technology", "startups", "programming", "webdev"],
        },
        "xiaohongshu": {
            "name": "小红书",
            "endpoints": {
                # From OpenAPI spec
                "hot_list": "/api/v1/xiaohongshu/web_v2/fetch_hot_list",
                "home_notes": "/api/v1/xiaohongshu/web_v2/fetch_home_notes",
                "search": "/api/v1/xiaohongshu/web/search_notes",
                "search_v3": "/api/v1/xiaohongshu/web/search_notes_v3",
                "search_v2": "/api/v1/xiaohongshu/web_v2/fetch_search_notes",
            },
            "content_type": ContentType.USER_POST,
            "weight": 1.4,
        },
        "weibo": {
            "name": "微博",
            "endpoints": {
                # From OpenAPI spec
                "hot_search": "/api/v1/weibo/web/fetch_hot_search",
                "hot_search_v2": "/api/v1/weibo/web_v2/fetch_hot_search",
                "trend_top": "/api/v1/weibo/web/fetch_trend_top",
                "hot_ranking": "/api/v1/weibo/web_v2/fetch_hot_ranking_timeline",
                "realtime_search": "/api/v1/weibo/web_v2/fetch_realtime_search",
            },
            "content_type": ContentType.HOT_SEARCH,
            "weight": 1.5,
        },
    }

    def __init__(self, api_key: str = None, config: Dict[str, Any] = None):
        """Initialize TikHub adapter.

        Args:
            api_key: TikHub API key. Falls back to TIKHUB_API_KEY env var.
            config: Additional configuration.
        """
        super().__init__(config)
        self.api_key = api_key or os.environ.get("TIKHUB_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CreativityPipeline/1.0",
        })

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.5  # seconds

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Optional[Dict]:
        """Make API request.

        Args:
            endpoint: API endpoint path.
            params: Query parameters.
            method: HTTP method (GET or POST).

        Returns:
            JSON response or None on error.
        """
        if not self.api_key:
            logger.warning("TikHub API key not configured")
            return None

        self._rate_limit()

        url = f"{self.API_BASE}{endpoint}"
        try:
            if method.upper() == "POST":
                response = self.session.post(url, json=params, timeout=30)
            else:
                response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            logger.debug(f"TikHub API success: {endpoint}")
            return result
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            logger.warning(f"TikHub API HTTP {status_code} for {endpoint}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"TikHub API request error for {endpoint}: {e}")
            return None

    def _try_endpoints(self, endpoints: List[str], params: Dict = None) -> Optional[Dict]:
        """Try multiple endpoints until one succeeds.

        Args:
            endpoints: List of endpoint paths to try.
            params: Query parameters.

        Returns:
            JSON response from first successful endpoint, or None.
        """
        for endpoint in endpoints:
            result = self._request(endpoint, params)
            if result and (result.get("data") or result.get("code") == 200):
                return result
        return None

    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platforms."""
        return list(self.PLATFORM_CONFIG.keys())

    def fetch_platform(self, platform: str, limit: int = 20) -> List[RawNewsItem]:
        """Fetch news from a specific platform.

        Args:
            platform: Platform identifier.
            limit: Maximum items to fetch.

        Returns:
            List of RawNewsItem objects.
        """
        if platform not in self.PLATFORM_CONFIG:
            logger.warning(f"Unsupported platform: {platform}")
            return []

        config = self.PLATFORM_CONFIG[platform]

        if platform == "twitter":
            return self._fetch_twitter(limit)
        elif platform == "reddit":
            return self._fetch_reddit(limit)
        elif platform == "xiaohongshu":
            return self._fetch_xiaohongshu(limit)
        elif platform == "weibo":
            return self._fetch_weibo(limit)

        return []

    # ==================== Twitter ====================

    def _fetch_twitter(self, limit: int = 20) -> List[RawNewsItem]:
        """Fetch Twitter trending topics."""
        config = self.PLATFORM_CONFIG["twitter"]
        endpoint = config["endpoints"]["trending"]

        data = self._request(endpoint)
        if not data or "data" not in data:
            return []

        # TikHub returns data.trends (list)
        raw_data = data.get("data", {})
        trends = []
        if isinstance(raw_data, dict):
            trends = raw_data.get("trends", []) or raw_data.get("items", [])
        elif isinstance(raw_data, list):
            trends = raw_data

        items = []
        for rank, trend in enumerate(trends[:limit], 1):
            name = trend.get("name", "") or trend.get("title", "")
            item = RawNewsItem(
                title=name,
                url=trend.get("url", f"https://twitter.com/search?q={name}"),
                source_platform="twitter",
                source_type=SourceType.TIKHUB,
                content_type=ContentType.TRENDING,
                content=trend.get("description", ""),
                rank=rank,
                engagement={
                    "tweet_count": trend.get("tweet_volume", 0) or 0,
                },
                tags=trend.get("hashtags", []),
                raw_data=trend,
            )
            item.heat_score = self.calculate_heat_score(item)
            items.append(item)

        logger.info(f"Fetched {len(items)} Twitter trends")
        return items

    # ==================== Reddit ====================

    def _fetch_reddit(self, limit: int = 20) -> List[RawNewsItem]:
        """Fetch Reddit popular/trending posts."""
        config = self.PLATFORM_CONFIG["reddit"]

        # Try multiple endpoints in order of preference
        endpoints_to_try = [
            config["endpoints"]["popular"],
            config["endpoints"]["home"],
            config["endpoints"]["trending_searches"],
        ]

        data = self._try_endpoints(endpoints_to_try)
        if not data:
            logger.warning("Reddit endpoints failed")
            return []

        items = []
        # Handle different response structures (TikHub Reddit returns popularfeed.postsInfoByIds)
        raw_data = data.get("data", {})
        posts = []
        if isinstance(raw_data, dict):
            # TikHub format: data.popularfeed.postsInfoByIds
            popularfeed = raw_data.get("popularfeed", {})
            posts = (
                popularfeed.get("postsInfoByIds", []) or
                raw_data.get("children", []) or
                raw_data.get("items", []) or
                raw_data.get("posts", []) or
                raw_data.get("list", [])
            )
        elif isinstance(raw_data, list):
            posts = raw_data

        for rank, post in enumerate(posts[:limit], 1):
            # Handle nested post data (TikHub format has data at top level)
            post_data = post.get("data", post) if isinstance(post, dict) else {}

            # TikHub format: postTitle is at top level, subreddit is nested object
            title = (
                post.get("postTitle", "") or
                post_data.get("postTitle", "") or
                post_data.get("title", "") or
                post.get("title", "") or
                post_data.get("name", "") or
                post_data.get("display_text", "")
            )

            # Handle permalink/url
            permalink = (
                post_data.get("permalink", "") or
                post.get("permalink", "") or
                post_data.get("url", "") or
                post.get("url", "")
            )
            if permalink.startswith("/"):
                url = f"https://reddit.com{permalink}"
            elif permalink.startswith("http"):
                url = permalink
            else:
                post_id = post.get("id", "")
                url = f"https://reddit.com/comments/{post_id}" if post_id else ""

            # Get subreddit name (TikHub has nested subreddit object)
            subreddit = post_data.get("subreddit", "")
            if isinstance(subreddit, dict):
                subreddit = subreddit.get("name", "") or subreddit.get("prefixedName", "").replace("r/", "")
            elif not subreddit:
                subreddit = post.get("subreddit", {})
                if isinstance(subreddit, dict):
                    subreddit = subreddit.get("name", "")

            # Get engagement metrics
            upvotes = post_data.get("ups", 0) or post.get("score", 0) or post.get("upvoteCount", 0)
            comments = post_data.get("num_comments", 0) or post.get("commentCount", 0)

            item = RawNewsItem(
                title=title,
                url=url,
                source_platform="reddit",
                source_type=SourceType.TIKHUB,
                content_type=ContentType.DISCUSSION,
                content=(post_data.get("selftext", "") or post.get("body", "") or "")[:500],
                author=post_data.get("author", "") or post.get("authorInfo", {}).get("name", ""),
                rank=rank,
                engagement={
                    "upvotes": upvotes,
                    "comments": comments,
                    "awards": post_data.get("total_awards_received", 0) or post.get("awardCount", 0),
                },
                tags=[subreddit] if subreddit else [],
                raw_data=post,
            )
            item.heat_score = self._calculate_reddit_score(item)
            items.append(item)

        # Sort by heat score and limit
        items.sort(key=lambda x: -x.heat_score)
        logger.info(f"Fetched {len(items[:limit])} Reddit posts")
        return items[:limit]

    def _calculate_reddit_score(self, item: RawNewsItem) -> int:
        """Calculate Reddit-specific heat score."""
        engagement = item.engagement
        upvotes = engagement.get("upvotes", 0)
        comments = engagement.get("comments", 0)
        awards = engagement.get("awards", 0)

        # Reddit score formula
        score = upvotes * 1 + comments * 3 + awards * 10
        return min(10000, int(score / 10))

    # ==================== Xiaohongshu ====================

    def _fetch_xiaohongshu(self, limit: int = 20) -> List[RawNewsItem]:
        """Fetch Xiaohongshu hot list (confirmed endpoint)."""
        config = self.PLATFORM_CONFIG["xiaohongshu"]

        # Try multiple endpoints in order of preference
        endpoints_to_try = [
            config["endpoints"]["hot_list"],  # Confirmed from OpenAPI spec
            config["endpoints"]["home_notes"],
            config["endpoints"]["search"],
        ]

        data = self._try_endpoints(endpoints_to_try)
        if not data:
            logger.warning("Xiaohongshu hot list endpoints failed")
            return []

        items = []
        # Handle different response structures
        # TikHub xiaohongshu returns: data.data.items (nested data)
        raw_data = data.get("data", {})
        if isinstance(raw_data, dict):
            inner_data = raw_data.get("data", raw_data)
            if isinstance(inner_data, dict):
                hot_list = inner_data.get("items", []) or inner_data.get("list", [])
            else:
                hot_list = inner_data if isinstance(inner_data, list) else []
        else:
            hot_list = raw_data if isinstance(raw_data, list) else []

        for rank, note in enumerate(hot_list[:limit], 1):
            # Extract note data from various response formats
            title = (
                note.get("title", "") or
                note.get("display_name", "") or
                note.get("name", "") or
                note.get("desc", "")[:100]
            )
            note_url = (
                note.get("note_url", "") or
                note.get("url", "") or
                f"https://www.xiaohongshu.com/explore/{note.get('id', '')}"
            )

            item = RawNewsItem(
                title=title,
                url=note_url,
                source_platform="xiaohongshu",
                source_type=SourceType.TIKHUB,
                content_type=ContentType.USER_POST,
                content=note.get("desc", "")[:500],
                author=note.get("user", {}).get("nickname", "") if isinstance(note.get("user"), dict) else "",
                rank=rank,
                engagement={
                    "likes": note.get("liked_count", 0) or note.get("likes", 0),
                    "comments": note.get("comment_count", 0) or note.get("comments", 0),
                    "collects": note.get("collected_count", 0) or note.get("collects", 0),
                    "hot_value": note.get("hot_value", 0) or note.get("score", 0),
                },
                tags=note.get("tag_list", []) or note.get("tags", []),
                raw_data=note,
            )
            item.heat_score = self._calculate_xiaohongshu_score(item)
            items.append(item)

        logger.info(f"Fetched {len(items)} Xiaohongshu items")
        return items

    def _fetch_xiaohongshu_search(self, limit: int = 20) -> List[RawNewsItem]:
        """Fetch Xiaohongshu notes by search (fallback)."""
        config = self.PLATFORM_CONFIG["xiaohongshu"]
        endpoint = config["endpoints"]["search"]

        # Search keywords for pain points and complaints
        keywords = ["吐槽", "踩坑", "避雷", "求推荐", "怎么办"]
        all_items = []

        for keyword in keywords[:2]:  # Limit to avoid rate limiting
            data = self._request(endpoint, {"keyword": keyword, "limit": 10})
            if not data or "data" not in data:
                continue

            for rank, note in enumerate(data.get("data", {}).get("items", [])[:10], 1):
                note_data = note.get("note_card", {})
                item = RawNewsItem(
                    title=note_data.get("title", "") or note_data.get("desc", "")[:100],
                    url=note_data.get("note_url", ""),
                    source_platform="xiaohongshu",
                    source_type=SourceType.TIKHUB,
                    content_type=ContentType.USER_POST,
                    content=note_data.get("desc", "")[:500],
                    author=note_data.get("user", {}).get("nickname", ""),
                    rank=rank,
                    engagement={
                        "likes": note_data.get("liked_count", 0),
                        "comments": note_data.get("comment_count", 0),
                    },
                    tags=[keyword],
                    raw_data=note_data,
                )
                item.heat_score = self._calculate_xiaohongshu_score(item)
                all_items.append(item)

        all_items.sort(key=lambda x: -x.heat_score)
        return all_items[:limit]

    def _calculate_xiaohongshu_score(self, item: RawNewsItem) -> int:
        """Calculate Xiaohongshu-specific heat score."""
        engagement = item.engagement
        likes = engagement.get("likes", 0)
        comments = engagement.get("comments", 0)
        collects = engagement.get("collects", 0)

        # Xiaohongshu score: collects are very valuable
        score = likes * 1 + comments * 3 + collects * 5
        return min(10000, int(score / 5))

    # ==================== Weibo (Enhanced) ====================

    def _fetch_weibo(self, limit: int = 20) -> List[RawNewsItem]:
        """Fetch Weibo hot search via TikHub (as alternative to NewsNow)."""
        config = self.PLATFORM_CONFIG["weibo"]

        # Try multiple endpoints (from OpenAPI spec)
        endpoints_to_try = [
            config["endpoints"]["hot_search_v2"],  # web_v2 API
            config["endpoints"]["hot_search"],     # web API
            config["endpoints"]["trend_top"],      # trend top
            config["endpoints"]["hot_ranking"],    # hot ranking timeline
        ]

        data = self._try_endpoints(endpoints_to_try)
        if not data:
            logger.warning("Weibo hot search endpoints failed")
            return []

        items = []
        # Handle different response structures
        hot_list = data.get("data", [])
        if isinstance(hot_list, dict):
            hot_list = hot_list.get("realtime", []) or hot_list.get("list", []) or hot_list.get("items", [])

        for rank, topic in enumerate(hot_list[:limit], 1):
            title = (
                topic.get("word", "") or
                topic.get("note", "") or
                topic.get("name", "") or
                topic.get("title", "")
            )
            url = (
                topic.get("url", "") or
                topic.get("scheme", "") or
                f"https://s.weibo.com/weibo?q={title}"
            )

            item = RawNewsItem(
                title=title,
                url=url,
                source_platform="weibo",
                source_type=SourceType.TIKHUB,
                content_type=ContentType.HOT_SEARCH,
                rank=rank,
                engagement={
                    "hot_value": topic.get("num", 0) or topic.get("raw_hot", 0) or topic.get("hot", 0),
                },
                tags=[topic.get("category", "")] if topic.get("category") else [],
                raw_data=topic,
            )
            item.heat_score = self._calculate_weibo_score(item, rank)
            items.append(item)

        logger.info(f"Fetched {len(items)} Weibo hot topics")
        return items

    def _calculate_weibo_score(self, item: RawNewsItem, rank: int) -> int:
        """Calculate Weibo-specific heat score."""
        hot_value = item.engagement.get("hot_value", 0)

        # Weibo: high rank + hot value
        rank_score = max(0, 100 - (rank - 1) * 3)
        hot_score = min(100, hot_value / 100000) if hot_value else 50

        return int((rank_score * 0.4 + hot_score * 0.6) * 100)


    # ==================== Diagnostics ====================

    def test_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """Test all configured endpoints and report status.

        Returns:
            Dictionary mapping platform -> endpoint -> status info.
        """
        results = {}

        for platform, config in self.PLATFORM_CONFIG.items():
            results[platform] = {}
            for endpoint_name, endpoint_path in config.get("endpoints", {}).items():
                status = {"path": endpoint_path, "success": False, "error": None, "data_count": 0}

                try:
                    data = self._request(endpoint_path)
                    if data:
                        status["success"] = True
                        status["code"] = data.get("code")
                        # Count data items
                        data_content = data.get("data", [])
                        if isinstance(data_content, list):
                            status["data_count"] = len(data_content)
                        elif isinstance(data_content, dict):
                            for key in ["items", "list", "children", "realtime"]:
                                if key in data_content:
                                    status["data_count"] = len(data_content[key])
                                    break
                except Exception as e:
                    status["error"] = str(e)

                results[platform][endpoint_name] = status
                logger.info(f"  {platform}/{endpoint_name}: {'OK' if status['success'] else 'FAIL'} ({status.get('data_count', 0)} items)")

        return results


# ==================== Factory Function ====================

def create_tikhub_adapter(api_key: str = None) -> TikHubAdapter:
    """Create a TikHub adapter instance.

    Args:
        api_key: Optional API key. Uses TIKHUB_API_KEY env var if not provided.

    Returns:
        Configured TikHubAdapter instance.
    """
    return TikHubAdapter(api_key=api_key)
