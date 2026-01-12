"""Unified data fetcher for creativity pipeline.

Combines multiple data source adapters (NewsNow, TikHub, Custom)
into a single unified interface.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import yaml

from .base import (
    BaseDataSourceAdapter,
    RawNewsItem,
    DataSourceRegistry,
    SourceType,
    ContentType,
)
from .newsnow_adapter import NewsNowAdapter
from .tikhub_adapter import TikHubAdapter
from .mock_data import get_mock_data, is_mock_mode

logger = logging.getLogger(__name__)


class UnifiedDataFetcher:
    """Unified data fetcher that combines all data sources.

    Reads configuration from industries.yaml and fetches from
    appropriate adapters based on provider settings.
    """

    def __init__(self, config_path: str = None):
        """Initialize the unified fetcher.

        Args:
            config_path: Path to industries.yaml. Auto-detected if not provided.
        """
        self.config_path = config_path or self._find_config()
        self.config = self._load_config()
        self.adapters: Dict[str, BaseDataSourceAdapter] = {}

        self._init_adapters()

    def _find_config(self) -> str:
        """Find the industries.yaml config file."""
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "industries.yaml",
            Path("config/industries.yaml"),
            Path("../config/industries.yaml"),
        ]

        for path in possible_paths:
            if path.exists():
                return str(path)

        raise FileNotFoundError("industries.yaml not found")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _init_adapters(self) -> None:
        """Initialize enabled data source adapters."""
        providers = self.config.get("providers", {})

        # NewsNow adapter
        if providers.get("newsnow", {}).get("enabled", True):
            self.adapters["newsnow"] = NewsNowAdapter()
            logger.info("NewsNow adapter initialized")

        # TikHub adapter
        tikhub_config = providers.get("tikhub", {})
        if tikhub_config.get("enabled", False):
            api_key = os.environ.get("TIKHUB_API_KEY", "")
            if api_key:
                self.adapters["tikhub"] = TikHubAdapter(api_key=api_key)
                logger.info("TikHub adapter initialized")
            else:
                logger.warning("TikHub enabled but TIKHUB_API_KEY not set")

        # Custom adapter placeholder (方案C)
        if providers.get("custom", {}).get("enabled", False):
            logger.info("Custom adapter placeholder (not implemented)")

    def get_sources_by_industry(self, industry: str) -> List[Dict[str, Any]]:
        """Get source configurations for an industry.

        Args:
            industry: Industry key (e.g., "tech/ai").

        Returns:
            List of source configurations.
        """
        industries = self.config.get("industries", {})
        industry_config = industries.get(industry, {})
        return industry_config.get("sources", [])

    def get_all_sources(self) -> List[Dict[str, Any]]:
        """Get all configured sources across all industries."""
        all_sources = []
        industries = self.config.get("industries", {})

        for industry_key, industry_config in industries.items():
            for source in industry_config.get("sources", []):
                source["industry"] = industry_key
                all_sources.append(source)

        return all_sources

    def fetch_source(self, source_id: str, limit: int = 20) -> List[RawNewsItem]:
        """Fetch from a specific source.

        Args:
            source_id: Source identifier (e.g., "twitter", "zhihu").
            limit: Maximum items to fetch.

        Returns:
            List of RawNewsItem objects.
        """
        # Check for mock mode - return mock data instead of calling APIs
        if is_mock_mode():
            mock_items = get_mock_data(source_id, limit)
            if mock_items:
                logger.info(f"[MOCK] Returning {len(mock_items)} mock items for {source_id}")
                return mock_items
            # Fall through to try actual fetch if no mock data available

        # Find source config
        source_config = None
        for source in self.get_all_sources():
            if source.get("id") == source_id:
                source_config = source
                break

        if not source_config:
            logger.warning(f"Source not found: {source_id}")
            return []

        provider = source_config.get("provider", "newsnow")
        adapter = self.adapters.get(provider)

        if not adapter:
            logger.warning(f"Adapter not available for provider: {provider}")
            return []

        try:
            return adapter.fetch_platform(source_id, limit)
        except Exception as e:
            logger.error(f"Error fetching from {source_id}: {e}")
            return []

    def fetch_industry(self, industry: str, limit_per_source: int = 20) -> Dict[str, List[RawNewsItem]]:
        """Fetch all sources for an industry.

        Args:
            industry: Industry key.
            limit_per_source: Maximum items per source.

        Returns:
            Dictionary mapping source_id to list of items.
        """
        results = {}
        sources = self.get_sources_by_industry(industry)

        for source in sources:
            source_id = source.get("id")
            items = self.fetch_source(source_id, limit_per_source)
            if items:
                results[source_id] = items
                logger.info(f"Fetched {len(items)} items from {source_id}")

        return results

    def fetch_all(self, limit_per_source: int = 20) -> Dict[str, Dict[str, List[RawNewsItem]]]:
        """Fetch from all sources across all industries.

        Returns:
            Nested dictionary: industry -> source_id -> items
        """
        results = {}
        industries = self.config.get("industries", {})

        for industry_key in industries.keys():
            results[industry_key] = self.fetch_industry(industry_key, limit_per_source)

        return results

    def fetch_pain_points(self, limit: int = 50) -> List[RawNewsItem]:
        """Fetch from sources marked as high pain_point_value.

        These are sources where users frequently complain/discuss problems.

        Args:
            limit: Maximum total items.

        Returns:
            List of items sorted by heat score.
        """
        pain_point_sources = []

        for source in self.get_all_sources():
            if source.get("pain_point_value") == "high":
                pain_point_sources.append(source.get("id"))

        all_items = []
        per_source = max(10, limit // len(pain_point_sources)) if pain_point_sources else limit

        for source_id in pain_point_sources:
            items = self.fetch_source(source_id, per_source)
            all_items.extend(items)

        # Sort by heat score and return top items
        all_items.sort(key=lambda x: -x.heat_score)
        return all_items[:limit]

    def get_cross_platform_topics(self, min_platforms: int = 2) -> List[Dict[str, Any]]:
        """Find topics that appear across multiple platforms.

        Args:
            min_platforms: Minimum number of platforms for inclusion.

        Returns:
            List of cross-platform topic aggregations.
        """
        all_results = self.fetch_all(limit_per_source=30)

        # Flatten all items
        all_items = []
        for industry, sources in all_results.items():
            for source_id, items in sources.items():
                all_items.extend(items)

        # Group by normalized title
        from collections import defaultdict
        import re

        title_groups = defaultdict(list)

        for item in all_items:
            # Normalize title
            normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', item.title.lower())[:50]
            if normalized:
                title_groups[normalized].append(item)

        # Filter to cross-platform
        cross_platform = []
        for normalized, items in title_groups.items():
            platforms = set(item.source_platform for item in items)
            if len(platforms) >= min_platforms:
                best_item = max(items, key=lambda x: x.heat_score)
                cross_platform.append({
                    "title": best_item.title,
                    "platforms": list(platforms),
                    "platform_count": len(platforms),
                    "total_heat": sum(item.heat_score for item in items),
                    "best_url": best_item.url,
                    "items": [item.to_dict() for item in items],
                })

        cross_platform.sort(key=lambda x: (-x["platform_count"], -x["total_heat"]))
        return cross_platform


# ==================== Convenience Functions ====================

_fetcher_instance: Optional[UnifiedDataFetcher] = None


def get_unified_fetcher() -> UnifiedDataFetcher:
    """Get the global UnifiedDataFetcher instance."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = UnifiedDataFetcher()
    return _fetcher_instance


