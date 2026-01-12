"""Data sources module for creativity pipeline.

Provides unified access to multiple data source providers:
- NewsNow: 国内平台热搜 (知乎、微博、V2EX等)
- TikHub: 国际平台 (Twitter、Reddit、小红书)
- Custom: 自定义爬虫 (方案C预留)
- NewsStore: 本地数据存储 (Agent-driven analysis)
"""

# Base classes
from .base import (
    BaseDataSourceAdapter,
    RawNewsItem,
    DataSourceRegistry,
    SourceType,
    ContentType,
)

# Adapters
from .newsnow_adapter import NewsNowAdapter, INDUSTRY_SOURCES
from .tikhub_adapter import TikHubAdapter, create_tikhub_adapter

# Unified fetcher
from .unified_fetcher import (
    UnifiedDataFetcher,
    get_unified_fetcher,
    fetch_all_sources,
    get_top_items,
)

# Local storage
from .news_store import NewsStore
from .news_ranker import NewsRanker

# Mock data for testing
from .mock_data import get_mock_data, is_mock_mode, MOCK_DATA_FUNCTIONS

__all__ = [
    # Base
    "BaseDataSourceAdapter",
    "RawNewsItem",
    "DataSourceRegistry",
    "SourceType",
    "ContentType",
    # Adapters
    "NewsNowAdapter",
    "TikHubAdapter",
    "create_tikhub_adapter",
    "INDUSTRY_SOURCES",
    # Unified
    "UnifiedDataFetcher",
    "get_unified_fetcher",
    "fetch_all_sources",
    "get_top_items",
    # Storage & Ranking
    "NewsStore",
    "NewsRanker",
    # Mock data
    "get_mock_data",
    "is_mock_mode",
    "MOCK_DATA_FUNCTIONS",
]
