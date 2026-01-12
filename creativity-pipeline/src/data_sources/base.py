"""Base classes for data source adapters.

Provides abstract base class and common utilities for implementing
various data source adapters (NewsNow, TikHub, custom crawlers, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class SourceType(str, Enum):
    """Type of data source."""
    NEWSNOW = "newsnow"      # NewsNow API
    TIKHUB = "tikhub"        # TikHub API
    CUSTOM = "custom"        # Custom crawler (方案C)


class ContentType(str, Enum):
    """Type of content from the source."""
    HOT_SEARCH = "hot_search"       # 热搜榜单
    TRENDING = "trending"           # 趋势话题
    USER_POST = "user_post"         # 用户帖子
    COMMENT = "comment"             # 评论/吐槽
    DISCUSSION = "discussion"       # 讨论帖


@dataclass
class RawNewsItem:
    """Raw news item from any data source.

    Unified structure for news items regardless of source.
    """
    title: str
    url: str
    source_platform: str        # e.g., "twitter", "reddit", "xiaohongshu"
    source_type: SourceType     # e.g., TIKHUB, NEWSNOW
    content_type: ContentType   # e.g., HOT_SEARCH, USER_POST

    # Optional fields
    content: str = ""           # Full content if available
    author: str = ""
    publish_time: Optional[datetime] = None
    engagement: Dict[str, int] = field(default_factory=dict)  # likes, comments, shares
    rank: int = 0               # Position in list/trending
    heat_score: int = 0         # Calculated heat score
    tags: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)  # Original API response

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "source_platform": self.source_platform,
            "source_type": self.source_type.value,
            "content_type": self.content_type.value,
            "content": self.content,
            "author": self.author,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "engagement": self.engagement,
            "rank": self.rank,
            "heat_score": self.heat_score,
            "tags": self.tags,
        }


class BaseDataSourceAdapter(ABC):
    """Abstract base class for data source adapters.

    All data source adapters (NewsNow, TikHub, custom) should inherit
    from this class and implement the required methods.
    """

    source_type: SourceType = SourceType.CUSTOM

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the adapter.

        Args:
            config: Configuration dictionary for the adapter.
        """
        self.config = config or {}

    @abstractmethod
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platform IDs.

        Returns:
            List of platform identifiers (e.g., ["twitter", "reddit"])
        """
        pass

    @abstractmethod
    def fetch_platform(self, platform: str, limit: int = 20) -> List[RawNewsItem]:
        """Fetch news from a specific platform.

        Args:
            platform: Platform identifier.
            limit: Maximum number of items to fetch.

        Returns:
            List of RawNewsItem objects.
        """
        pass

    def fetch_all(self, platforms: List[str] = None, limit: int = 20) -> Dict[str, List[RawNewsItem]]:
        """Fetch news from multiple platforms.

        Args:
            platforms: List of platforms to fetch. Defaults to all supported.
            limit: Maximum items per platform.

        Returns:
            Dictionary mapping platform to list of items.
        """
        platforms = platforms or self.get_supported_platforms()
        results = {}

        for platform in platforms:
            if platform in self.get_supported_platforms():
                try:
                    results[platform] = self.fetch_platform(platform, limit)
                except Exception as e:
                    print(f"Error fetching {platform}: {e}")
                    results[platform] = []

        return results

    def calculate_heat_score(self, item: RawNewsItem) -> int:
        """Calculate heat score for an item.

        Override this method for custom scoring logic.

        Args:
            item: The news item.

        Returns:
            Heat score (0-10000).
        """
        # Default scoring based on engagement and rank
        engagement = item.engagement
        likes = engagement.get("likes", 0)
        comments = engagement.get("comments", 0)
        shares = engagement.get("shares", 0)

        # Engagement score (normalized)
        engagement_score = min(100, (likes + comments * 2 + shares * 3) / 100)

        # Rank score (higher rank = lower score)
        rank_score = max(0, 100 - (item.rank - 1) * 5) if item.rank > 0 else 50

        return int((engagement_score * 0.6 + rank_score * 0.4) * 100)


class DataSourceRegistry:
    """Registry for managing multiple data source adapters."""

    _adapters: Dict[str, BaseDataSourceAdapter] = {}
    _platform_to_adapter: Dict[str, str] = {}

    @classmethod
    def register(cls, name: str, adapter: BaseDataSourceAdapter) -> None:
        """Register an adapter.

        Args:
            name: Unique name for the adapter.
            adapter: Adapter instance.
        """
        cls._adapters[name] = adapter

        # Map platforms to adapter
        for platform in adapter.get_supported_platforms():
            cls._platform_to_adapter[platform] = name

    @classmethod
    def get_adapter(cls, name: str) -> Optional[BaseDataSourceAdapter]:
        """Get adapter by name."""
        return cls._adapters.get(name)

    @classmethod
    def get_adapter_for_platform(cls, platform: str) -> Optional[BaseDataSourceAdapter]:
        """Get adapter that supports a specific platform."""
        adapter_name = cls._platform_to_adapter.get(platform)
        if adapter_name:
            return cls._adapters.get(adapter_name)
        return None

    @classmethod
    def fetch_platform(cls, platform: str, limit: int = 20) -> List[RawNewsItem]:
        """Fetch from a platform using the appropriate adapter."""
        adapter = cls.get_adapter_for_platform(platform)
        if adapter:
            return adapter.fetch_platform(platform, limit)
        return []

    @classmethod
    def fetch_all_platforms(cls, limit: int = 20) -> Dict[str, List[RawNewsItem]]:
        """Fetch from all registered platforms."""
        results = {}
        for adapter_name, adapter in cls._adapters.items():
            adapter_results = adapter.fetch_all(limit=limit)
            results.update(adapter_results)
        return results

    @classmethod
    def get_all_platforms(cls) -> List[str]:
        """Get all supported platforms across all adapters."""
        return list(cls._platform_to_adapter.keys())
