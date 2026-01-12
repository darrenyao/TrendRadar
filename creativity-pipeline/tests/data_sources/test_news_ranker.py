"""Unit tests for NewsRanker module."""
import pytest
from src.data_sources.news_ranker import NewsRanker, NewsScore


class TestNewsRanker:
    """Tests for NewsRanker class."""

    @pytest.fixture
    def ranker(self):
        """Create a NewsRanker instance."""
        return NewsRanker()

    @pytest.fixture
    def sample_items(self):
        """Sample news items for testing."""
        return [
            {
                "id": "news-2026-01-12-001",
                "title": "苹果发布Vision Pro 2",
                "source_platform": "36kr",
                "heat_score": 9500,
                "rank": 1,
            },
            {
                "id": "news-2026-01-12-002",
                "title": "比特币突破15万美元",
                "source_platform": "wallstreetcn-hot",
                "heat_score": 8000,
                "rank": 2,
            },
            {
                "id": "news-2026-01-12-003",
                "title": "某明星离婚",
                "source_platform": "weibo",
                "heat_score": 5000,
                "rank": 10,
            },
        ]

    # ==================== Score Item Tests ====================

    def test_score_item_returns_news_score(self, ranker, sample_items):
        """Test that score_item returns a NewsScore object."""
        score = ranker.score_item(sample_items[0])

        assert isinstance(score, NewsScore)
        assert score.item_id == "news-2026-01-12-001"
        assert score.total_score > 0

    def test_score_item_high_heat_scores_higher(self, ranker, sample_items):
        """Test that higher heat items score higher."""
        score_high = ranker.score_item(sample_items[0])  # heat_score: 9500
        score_low = ranker.score_item(sample_items[2])   # heat_score: 5000

        assert score_high.total_score > score_low.total_score

    def test_score_item_cross_platform_bonus(self, ranker):
        """Test cross-platform items get bonus."""
        item = {
            "id": "test-001",
            "title": "Test News",
            "source_platform": "weibo",
            "heat_score": 5000,
            "rank": 1,
        }

        # Without cross-platform
        score_single = ranker.score_item(item)

        # With cross-platform
        cross_info = {
            "is_trending": True,
            "platforms": ["weibo", "zhihu", "36kr"],
            "total_mentions": 3,
        }
        score_cross = ranker.score_item(item, cross_info)

        assert score_cross.cross_platform_bonus > score_single.cross_platform_bonus
        assert score_cross.total_score > score_single.total_score

    def test_score_item_source_weight_applied(self, ranker):
        """Test that source weight affects score."""
        item_high_weight = {
            "id": "test-001",
            "title": "Test News",
            "source_platform": "hackernews",  # High weight: 1.5
            "heat_score": 5000,
            "rank": 1,
        }
        item_low_weight = {
            "id": "test-002",
            "title": "Test News",
            "source_platform": "douyin",  # Lower weight: 0.9
            "heat_score": 5000,
            "rank": 1,
        }

        score_high = ranker.score_item(item_high_weight)
        score_low = ranker.score_item(item_low_weight)

        assert score_high.source_weight > score_low.source_weight
        assert score_high.total_score > score_low.total_score

    def test_score_item_recency_affects_score(self, ranker):
        """Test that rank (recency proxy) affects score."""
        item_recent = {
            "id": "test-001",
            "title": "Test News",
            "source_platform": "weibo",
            "heat_score": 5000,
            "rank": 1,  # More recent
        }
        item_old = {
            "id": "test-002",
            "title": "Test News",
            "source_platform": "weibo",
            "heat_score": 5000,
            "rank": 50,  # Less recent
        }

        score_recent = ranker.score_item(item_recent)
        score_old = ranker.score_item(item_old)

        assert score_recent.recency_score > score_old.recency_score

    # ==================== Priority Level Tests ====================

    def test_priority_level_critical(self, ranker):
        """Test critical priority level assignment."""
        item = {
            "id": "test-001",
            "title": "Major Tech Event",
            "source_platform": "hackernews",
            "heat_score": 9000,
            "rank": 1,
        }
        cross_info = {
            "is_trending": True,
            "platforms": ["hackernews", "36kr", "zhihu", "weibo"],
            "total_mentions": 4,
        }

        score = ranker.score_item(item, cross_info)
        assert score.priority_level == "critical"

    def test_priority_level_low(self, ranker):
        """Test low priority level assignment."""
        item = {
            "id": "test-001",
            "title": "Minor News",
            "source_platform": "douyin",
            "heat_score": 1000,
            "rank": 50,
        }

        score = ranker.score_item(item)
        assert score.priority_level == "low"

    # ==================== Rank Items Tests ====================

    def test_rank_items_sorts_by_score(self, ranker, sample_items):
        """Test that rank_items sorts by score descending."""
        ranked = ranker.rank_items(sample_items)

        # Should be sorted by score descending
        scores = [item["priority"]["total_score"] for item in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_items_adds_priority_field(self, ranker, sample_items):
        """Test that rank_items adds priority field to items."""
        ranked = ranker.rank_items(sample_items)

        for item in ranked:
            assert "priority" in item
            assert "total_score" in item["priority"]
            assert "priority_level" in item["priority"]
            assert "breakdown" in item["priority"]

    def test_rank_items_preserves_original_data(self, ranker, sample_items):
        """Test that ranking preserves original item data."""
        ranked = ranker.rank_items(sample_items)

        # Find the 36kr item
        kr_item = next(i for i in ranked if i["source_platform"] == "36kr")
        assert kr_item["title"] == "苹果发布Vision Pro 2"
        assert kr_item["heat_score"] == 9500

    # ==================== Statistics Tests ====================

    def test_get_statistics_returns_counts(self, ranker, sample_items):
        """Test that get_statistics returns priority counts."""
        ranked = ranker.rank_items(sample_items)
        stats = ranker.get_statistics(ranked)

        assert "total" in stats
        assert "by_priority" in stats
        assert stats["total"] == 3

    def test_get_statistics_returns_top_items(self, ranker, sample_items):
        """Test that get_statistics returns top items."""
        ranked = ranker.rank_items(sample_items)
        stats = ranker.get_statistics(ranked)

        assert "top_items" in stats
        assert len(stats["top_items"]) <= 5

    def test_get_statistics_empty_list(self, ranker):
        """Test statistics for empty list."""
        stats = ranker.get_statistics([])

        assert stats["total"] == 0
        assert stats["by_priority"] == {}

    # ==================== Edge Cases ====================

    def test_score_item_missing_fields(self, ranker):
        """Test scoring item with missing fields."""
        item = {
            "id": "test-001",
            "title": "Test News",
        }

        score = ranker.score_item(item)
        assert score.total_score >= 0
        assert score.priority_level in ["critical", "high", "medium", "low"]

    def test_score_item_unknown_source(self, ranker):
        """Test scoring item with unknown source platform."""
        item = {
            "id": "test-001",
            "title": "Test News",
            "source_platform": "unknown_platform",
            "heat_score": 5000,
            "rank": 1,
        }

        score = ranker.score_item(item)
        assert score.source_weight == 1.0  # Default weight

    def test_news_score_to_dict(self, ranker, sample_items):
        """Test NewsScore.to_dict() method."""
        score = ranker.score_item(sample_items[0])
        score_dict = score.to_dict()

        assert "total_score" in score_dict
        assert "priority_level" in score_dict
        assert "breakdown" in score_dict
        assert "heat" in score_dict["breakdown"]
        assert "cross_platform" in score_dict["breakdown"]
        assert "source_weight" in score_dict["breakdown"]
        assert "recency" in score_dict["breakdown"]

    def test_cross_platform_bonus_thresholds(self, ranker):
        """Test cross-platform bonus at different platform counts."""
        item = {
            "id": "test-001",
            "title": "Test",
            "source_platform": "weibo",
            "heat_score": 5000,
            "rank": 1,
        }

        # 1 platform
        score_1 = ranker.score_item(item, {"platforms": ["weibo"], "is_trending": False})
        # 2 platforms
        score_2 = ranker.score_item(item, {"platforms": ["weibo", "zhihu"], "is_trending": True})
        # 3 platforms
        score_3 = ranker.score_item(item, {"platforms": ["weibo", "zhihu", "36kr"], "is_trending": True})
        # 4+ platforms
        score_4 = ranker.score_item(item, {"platforms": ["weibo", "zhihu", "36kr", "v2ex"], "is_trending": True})

        assert score_1.cross_platform_bonus == 0
        assert score_2.cross_platform_bonus == 20
        assert score_3.cross_platform_bonus == 35
        assert score_4.cross_platform_bonus == 45
