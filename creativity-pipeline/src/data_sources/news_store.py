"""News data local storage service.

Saves fetched news to local JSON files with enriched metadata,
enabling Agent-driven analysis with full context.
"""
import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .news_ranker import NewsRanker

logger = logging.getLogger(__name__)


class NewsStore:
    """Local storage service for news data.

    Responsibilities:
    1. Save raw fetched data with enriched metadata
    2. Detect cross-platform topics
    3. Calculate statistics
    4. Provide query interface for Agent access

    Directory structure:
        vault/
        └── raw_data/
            ├── 2026-01-12/
            │   ├── morning_fetch.json
            │   ├── afternoon_fetch.json
            │   └── evening_fetch.json
            └── latest.json
    """

    def __init__(self, vault_path: str = "./vault"):
        """Initialize the news store.

        Args:
            vault_path: Path to the vault directory.
        """
        self.vault_path = Path(vault_path)
        self.raw_data_path = self.vault_path / "raw_data"
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        self.ranker = NewsRanker()

    def save_fetch_result(
        self,
        items: List[Dict[str, Any]],
        time_slot: str = "morning"
    ) -> Path:
        """Save fetch result to local storage.

        Enriches data with:
        - Unique IDs
        - Cross-platform detection
        - Statistics

        Args:
            items: List of news items from fetcher.
            time_slot: morning|afternoon|evening

        Returns:
            Path to the saved file.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        day_path = self.raw_data_path / today
        day_path.mkdir(exist_ok=True)

        # Enrich items with metadata
        enriched_items = self._enrich_items(items, today)

        # Calculate statistics
        statistics = self._calculate_statistics(enriched_items)

        # Build complete data structure
        data = {
            "fetch_time": datetime.now().isoformat(),
            "fetch_date": today,
            "time_slot": time_slot,
            "total_items": len(enriched_items),
            "statistics": statistics,
            "items": enriched_items,
        }

        # Save to date directory
        file_path = day_path / f"{time_slot}_fetch.json"
        self._write_json(file_path, data)

        # Update latest.json symlink/copy
        latest_path = self.raw_data_path / "latest.json"
        self._write_json(latest_path, data)

        logger.info(f"Saved {len(items)} items to {file_path}")
        return file_path

    def _enrich_items(
        self,
        items: List[Dict[str, Any]],
        date: str
    ) -> List[Dict[str, Any]]:
        """Enrich news items with metadata.

        Adds:
        - Unique ID
        - Cross-platform detection
        - Normalized fields

        Args:
            items: Raw news items.
            date: Date string (YYYY-MM-DD).

        Returns:
            Enriched news items.
        """
        # Group by normalized title for cross-platform detection
        title_map = defaultdict(list)
        for i, item in enumerate(items):
            normalized = self._normalize_title(item.get('title', ''))
            if normalized:
                title_map[normalized].append((i, item))

        # Build enriched items
        enriched = []
        for i, item in enumerate(items):
            normalized = self._normalize_title(item.get('title', ''))
            related = title_map.get(normalized, [])

            # Get all platforms for this topic
            platforms = list(set(
                r[1].get('source_platform', '') or r[1].get('source', '')
                for r in related
            ))

            cross_platform_info = {
                "is_trending": len(platforms) > 1,
                "platforms": platforms,
                "total_mentions": len(related),
            }

            enriched_item = {
                # Core fields
                "id": f"news-{date}-{i+1:03d}",
                "title": item.get('title', ''),
                "url": item.get('url', ''),
                "mobile_url": item.get('mobile_url', ''),

                # Source info
                "source_platform": item.get('source_platform', '') or item.get('source', ''),
                "source_name": item.get('source_name', '') or item.get('source', ''),
                "industry": item.get('industry', 'unknown'),

                # Ranking
                "rank": item.get('rank', 0),
                "heat_score": item.get('heat_score', 0) or item.get('heat', 0),

                # Summary (may be empty, Agent can fetch on demand)
                "summary": item.get('summary', ''),

                # Cross-platform info
                "cross_platform": cross_platform_info,

                # Original data preserved
                "_original": item,
            }

            # Add priority score using NewsRanker
            score = self.ranker.score_item(enriched_item, cross_platform_info)
            enriched_item["priority"] = score.to_dict()

            enriched.append(enriched_item)

        return enriched

    def _normalize_title(self, title: str) -> str:
        """Normalize title for cross-platform matching.

        Removes punctuation and whitespace, keeps Chinese and alphanumeric.

        Args:
            title: Raw title string.

        Returns:
            Normalized title (first 30 chars).
        """
        if not title:
            return ''
        normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', title.lower())
        return normalized[:30]

    def _calculate_statistics(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from enriched items.

        Args:
            items: Enriched news items.

        Returns:
            Statistics dictionary.
        """
        from collections import Counter

        industries = Counter(item.get('industry', 'unknown') for item in items)
        sources = Counter(item.get('source_platform', 'unknown') for item in items)

        cross_platform_count = sum(
            1 for item in items
            if item.get('cross_platform', {}).get('is_trending', False)
        )

        # Find top heat items
        sorted_by_heat = sorted(items, key=lambda x: -x.get('heat_score', 0))
        top_items = [
            {"title": item['title'][:50], "heat_score": item['heat_score'], "source": item['source_platform']}
            for item in sorted_by_heat[:10]
        ]

        # Find cross-platform topics
        cross_platform_topics = [
            {
                "title": item['title'][:50],
                "platforms": item['cross_platform']['platforms'],
                "mentions": item['cross_platform']['total_mentions'],
            }
            for item in items
            if item.get('cross_platform', {}).get('is_trending', False)
        ]
        # Deduplicate by title
        seen_titles = set()
        unique_cross_platform = []
        for topic in cross_platform_topics:
            if topic['title'] not in seen_titles:
                seen_titles.add(topic['title'])
                unique_cross_platform.append(topic)

        # Priority distribution
        priority_stats = self.ranker.get_statistics(items)

        return {
            "by_industry": dict(industries),
            "by_source": dict(sources),
            "cross_platform_count": cross_platform_count,
            "cross_platform_topics": unique_cross_platform[:10],
            "top_items": top_items,
            "total_heat": sum(item.get('heat_score', 0) for item in items),
            # Priority-based statistics
            "by_priority": priority_stats.get("by_priority", {}),
            "priority_top_items": priority_stats.get("top_items", []),
        }

    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Write data to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== Query Methods ====================

    def load_latest(self) -> Optional[Dict[str, Any]]:
        """Load the latest fetch result.

        Returns:
            Latest data or None if not found.
        """
        latest_path = self.raw_data_path / "latest.json"
        return self._load_json(latest_path)

    def load_by_date(
        self,
        date: str,
        time_slot: str = "morning"
    ) -> Optional[Dict[str, Any]]:
        """Load fetch result by date and time slot.

        Args:
            date: Date string (YYYY-MM-DD).
            time_slot: morning|afternoon|evening

        Returns:
            Data or None if not found.
        """
        file_path = self.raw_data_path / date / f"{time_slot}_fetch.json"
        return self._load_json(file_path)

    def load_today(self, time_slot: str = "morning") -> Optional[Dict[str, Any]]:
        """Load today's fetch result.

        Args:
            time_slot: morning|afternoon|evening

        Returns:
            Data or None if not found.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.load_by_date(today, time_slot)

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON file."""
        if not path.exists():
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading {path}: {e}")
            return None

    def list_dates(self) -> List[str]:
        """List all dates with saved data.

        Returns:
            List of date strings, sorted descending.
        """
        dates = []
        for path in self.raw_data_path.iterdir():
            if path.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', path.name):
                dates.append(path.name)
        return sorted(dates, reverse=True)

    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific item by ID.

        Args:
            item_id: News item ID (e.g., "news-2026-01-12-001").

        Returns:
            Item data or None.
        """
        # Extract date from ID
        match = re.match(r'news-(\d{4}-\d{2}-\d{2})-\d+', item_id)
        if not match:
            return None

        date = match.group(1)

        # Search in all time slots
        for time_slot in ['morning', 'afternoon', 'evening']:
            data = self.load_by_date(date, time_slot)
            if data:
                for item in data.get('items', []):
                    if item.get('id') == item_id:
                        return item

        return None

    def search_items(
        self,
        query: str,
        date: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search items by title keyword.

        Args:
            query: Search keyword.
            date: Optional date filter.
            limit: Maximum results.

        Returns:
            Matching items.
        """
        if date:
            dates = [date]
        else:
            dates = self.list_dates()[:7]  # Last 7 days

        results = []
        query_lower = query.lower()

        for d in dates:
            for time_slot in ['morning', 'afternoon', 'evening']:
                data = self.load_by_date(d, time_slot)
                if data:
                    for item in data.get('items', []):
                        if query_lower in item.get('title', '').lower():
                            results.append(item)
                            if len(results) >= limit:
                                return results

        return results

    # ==================== Summary Management ====================

    def update_item_summary(
        self,
        item_id: str,
        summary: str,
        source: str = "webfetch"
    ) -> bool:
        """Update an item's summary.

        Called after Agent fetches article content.

        Args:
            item_id: News item ID.
            summary: Summary text.
            source: webfetch|ai_generated|manual

        Returns:
            True if updated successfully.
        """
        match = re.match(r'news-(\d{4}-\d{2}-\d{2})-\d+', item_id)
        if not match:
            return False

        date = match.group(1)

        # Find and update in all time slots
        for time_slot in ['morning', 'afternoon', 'evening']:
            file_path = self.raw_data_path / date / f"{time_slot}_fetch.json"
            data = self._load_json(file_path)

            if data:
                updated = False
                for item in data.get('items', []):
                    if item.get('id') == item_id:
                        item['summary'] = summary
                        item['summary_source'] = source
                        item['summary_updated'] = datetime.now().isoformat()
                        updated = True
                        break

                if updated:
                    self._write_json(file_path, data)

                    # Also update latest.json if it's the same date
                    latest = self.load_latest()
                    if latest and latest.get('fetch_date') == date:
                        for item in latest.get('items', []):
                            if item.get('id') == item_id:
                                item['summary'] = summary
                                item['summary_source'] = source
                                item['summary_updated'] = datetime.now().isoformat()
                                break
                        self._write_json(self.raw_data_path / "latest.json", latest)

                    logger.info(f"Updated summary for {item_id}")
                    return True

        return False
