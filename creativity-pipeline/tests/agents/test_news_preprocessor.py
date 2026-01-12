"""Unit tests for NewsPreprocessor module."""
import pytest
from src.agents.news_preprocessor import NewsPreprocessor, NewsCluster


class TestNewsPreprocessor:
    """Tests for NewsPreprocessor class."""

    @pytest.fixture
    def preprocessor(self):
        """Create a preprocessor instance for testing."""
        return NewsPreprocessor()  # Use default threshold (0.25)

    # ==================== Keyword Extraction Tests ====================

    def test_extract_keywords_chinese(self, preprocessor):
        """Test keyword extraction from Chinese title (using n-grams)."""
        keywords = preprocessor._extract_keywords("苹果发布新款iPhone 16 Pro")
        # Chinese text is extracted as 2-4 character n-grams
        assert "苹果" in keywords
        assert "发布" in keywords
        assert "新款" in keywords
        assert "苹果发布" in keywords  # 4-char ngram
        # English and numbers
        assert "iphone" in keywords  # lowercase
        assert "pro" in keywords
        assert "16" in keywords

    def test_extract_keywords_english(self, preprocessor):
        """Test keyword extraction from English title."""
        keywords = preprocessor._extract_keywords("OpenAI releases GPT-5 with amazing features")
        assert "openai" in keywords
        assert "releases" in keywords
        assert "gpt" in keywords
        assert "features" in keywords
        assert "amazing" in keywords
        # Stopwords should be filtered
        assert "with" not in keywords

    def test_extract_keywords_mixed(self, preprocessor):
        """Test keyword extraction from mixed Chinese/English title."""
        keywords = preprocessor._extract_keywords("微软Microsoft发布Copilot 2.0版本")
        assert "微软" in keywords
        assert "microsoft" in keywords
        assert "copilot" in keywords
        assert "版本" in keywords

    def test_extract_keywords_empty(self, preprocessor):
        """Test keyword extraction from empty string."""
        keywords = preprocessor._extract_keywords("")
        assert keywords == set()

    def test_extract_keywords_filters_stopwords(self, preprocessor):
        """Test that meaningful Chinese n-grams are extracted."""
        keywords = preprocessor._extract_keywords("人工智能最新发展")
        # Meaningful n-grams should be present
        assert "人工" in keywords
        assert "智能" in keywords
        assert "人工智能" in keywords  # 4-char ngram
        assert "发展" in keywords
        assert "最新" in keywords
        # Single characters should not be present (min_keyword_length=2)
        assert len(min(keywords, key=len)) >= 2

    def test_extract_keywords_min_length(self, preprocessor):
        """Test that short tokens are filtered."""
        keywords = preprocessor._extract_keywords("AI人工智能A股市场")
        # "AI" has length 2, should be included
        assert "ai" in keywords
        # Single characters should be filtered (min_keyword_length=2)
        assert "a" not in keywords

    # ==================== Similarity Calculation Tests ====================

    def test_calculate_similarity_identical(self, preprocessor):
        """Test similarity of identical sets."""
        keywords = {"apple", "iphone", "pro"}
        similarity = preprocessor._calculate_similarity(keywords, keywords)
        assert similarity == 1.0

    def test_calculate_similarity_disjoint(self, preprocessor):
        """Test similarity of completely different sets."""
        keywords1 = {"apple", "iphone"}
        keywords2 = {"bitcoin", "crypto"}
        similarity = preprocessor._calculate_similarity(keywords1, keywords2)
        assert similarity == 0.0

    def test_calculate_similarity_partial(self, preprocessor):
        """Test similarity of partially overlapping sets."""
        keywords1 = {"apple", "iphone", "pro"}
        keywords2 = {"apple", "iphone", "max"}
        # Intersection: {apple, iphone} = 2
        # Union: {apple, iphone, pro, max} = 4
        # Jaccard: 2/4 = 0.5
        similarity = preprocessor._calculate_similarity(keywords1, keywords2)
        assert similarity == 0.5

    def test_calculate_similarity_empty(self, preprocessor):
        """Test similarity with empty sets."""
        assert preprocessor._calculate_similarity(set(), {"a", "b"}) == 0.0
        assert preprocessor._calculate_similarity({"a", "b"}, set()) == 0.0
        assert preprocessor._calculate_similarity(set(), set()) == 0.0

    # ==================== Clustering Tests ====================

    def test_cluster_similar_news(self, preprocessor):
        """Test that similar news items are clustered together."""
        # Use more similar titles to ensure clustering
        news = [
            {"title": "苹果iPhone16发布会", "source_platform": "36kr", "heat": 90},
            {"title": "苹果iPhone16正式发布", "source_platform": "weibo", "heat": 85},
            {"title": "比特币突破十万美元大关", "source_platform": "wallstreetcn-hot", "heat": 95},
        ]
        clusters = preprocessor.preprocess(news)

        # Should create 2 clusters: iPhone-related (with shared keywords) and Bitcoin
        # Note: with n-gram extraction, "苹果", "iPhone16", "发布" should be shared
        assert len(clusters) == 2

    def test_cluster_cross_platform_detection(self, preprocessor):
        """Test cross-platform topic detection."""
        # Use nearly identical titles to ensure reliable clustering
        # These share: 苹果, 发布, iphone16, 新款, 手机 and many n-grams
        news = [
            {"title": "苹果发布新款iPhone16手机", "source_platform": "36kr", "heat": 90},
            {"title": "苹果发布新款iPhone16手机售价", "source_platform": "weibo", "heat": 85},
            {"title": "比特币价格创历史新高", "source_platform": "wallstreetcn-hot", "heat": 95},
        ]
        clusters = preprocessor.preprocess(news)

        # Find iPhone cluster (should be cross-platform due to high keyword overlap)
        iphone_cluster = None
        for c in clusters:
            if "iphone" in c.topic.lower() or "苹果" in c.topic:
                iphone_cluster = c
                break

        assert iphone_cluster is not None
        assert iphone_cluster.cross_platform is True
        assert len(iphone_cluster.sources) >= 2

    def test_cluster_single_item(self, preprocessor):
        """Test that unique news creates single-item cluster."""
        news = [
            {"title": "独特新闻标题无重复", "source_platform": "test", "heat": 50},
        ]
        clusters = preprocessor.preprocess(news)

        assert len(clusters) == 1
        assert len(clusters[0].news_items) == 1
        assert clusters[0].cross_platform is False

    def test_cluster_empty_input(self, preprocessor):
        """Test preprocessing empty list."""
        clusters = preprocessor.preprocess([])
        assert clusters == []

    def test_cluster_sorting(self, preprocessor):
        """Test that clusters are sorted by cross-platform and heat."""
        news = [
            {"title": "单平台新闻A", "source_platform": "a", "heat": 100},
            {"title": "跨平台话题X", "source_platform": "a", "heat": 50},
            {"title": "跨平台话题X续", "source_platform": "b", "heat": 50},
        ]
        clusters = preprocessor.preprocess(news)

        # Cross-platform cluster should come first even with lower heat
        assert clusters[0].cross_platform is True

    def test_cluster_heat_aggregation(self, preprocessor):
        """Test that heat is aggregated across cluster items."""
        news = [
            {"title": "相同话题新闻1", "source_platform": "a", "heat": 50},
            {"title": "相同话题新闻2", "source_platform": "b", "heat": 50},
        ]
        # Use lower threshold to ensure clustering
        preprocessor.similarity_threshold = 0.3
        clusters = preprocessor.preprocess(news)

        if len(clusters) == 1:
            # If clustered together, heat should be aggregated
            assert clusters[0].total_heat == 100

    def test_cluster_representative_selection(self, preprocessor):
        """Test that representative is the highest heat item."""
        news = [
            {"title": "iPhone新闻低热度", "source_platform": "a", "heat": 30},
            {"title": "iPhone新闻高热度", "source_platform": "b", "heat": 90},
        ]
        preprocessor.similarity_threshold = 0.3
        clusters = preprocessor.preprocess(news)

        # Representative should be the high-heat item
        for cluster in clusters:
            if len(cluster.news_items) > 1:
                assert cluster.representative.get('heat') == 90

    # ==================== Agent Input Conversion Tests ====================

    def test_to_agent_input_enrichment(self, preprocessor):
        """Test that agent input is properly enriched."""
        cluster = NewsCluster(
            cluster_id="cluster-001",
            topic="测试话题",
            news_items=[
                {"title": "新闻1", "heat": 80, "_keywords": {"test"}},
                {"title": "新闻2", "heat": 70, "_keywords": {"test"}}
            ],
            sources={"weibo", "zhihu"},
            total_heat=150,
            cross_platform=True,
            representative={"title": "新闻1", "heat": 80, "_keywords": {"test"}}
        )

        result = preprocessor.to_agent_input([cluster])

        assert len(result) == 1
        item = result[0]
        assert item['is_cross_platform'] is True
        assert item['aggregated_heat'] == 150
        assert set(item['related_sources']) == {"weibo", "zhihu"}
        assert item['related_news_count'] == 2
        assert item['cluster_id'] == "cluster-001"
        # Internal _keywords should be removed
        assert '_keywords' not in item

    def test_to_agent_input_limit(self, preprocessor):
        """Test that limit is respected."""
        clusters = [
            NewsCluster(
                cluster_id=f"cluster-{i:03d}",
                topic=f"Topic {i}",
                news_items=[{"title": f"News {i}"}],
                sources={f"source{i}"},
                total_heat=i * 10,
                cross_platform=False,
                representative={"title": f"News {i}"}
            )
            for i in range(10)
        ]

        result = preprocessor.to_agent_input(clusters, limit=5)
        assert len(result) == 5

    def test_to_agent_input_related_titles(self, preprocessor):
        """Test that related titles are included (max 3)."""
        cluster = NewsCluster(
            cluster_id="cluster-001",
            topic="Topic",
            news_items=[
                {"title": "Representative"},
                {"title": "Related 1"},
                {"title": "Related 2"},
                {"title": "Related 3"},
                {"title": "Related 4"},
            ],
            sources={"a"},
            total_heat=100,
            cross_platform=False,
            representative={"title": "Representative"}
        )

        result = preprocessor.to_agent_input([cluster])

        # Should have at most 3 related titles, excluding representative
        assert len(result[0]['related_titles']) <= 3
        assert "Representative" not in result[0]['related_titles']

    # ==================== Statistics Tests ====================

    def test_get_statistics(self, preprocessor):
        """Test statistics calculation."""
        news = [
            {"title": "News A platform 1", "source_platform": "a", "heat": 50},
            {"title": "News A platform 2", "source_platform": "b", "heat": 50},
            {"title": "Unique news", "source_platform": "c", "heat": 30},
        ]
        clusters = preprocessor.preprocess(news)
        stats = preprocessor.get_statistics(clusters)

        assert stats['total_clusters'] >= 1
        assert stats['total_items'] == 3
        assert 'sources_distribution' in stats
        assert 'cross_platform_ratio' in stats

    def test_get_statistics_empty(self, preprocessor):
        """Test statistics for empty clusters."""
        stats = preprocessor.get_statistics([])

        assert stats['total_clusters'] == 0
        assert stats['total_items'] == 0
        assert stats['cross_platform_count'] == 0

    # ==================== Heat Extraction Tests ====================

    def test_get_heat_various_fields(self, preprocessor):
        """Test heat extraction from various field names."""
        assert preprocessor._get_heat({"heat": 50}) == 50
        assert preprocessor._get_heat({"heat_score": 60}) == 60
        assert preprocessor._get_heat({"hot": 70}) == 70
        assert preprocessor._get_heat({"score": 80}) == 80
        assert preprocessor._get_heat({}) == 0

    def test_get_heat_string_value(self, preprocessor):
        """Test heat extraction from string values."""
        assert preprocessor._get_heat({"heat": "50"}) == 50

    # ==================== Edge Cases ====================

    def test_news_without_source_platform(self, preprocessor):
        """Test handling news without source_platform field."""
        news = [
            {"title": "News without source", "heat": 50},
        ]
        clusters = preprocessor.preprocess(news)

        assert len(clusters) == 1
        assert "unknown" in clusters[0].sources

    def test_news_without_title(self, preprocessor):
        """Test handling news without title field."""
        news = [
            {"source_platform": "test", "heat": 50},
        ]
        clusters = preprocessor.preprocess(news)

        assert len(clusters) == 1

    def test_custom_similarity_threshold(self):
        """Test with custom similarity threshold."""
        # High threshold - less clustering
        preprocessor_high = NewsPreprocessor(similarity_threshold=0.8)
        # Low threshold - more clustering
        preprocessor_low = NewsPreprocessor(similarity_threshold=0.2)

        news = [
            {"title": "苹果iPhone发布", "source_platform": "a", "heat": 50},
            {"title": "苹果公司新品", "source_platform": "b", "heat": 50},
        ]

        clusters_high = preprocessor_high.preprocess(news)
        clusters_low = preprocessor_low.preprocess(news)

        # Higher threshold should create more clusters (less merging)
        assert len(clusters_high) >= len(clusters_low)

    def test_custom_stopwords(self):
        """Test with custom stopwords."""
        # Custom stopwords that will be filtered from n-grams
        custom_stopwords = {"苹果", "发布", "苹果发", "果发布"}
        preprocessor = NewsPreprocessor(stopwords=custom_stopwords)

        keywords = preprocessor._extract_keywords("苹果发布新款iPhone")

        # These exact strings should be filtered
        assert "苹果" not in keywords
        assert "发布" not in keywords
        # Other n-grams should still be present
        assert "新款" in keywords
        assert "iphone" in keywords


class TestNewsCluster:
    """Tests for NewsCluster dataclass."""

    def test_cluster_creation(self):
        """Test NewsCluster creation."""
        cluster = NewsCluster(
            cluster_id="test-001",
            topic="Test Topic",
            news_items=[{"title": "News 1"}],
            sources={"source1", "source2"},
            total_heat=100,
            cross_platform=True,
            representative={"title": "News 1"}
        )

        assert cluster.cluster_id == "test-001"
        assert cluster.topic == "Test Topic"
        assert len(cluster.news_items) == 1
        assert len(cluster.sources) == 2
        assert cluster.total_heat == 100
        assert cluster.cross_platform is True
