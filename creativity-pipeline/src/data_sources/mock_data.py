"""Mock data for testing without calling external APIs.

Use this module when running with --mock-data flag to avoid
consuming API quotas during development and testing.

Usage:
    python -m src.main --mode once --touch-point morning --mock-data
"""

from datetime import datetime
from typing import List

from .base import RawNewsItem, SourceType, ContentType


def get_mock_twitter_data(limit: int = 20) -> List[RawNewsItem]:
    """Generate mock Twitter trending data."""
    mock_trends = [
        {"name": "#AI大模型", "description": "人工智能大模型技术突破", "tweet_count": 125000},
        {"name": "OpenAI", "description": "OpenAI发布新产品引发热议", "tweet_count": 98000},
        {"name": "#远程办公", "description": "远程工作趋势讨论", "tweet_count": 76000},
        {"name": "Rust语言", "description": "Rust编程语言越来越火", "tweet_count": 54000},
        {"name": "#创业失败", "description": "创业者分享失败经验", "tweet_count": 42000},
        {"name": "Web3", "description": "Web3技术讨论", "tweet_count": 38000},
        {"name": "#效率工具", "description": "提升工作效率的工具推荐", "tweet_count": 35000},
        {"name": "Claude", "description": "Anthropic Claude模型讨论", "tweet_count": 32000},
        {"name": "#独立开发", "description": "独立开发者交流", "tweet_count": 28000},
        {"name": "MCP协议", "description": "Model Context Protocol讨论", "tweet_count": 25000},
    ]

    items = []
    for rank, trend in enumerate(mock_trends[:limit], 1):
        item = RawNewsItem(
            title=trend["name"],
            url=f"https://twitter.com/search?q={trend['name']}",
            source_platform="twitter",
            source_type=SourceType.TIKHUB,
            content_type=ContentType.TRENDING,
            content=trend["description"],
            rank=rank,
            engagement={"tweet_count": trend["tweet_count"]},
            tags=[],
            raw_data=trend,
        )
        item.heat_score = max(1000, 10000 - (rank - 1) * 800)
        items.append(item)

    return items


def get_mock_reddit_data(limit: int = 20) -> List[RawNewsItem]:
    """Generate mock Reddit popular data."""
    mock_posts = [
        {
            "title": "Why I quit my $300k job to build my own SaaS",
            "subreddit": "startups",
            "upvotes": 2500,
            "comments": 450,
        },
        {
            "title": "The state of AI coding assistants in 2026 - honest review",
            "subreddit": "programming",
            "upvotes": 1800,
            "comments": 320,
        },
        {
            "title": "Built a tool that saves me 10 hours per week - sharing for free",
            "subreddit": "SideProject",
            "upvotes": 1500,
            "comments": 280,
        },
        {
            "title": "I interviewed 100 failed founders. Here's what I learned.",
            "subreddit": "Entrepreneur",
            "upvotes": 1200,
            "comments": 210,
        },
        {
            "title": "What tools do you use daily that most people don't know about?",
            "subreddit": "technology",
            "upvotes": 980,
            "comments": 650,
        },
        {
            "title": "Unpopular opinion: Most SaaS products solve problems that don't exist",
            "subreddit": "startups",
            "upvotes": 850,
            "comments": 420,
        },
        {
            "title": "How I got my first 1000 users without spending on marketing",
            "subreddit": "indiehackers",
            "upvotes": 720,
            "comments": 180,
        },
        {
            "title": "The most underrated programming languages for 2026",
            "subreddit": "programming",
            "upvotes": 680,
            "comments": 350,
        },
    ]

    items = []
    for rank, post in enumerate(mock_posts[:limit], 1):
        item = RawNewsItem(
            title=post["title"],
            url=f"https://reddit.com/r/{post['subreddit']}/comments/mock{rank}",
            source_platform="reddit",
            source_type=SourceType.TIKHUB,
            content_type=ContentType.DISCUSSION,
            content="",
            author="mock_user",
            rank=rank,
            engagement={
                "upvotes": post["upvotes"],
                "comments": post["comments"],
                "awards": 0,
            },
            tags=[post["subreddit"]],
            raw_data=post,
        )
        item.heat_score = post["upvotes"] // 10 + post["comments"] * 3
        items.append(item)

    return items