async def fetch_all_sources(
    industries: List[str] = None,
    include_pain_points: bool = True,
) -> List[Dict[str, Any]]:
    """Async wrapper for fetching all sources.

    Args:
        industries: Industries to fetch. Defaults to all.
        include_pain_points: Prioritize pain point sources.

    Returns:
        List of raw news items as dictionaries.
    """
    fetcher = get_unified_fetcher()

    if include_pain_points:
        items = fetcher.fetch_pain_points(limit=50)
    else:
        all_results = fetcher.fetch_all(limit_per_source=20)
        items = []
        for industry, sources in all_results.items():
            if industries and industry not in industries:
                continue
            for source_id, source_items in sources.items():
                items.extend(source_items)

    return [item.to_dict() for item in items]


def get_top_items(
    limit: int = 50,
    industries: List[str] = None,
    pain_points_only: bool = False,
) -> List[Dict[str, Any]]:
    """Get top news items for creativity pipeline input.

    Args:
        limit: Maximum number of items.
        industries: Industries to include.
        pain_points_only: Only from pain point sources.

    Returns:
        List of top items as dictionaries.
    """
    fetcher = get_unified_fetcher()

    if pain_points_only:
        items = fetcher.fetch_pain_points(limit=limit)
    else:
        all_results = fetcher.fetch_all(limit_per_source=20)
        items = []
        for industry, sources in all_results.items():
            if industries and industry not in industries:
                continue
            for source_id, source_items in sources.items():
                items.extend(source_items)

        items.sort(key=lambda x: -x.heat_score)
        items = items[:limit]

    return [item.to_dict() for item in items]
