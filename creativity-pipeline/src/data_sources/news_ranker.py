"""News ranking module for priority scoring.

Provides multi-dimensional scoring to help identify the most important news items.
Integrated with NewsStore to enrich items with priority scores.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class NewsScore:
    """Detailed score breakdown for a news item."""

    item_id: str
    heat_score: float           # Original heat score (0-100)
    cross_platform_bonus: float  # Cross-platform bonus (0-50)
    source_weight: float        # Source credibility weight (0.5-1.5)
    recency_score: float        # Time-based score (0-20)
    total_score: float          # Final weighted score
    priority_level: str         # "critical" | "high" | "medium" | "low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_score": round(self.total_score, 1),
            "priority_level": self.priority_level,
            "breakdown": {
                "heat": round(self.heat_score, 1),
                "cross_platform": round(self.cross_platform_bonus, 1),
                "source_weight": round(self.source_weight, 2),
                "recency": round(self.recency_score, 1),
            }
        }


class NewsRanker:
    """Multi-dimensional news ranking system.

    Scoring dimensions:
    1. Heat score - Original platform heat/popularity
    2. Cross-platform bonus - Items appearing on multiple platforms
    3. Source weight - Credibility/relevance of source platform
    4. Recency - Fresher news scores higher

    Priority levels:
    - critical (90+): Must-read, major industry events
    - high (70-89): Important trends, significant changes
    - medium (50-69): Worth noting, potential opportunities
    - low (<50): Background information
    """

    # Source platform weights for different industries
    # Higher weight = more credible/relevant for business insights
    SOURCE_WEIGHTS: Dict[str, float] = {
        # Tech/AI - High weight (primary focus)
        "36kr": 1.4,
        "hackernews": 1.5,
        "producthunt": 1.5,
        "github-trending-today": 1.3,
        "v2ex": 1.2,
        "sspai": 1.2,
        "zhihu": 1.2,

        # Finance - High weight
        "wallstreetcn-hot": 1.4,
        "cls-hot": 1.3,
        "xueqiu": 1.3,
        "eastmoney": 1.2,

        # Social/General - Medium weight
        "weibo": 1.0,
        "toutiao": 1.0,
        "baidu": 0.9,
        "douyin": 0.9,
        "bilibili-hot-search": 1.0,

        # International
        "twitter": 1.3,
        "reddit": 1.2,
        "xiaohongshu": 1.0,
    }

    # Cross-platform bonus thresholds
    CROSS_PLATFORM_BONUS = {
        1: 0,      # Single platform
        2: 20,     # 2 platforms
        3: 35,     # 3 platforms
        4: 45,     # 4+ platforms
    }

    def __init__(self, user_preferences: Optional[Dict] = None):
        """Initialize ranker with optional user preferences.

        Args:
            user_preferences: Optional dict with keyword/industry preferences.
        """
        self.user_preferences = user_preferences or {}

    def score_item(
        self,
        item: Dict[str, Any],
        cross_platform_info: Optional[Dict] = None
    ) -> NewsScore:
        """Calculate priority score for a single news item.

        Args:
            item: News item dictionary.
            cross_platform_info: Optional cross-platform detection info.

        Returns:
            NewsScore with detailed breakdown.
        """
        item_id = item.get("id", "unknown")

        # 1. Heat score (normalize to 0-100)
        raw_heat = self._get_heat_value(item)
        heat_score = min(raw_heat / 100, 100)  # Normalize assuming max 10000

        # 2. Cross-platform bonus
        cross_info = cross_platform_info or item.get("cross_platform", {})
        platform_count = len(cross_info.get("platforms", [item.get("source_platform", "")]))
        cross_bonus = self._get_cross_platform_bonus(platform_count)

        # 3. Source weight
        source = item.get("source_platform", "unknown").lower()
        source_weight = self.SOURCE_WEIGHTS.get(source, 1.0)

        # 4. Recency score (simplified - could be enhanced with timestamps)
        rank = item.get("rank", 50)
        recency_score = max(0, 20 - rank * 0.4)  # Higher rank = less recent

        # Calculate total score
        base_score = heat_score + cross_bonus + recency_score
        total_score = base_score * source_weight

        # Determine priority level
        priority_level = self._get_priority_level(total_score)

        return NewsScore(
            item_id=item_id,
            heat_score=heat_score,
            cross_platform_bonus=cross_bonus,
            source_weight=source_weight,
            recency_score=recency_score,
            total_score=total_score,
            priority_level=priority_level,
        )

    def rank_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score and rank a list of news items.

        Args:
            items: List of news item dictionaries.

        Returns:
            Items sorted by priority score (highest first), with scores added.
        """
        scored_items = []

        for item in items:
            score = self.score_item(item)
            item_with_score = {
                **item,
                "priority": score.to_dict(),
            }
            scored_items.append((score.total_score, item_with_score))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[0], reverse=True)

        return [item for _, item in scored_items]

    def get_statistics(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate ranking statistics for a set of items.

        Args:
            items: List of items with priority scores.

        Returns:
            Statistics dictionary.
        """
        if not items:
            return {"total": 0, "by_priority": {}}

        priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for item in items:
            priority = item.get("priority", {})
            level = priority.get("priority_level", "low")
            priority_counts[level] = priority_counts.get(level, 0) + 1

        # Get top items
        sorted_items = sorted(
            items,
            key=lambda x: x.get("priority", {}).get("total_score", 0),
            reverse=True
        )
        top_items = [
            {
                "title": item.get("title", "")[:50],
                "score": item.get("priority", {}).get("total_score", 0),
                "level": item.get("priority", {}).get("priority_level", "low"),
            }
            for item in sorted_items[:5]
        ]

        return {
            "total": len(items),
            "by_priority": priority_counts,
            "top_items": top_items,
        }

    def _get_heat_value(self, item: Dict[str, Any]) -> float:
        """Extract heat value from item, handling different field names."""
        for field in ["heat_score", "heat", "hot_value", "score"]:
            value = item.get(field)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        return 0

    def _get_cross_platform_bonus(self, platform_count: int) -> float:
        """Get bonus score based on number of platforms."""
        if platform_count >= 4:
            return self.CROSS_PLATFORM_BONUS[4]
        return self.CROSS_PLATFORM_BONUS.get(platform_count, 0)

    def _get_priority_level(self, total_score: float) -> str:
        """Determine priority level from total score."""
        if total_score >= 90:
            return "critical"
        elif total_score >= 70:
            return "high"
        elif total_score >= 50:
            return "medium"
        else:
            return "low"