def get_mock_xiaohongshu_data(limit: int = 20) -> List[RawNewsItem]:
    """Generate mock Xiaohongshu hot list data."""
    mock_notes = [
        {"title": "AI工具推荐｜这10个工具让我效率翻倍", "score": "923万", "hot_value": 9230000},
        {"title": "程序员转行做自媒体的真实收入", "score": "856万", "hot_value": 8560000},
        {"title": "远程工作一年后的真实感受", "score": "782万", "hot_value": 7820000},
        {"title": "创业失败后我学到的5个教训", "score": "698万", "hot_value": 6980000},
        {"title": "独立开发者的一天是怎样的", "score": "645万", "hot_value": 6450000},
        {"title": "这个APP帮我戒掉了手机瘾", "score": "578万", "hot_value": 5780000},
        {"title": "从0到1做一个小程序需要多久", "score": "512万", "hot_value": 5120000},
        {"title": "吐槽一下现在的SaaS产品", "score": "467万", "hot_value": 4670000},
        {"title": "35岁程序员的出路在哪里", "score": "423万", "hot_value": 4230000},
        {"title": "我用Claude写了一个自动化工具", "score": "389万", "hot_value": 3890000},
    ]

    items = []
    for rank, note in enumerate(mock_notes[:limit], 1):
        item = RawNewsItem(
            title=note["title"],
            url=f"https://www.xiaohongshu.com/explore/mock{rank}",
            source_platform="xiaohongshu",
            source_type=SourceType.TIKHUB,
            content_type=ContentType.USER_POST,
            content="",
            rank=rank,
            engagement={
                "likes": note["hot_value"] // 100,
                "comments": note["hot_value"] // 500,
                "collects": note["hot_value"] // 200,
                "hot_value": note["score"],
            },
            tags=[],
            raw_data=note,
        )
        item.heat_score = note["hot_value"] // 1000
        items.append(item)

    return items


def get_mock_weibo_data(limit: int = 20) -> List[RawNewsItem]:
    """Generate mock Weibo hot search data."""
    mock_topics = [
        {"word": "AI编程助手", "num": 1580000, "label": "热"},
        {"word": "创业公司裁员", "num": 1320000, "label": "新"},
        {"word": "远程办公政策", "num": 1150000, "label": ""},
        {"word": "程序员35岁", "num": 980000, "label": ""},
        {"word": "开源项目", "num": 870000, "label": ""},
        {"word": "副业赚钱", "num": 760000, "label": ""},
        {"word": "技术博客", "num": 650000, "label": ""},
        {"word": "自媒体变现", "num": 540000, "label": ""},
        {"word": "产品经理", "num": 430000, "label": ""},
        {"word": "效率工具推荐", "num": 320000, "label": ""},
    ]

    items = []
    for rank, topic in enumerate(mock_topics[:limit], 1):
        item = RawNewsItem(
            title=topic["word"],
            url=f"https://s.weibo.com/weibo?q={topic['word']}",
            source_platform="weibo",
            source_type=SourceType.TIKHUB,
            content_type=ContentType.HOT_SEARCH,
            content="",
            rank=rank,
            engagement={
                "hot_value": topic["num"],
            },
            tags=[topic["label"]] if topic["label"] else [],
            raw_data=topic,
        )
        item.heat_score = topic["num"] // 100
        items.append(item)

    return items


def get_mock_zhihu_data(limit: int = 20) -> List[RawNewsItem]:
    """Generate mock Zhihu hot questions data."""
    mock_questions = [
        {"title": "如何评价AI对程序员行业的冲击？", "heat": 8500000},
        {"title": "为什么越来越多的人选择独立开发？", "heat": 7200000},
        {"title": "30岁转行做程序员还来得及吗？", "heat": 6800000},
        {"title": "创业失败后如何调整心态？", "heat": 5900000},
        {"title": "有哪些提高工作效率的方法？", "heat": 5200000},
        {"title": "远程工作真的好吗？", "heat": 4600000},
        {"title": "如何看待SaaS创业的前景？", "heat": 4100000},
        {"title": "程序员如何提升自己的核心竞争力？", "heat": 3700000},
    ]

    items = []
    for rank, q in enumerate(mock_questions[:limit], 1):
        item = RawNewsItem(
            title=q["title"],
            url=f"https://www.zhihu.com/question/mock{rank}",
            source_platform="zhihu",
            source_type=SourceType.NEWSNOW,
            content_type=ContentType.DISCUSSION,
            content="",
            rank=rank,
            engagement={"heat": q["heat"]},
            tags=[],
            raw_data=q,
        )
        item.heat_score = q["heat"] // 1000
        items.append(item)

    return items


# Platform to mock function mapping
MOCK_DATA_FUNCTIONS = {
    "twitter": get_mock_twitter_data,
    "reddit": get_mock_reddit_data,
    "xiaohongshu": get_mock_xiaohongshu_data,
    "weibo": get_mock_weibo_data,
    "zhihu": get_mock_zhihu_data,
}


def get_mock_data(platform: str, limit: int = 20) -> List[RawNewsItem]:
    """Get mock data for a specific platform.

    Args:
        platform: Platform identifier.
        limit: Maximum items to return.

    Returns:
        List of mock RawNewsItem objects.
    """
    mock_func = MOCK_DATA_FUNCTIONS.get(platform)
    if mock_func:
        return mock_func(limit)
    return []


def is_mock_mode() -> bool:
    """Check if mock data mode is enabled."""
    import os
    return os.environ.get("MOCK_DATA_SOURCES", "").lower() in ("1", "true", "yes")
