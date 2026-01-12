"""News preprocessor for deduplication and clustering.

This module provides preprocessing capabilities for news items:
1. Keyword extraction from titles
2. Similarity-based clustering
3. Cross-platform topic detection
4. Enriched output for agent consumption
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class NewsCluster:
    """Represents a cluster of related news items.

    Attributes:
        cluster_id: Unique identifier for the cluster
        topic: Main topic extracted from representative news
        news_items: List of news items in this cluster
        sources: Set of source platforms
        total_heat: Aggregated heat score
        cross_platform: Whether this topic appears on multiple platforms
        representative: The most representative news item (highest heat)
    """
    cluster_id: str
    topic: str
    news_items: List[Dict[str, Any]]
    sources: Set[str]
    total_heat: int
    cross_platform: bool
    representative: Dict[str, Any]


class NewsPreprocessor:
    """Preprocessor for news deduplication and clustering.

    Features:
    - Keyword extraction from Chinese/English titles
    - Jaccard similarity-based clustering
    - Cross-platform topic detection
    - Enriched output with metadata

    Example:
        >>> preprocessor = NewsPreprocessor()
        >>> clusters = preprocessor.preprocess(news_items)
        >>> enriched = preprocessor.to_agent_input(clusters, limit=10)
    """

    # Stopwords for filtering (Chinese and English)
    DEFAULT_STOPWORDS = {
        # Chinese single characters
        "的", "是", "在", "了", "和", "与", "为", "被", "将", "把",
        "这", "那", "有", "没", "不", "也", "都", "就", "要", "会",
        "之", "等", "及", "或", "但", "而", "且", "着", "过", "到",
        "从", "向", "对", "让", "给", "于", "上", "下", "中", "来",
        # Chinese common words
        "可以", "可能", "应该", "已经", "正在", "一个", "什么", "怎么",
        "如何", "为什么", "哪些", "这些", "那些", "自己", "我们", "他们",
        "你们", "它们", "因为", "所以", "如果", "虽然", "但是", "而且",
        "或者", "以及", "通过", "进行", "表示", "认为", "成为", "开始",
        # English stopwords
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "can",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "and", "or", "but", "if", "then", "so", "as", "that", "this",
        "it", "its", "new", "all", "any", "no", "not", "now", "out",
        "up", "our", "you", "your", "more", "some", "such", "into",
    }

    def __init__(
        self,
        similarity_threshold: float = 0.25,  # Lower threshold for n-gram matching
        stopwords: Optional[Set[str]] = None,
        min_keyword_length: int = 2
    ):
        """Initialize the preprocessor.

        Args:
            similarity_threshold: Minimum Jaccard similarity for clustering (0-1).
                                  Lower values create more clusters.
            stopwords: Custom stopwords set. Uses default if None.
            min_keyword_length: Minimum length for a keyword to be considered.
        """
        self.similarity_threshold = similarity_threshold
        self.stopwords = stopwords or self.DEFAULT_STOPWORDS
        self.min_keyword_length = min_keyword_length

    def preprocess(self, news_items: List[Dict[str, Any]]) -> List[NewsCluster]:
        """Preprocess news items: extract keywords, cluster, and sort.

        Args:
            news_items: List of news items with title, source_platform, heat fields.

        Returns:
            List of NewsCluster objects, sorted by (cross_platform, total_heat).
        """
        if not news_items:
            return []

        logger.info(f"Preprocessing {len(news_items)} news items")

        # Step 1: Extract keywords for each item
        for item in news_items:
            title = item.get('title', '')
            item['_keywords'] = self._extract_keywords(title)

        # Step 2: Cluster by similarity
        clusters = self._cluster_by_similarity(news_items)

        # Step 3: Sort clusters (cross-platform first, then by heat)
        clusters.sort(key=lambda c: (c.cross_platform, c.total_heat), reverse=True)

        logger.info(
            f"Created {len(clusters)} clusters, "
            f"{sum(1 for c in clusters if c.cross_platform)} cross-platform"
        )

        return clusters

    def _extract_keywords(self, title: str) -> Set[str]:
        """Extract keywords from a title.

        Extracts Chinese words (as 2-4 character n-grams), English words,
        and numbers, filtering out stopwords and short tokens.

        For Chinese text, since there are no word boundaries, we extract
        overlapping n-grams of 2-4 characters which often represent
        meaningful words.

        Args:
            title: The news title to extract keywords from.

        Returns:
            Set of extracted keywords.
        """
        if not title:
            return set()

        keywords = set()

        # Extract Chinese sequences and process them separately
        chinese_sequences = re.findall(r'[\u4e00-\u9fa5]+', title)
        for seq in chinese_sequences:
            # Extract n-grams (2-4 characters) from Chinese text
            for n in range(2, 5):  # 2, 3, 4 character n-grams
                for i in range(len(seq) - n + 1):
                    ngram = seq[i:i + n]
                    if ngram not in self.stopwords:
                        keywords.add(ngram)

        # Extract English words and numbers
        english_tokens = re.findall(r'[a-zA-Z]+[a-zA-Z0-9]*|\d+', title)
        for token in english_tokens:
            token_lower = token.lower()
            # Filter by length and stopwords
            if len(token) >= self.min_keyword_length and token_lower not in self.stopwords:
                keywords.add(token_lower)

        return keywords

    def _calculate_similarity(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """Calculate Jaccard similarity between two keyword sets.

        Args:
            keywords1: First set of keywords.
            keywords2: Second set of keywords.

        Returns:
            Jaccard similarity coefficient (0-1).
        """
        if not keywords1 or not keywords2:
            return 0.0

        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)

        return intersection / union if union > 0 else 0.0

    def _cluster_by_similarity(self, news_items: List[Dict[str, Any]]) -> List[NewsCluster]:
        """Cluster news items by keyword similarity.

        Uses a greedy clustering approach where each item is assigned to
        the first cluster it's similar enough to, or creates a new cluster.

        Args:
            news_items: List of news items with _keywords field populated.

        Returns:
            List of NewsCluster objects.
        """
        clusters: List[NewsCluster] = []
        used_indices: Set[int] = set()

        for i, item in enumerate(news_items):
            if i in used_indices:
                continue

            # Start a new cluster with this item
            cluster_items = [item]
            sources = {item.get('source_platform', 'unknown')}
            item_keywords = item.get('_keywords', set())

            # Find similar items
            for j in range(i + 1, len(news_items)):
                if j in used_indices:
                    continue

                other = news_items[j]
                other_keywords = other.get('_keywords', set())

                similarity = self._calculate_similarity(item_keywords, other_keywords)

                if similarity >= self.similarity_threshold:
                    cluster_items.append(other)
                    sources.add(other.get('source_platform', 'unknown'))
                    used_indices.add(j)
                    # Expand cluster keywords for better matching
                    item_keywords = item_keywords | other_keywords

            used_indices.add(i)

            # Calculate cluster properties
            total_heat = sum(self._get_heat(n) for n in cluster_items)
            cross_platform = len(sources) > 1

            # Select representative (highest heat)
            representative = max(cluster_items, key=lambda x: self._get_heat(x))

            # Create cluster
            cluster = NewsCluster(
                cluster_id=f"cluster-{len(clusters) + 1:03d}",
                topic=self._extract_topic(representative),
                news_items=cluster_items,
                sources=sources,
                total_heat=total_heat,
                cross_platform=cross_platform,
                representative=representative
            )
            clusters.append(cluster)

        return clusters

    def _get_heat(self, item: Dict[str, Any]) -> int:
        """Get heat score from a news item.

        Handles various field names for heat score.

        Args:
            item: News item dictionary.

        Returns:
            Heat score as integer, defaults to 0.
        """
        # Try different field names for heat
        for field in ['heat', 'heat_score', 'hot', 'score', 'rank']:
            value = item.get(field)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
        return 0

    def _extract_topic(self, item: Dict[str, Any]) -> str:
        """Extract topic string from a news item.

        Args:
            item: News item dictionary.

        Returns:
            Topic string (truncated title).
        """
        title = item.get('title', 'Unknown Topic')
        # Truncate to 50 characters for readability
        return title[:50] + '...' if len(title) > 50 else title

    def to_agent_input(
        self,
        clusters: List[NewsCluster],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Convert clusters to enriched agent input format.

        Adds metadata about clustering to help the agent understand
        the importance and context of each news item.

        Args:
            clusters: List of NewsCluster objects.
            limit: Maximum number of items to return.

        Returns:
            List of enriched news items ready for agent consumption.
        """
        result = []

        for cluster in clusters[:limit]:
            # Start with representative item
            enriched = {**cluster.representative}

            # Remove internal fields
            enriched.pop('_keywords', None)

            # Add cluster metadata
            enriched['is_cross_platform'] = cluster.cross_platform
            enriched['related_sources'] = sorted(list(cluster.sources))
            enriched['aggregated_heat'] = cluster.total_heat
            enriched['related_news_count'] = len(cluster.news_items)

            # Add related titles (up to 3, excluding representative)
            related_titles = []
            for item in cluster.news_items:
                if item.get('title') != cluster.representative.get('title'):
                    related_titles.append(item.get('title', ''))
                    if len(related_titles) >= 3:
                        break
            enriched['related_titles'] = related_titles

            # Add cluster ID for tracing
            enriched['cluster_id'] = cluster.cluster_id

            result.append(enriched)

        return result

    def get_statistics(self, clusters: List[NewsCluster]) -> Dict[str, Any]:
        """Get statistics about clustering results.

        Useful for logging and debugging.

        Args:
            clusters: List of NewsCluster objects.

        Returns:
            Dictionary with clustering statistics.
        """
        if not clusters:
            return {
                'total_clusters': 0,
                'total_items': 0,
                'cross_platform_count': 0,
                'avg_cluster_size': 0,
                'max_cluster_size': 0,
                'sources_distribution': {}
            }

        total_items = sum(len(c.news_items) for c in clusters)
        cross_platform_count = sum(1 for c in clusters if c.cross_platform)
        cluster_sizes = [len(c.news_items) for c in clusters]

        # Count items by source
        source_counts: Dict[str, int] = defaultdict(int)
        for cluster in clusters:
            for item in cluster.news_items:
                source = item.get('source_platform', 'unknown')
                source_counts[source] += 1

        return {
            'total_clusters': len(clusters),
            'total_items': total_items,
            'cross_platform_count': cross_platform_count,
            'cross_platform_ratio': cross_platform_count / len(clusters) if clusters else 0,
            'avg_cluster_size': total_items / len(clusters) if clusters else 0,
            'max_cluster_size': max(cluster_sizes) if cluster_sizes else 0,
            'single_item_clusters': sum(1 for s in cluster_sizes if s == 1),
            'sources_distribution': dict(source_counts)
        }
