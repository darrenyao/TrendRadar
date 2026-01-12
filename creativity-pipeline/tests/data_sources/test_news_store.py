"""Unit tests for NewsStore module."""
import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.data_sources.news_store import NewsStore


class TestNewsStore:
    """Tests for NewsStore class."""

    @pytest.fixture
    def temp_vault(self):
        """Create a temporary vault directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def store(self, temp_vault):
        """Create a NewsStore instance with temp vault."""
        return NewsStore(temp_vault)

    @pytest.fixture
    def sample_items(self):
        """Sample news items for testing."""
        return [
            {
                "title": "苹果发布iPhone 16",
                "url": "https://36kr.com/p/1",
                "source_platform": "36kr",
                "source_name": "36氪",
                "industry": "tech/ai",
                "rank": 1,
                "heat_score": 9500,
            },
            {
                "title": "苹果iPhone 16正式发布",
                "url": "https://weibo.com/1",
                "source_platform": "weibo",
                "source_name": "微博",
                "industry": "social",
                "rank": 1,
                "heat_score": 9000,
            },
            {
                "title": "比特币突破10万美元",
                "url": "https://wallstreetcn.com/1",
                "source_platform": "wallstreetcn-hot",
                "source_name": "华尔街见闻",
                "industry": "finance",
                "rank": 1,
                "heat_score": 8500,
            },
        ]

    # ==================== Save Tests ====================

    def test_save_fetch_result(self, store, sample_items):
        """Test saving fetch results."""
        path = store.save_fetch_result(sample_items, time_slot="morning")

        assert path.exists()
        assert "morning_fetch.json" in str(path)

    def test_save_creates_latest(self, store, sample_items):
        """Test that saving also updates latest.json."""
        store.save_fetch_result(sample_items, time_slot="morning")

        latest_path = store.raw_data_path / "latest.json"
        assert latest_path.exists()

    def test_save_enriches_items(self, store, sample_items):
        """Test that items are enriched with metadata."""
        store.save_fetch_result(sample_items, time_slot="morning")

        data = store.load_latest()
        items = data["items"]

        # Check ID format
        assert all("id" in item for item in items)
        assert items[0]["id"].startswith("news-")

        # Check cross-platform info
        assert all("cross_platform" in item for item in items)

    def test_cross_platform_detection(self, store):
        """Test that cross-platform topics are detected."""
        # Use nearly identical titles for reliable matching
        items = [
            {
                "title": "苹果发布iPhone16",
                "url": "https://36kr.com/p/1",
                "source_platform": "36kr",
                "industry": "tech/ai",
                "heat_score": 9500,
            },
            {
                "title": "苹果发布iPhone16",  # Same title, different platform
                "url": "https://weibo.com/1",
                "source_platform": "weibo",
                "industry": "social",
                "heat_score": 9000,
            },
            {
                "title": "比特币突破10万美元",
                "url": "https://wallstreetcn.com/1",
                "source_platform": "wallstreetcn-hot",
                "industry": "finance",
                "heat_score": 8500,
            },
        ]
        store.save_fetch_result(items, time_slot="morning")

        data = store.load_latest()
        result_items = data["items"]

        # iPhone news should be cross-platform (36kr + weibo)
        iphone_items = [i for i in result_items if "苹果" in i["title"]]

        # At least one should be marked as cross-platform
        cross_platform_items = [i for i in iphone_items if i["cross_platform"]["is_trending"]]
        assert len(cross_platform_items) > 0
        assert len(cross_platform_items[0]["cross_platform"]["platforms"]) >= 2

    def test_statistics_calculation(self, store, sample_items):
        """Test statistics are calculated correctly."""
        store.save_fetch_result(sample_items, time_slot="morning")

        data = store.load_latest()
        stats = data["statistics"]

        assert "by_industry" in stats
        assert "by_source" in stats
        assert "cross_platform_count" in stats
        assert "top_items" in stats

        # Check industry counts
        assert stats["by_industry"]["tech/ai"] == 1
        assert stats["by_industry"]["social"] == 1
        assert stats["by_industry"]["finance"] == 1

    # ==================== Load Tests ====================

    def test_load_latest(self, store, sample_items):
        """Test loading latest data."""
        store.save_fetch_result(sample_items, time_slot="morning")

        data = store.load_latest()

        assert data is not None
        assert data["total_items"] == 3
        assert len(data["items"]) == 3

    def test_load_by_date(self, store, sample_items):
        """Test loading by date."""
        store.save_fetch_result(sample_items, time_slot="morning")

        today = datetime.now().strftime("%Y-%m-%d")
        data = store.load_by_date(today, "morning")

        assert data is not None
        assert data["total_items"] == 3

    def test_load_today(self, store, sample_items):
        """Test loading today's data."""
        store.save_fetch_result(sample_items, time_slot="afternoon")

        data = store.load_today("afternoon")

        assert data is not None
        assert data["time_slot"] == "afternoon"

    def test_load_nonexistent(self, store):
        """Test loading nonexistent data returns None."""
        data = store.load_by_date("2020-01-01", "morning")
        assert data is None

    def test_list_dates(self, store, sample_items):
        """Test listing available dates."""
        store.save_fetch_result(sample_items, time_slot="morning")

        dates = store.list_dates()

        assert len(dates) >= 1
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in dates

    # ==================== Query Tests ====================

    def test_get_item_by_id(self, store, sample_items):
        """Test getting item by ID."""
        store.save_fetch_result(sample_items, time_slot="morning")

        data = store.load_latest()
        first_id = data["items"][0]["id"]

        item = store.get_item_by_id(first_id)

        assert item is not None
        assert item["id"] == first_id

    def test_get_item_by_id_not_found(self, store, sample_items):
        """Test getting nonexistent item."""
        store.save_fetch_result(sample_items, time_slot="morning")

        item = store.get_item_by_id("news-2020-01-01-999")
        assert item is None

    def test_search_items(self, store, sample_items):
        """Test searching items by keyword."""
        store.save_fetch_result(sample_items, time_slot="morning")

        results = store.search_items("苹果")

        assert len(results) >= 1
        assert all("苹果" in r["title"] for r in results)

    def test_search_items_no_results(self, store, sample_items):
        """Test searching with no matches."""
        store.save_fetch_result(sample_items, time_slot="morning")

        results = store.search_items("不存在的关键词xyz")
        assert len(results) == 0

    def test_search_items_with_limit(self, store, sample_items):
        """Test search respects limit."""
        store.save_fetch_result(sample_items, time_slot="morning")

        results = store.search_items("", limit=1)  # Empty query matches all
        assert len(results) <= 1

    # ==================== Summary Update Tests ====================

    def test_update_item_summary(self, store, sample_items):
        """Test updating item summary."""
        store.save_fetch_result(sample_items, time_slot="morning")

        data = store.load_latest()
        item_id = data["items"][0]["id"]

        success = store.update_item_summary(
            item_id,
            "This is a test summary.",
            source="webfetch"
        )

        assert success

        # Verify update
        updated_item = store.get_item_by_id(item_id)
        assert updated_item["summary"] == "This is a test summary."
        assert updated_item["summary_source"] == "webfetch"

    def test_update_item_summary_invalid_id(self, store, sample_items):
        """Test updating with invalid ID."""
        store.save_fetch_result(sample_items, time_slot="morning")

        success = store.update_item_summary(
            "invalid-id",
            "Test summary"
        )

        assert not success

    # ==================== Edge Cases ====================

    def test_empty_items(self, store):
        """Test saving empty item list."""
        path = store.save_fetch_result([], time_slot="morning")

        assert path.exists()

        data = store.load_latest()
        assert data["total_items"] == 0
        assert data["items"] == []

    def test_items_without_optional_fields(self, store):
        """Test items with missing optional fields."""
        items = [
            {
                "title": "Test News",
                "url": "https://example.com",
            }
        ]

        store.save_fetch_result(items, time_slot="morning")

        data = store.load_latest()
        item = data["items"][0]

        # Should have defaults
        assert item["source_platform"] == ""
        assert item["industry"] == "unknown"
        assert item["heat_score"] == 0

    def test_normalize_title(self, store):
        """Test title normalization for cross-platform matching."""
        # Access private method for testing
        assert store._normalize_title("Hello World!") == "helloworld"
        assert store._normalize_title("苹果发布iPhone 16") == "苹果发布iphone16"
        assert store._normalize_title("") == ""

    def test_multiple_time_slots(self, store, sample_items):
        """Test saving multiple time slots."""
        store.save_fetch_result(sample_items, time_slot="morning")
        store.save_fetch_result(sample_items[:1], time_slot="afternoon")

        morning = store.load_today("morning")
        afternoon = store.load_today("afternoon")

        assert morning["total_items"] == 3
        assert afternoon["total_items"] == 1
