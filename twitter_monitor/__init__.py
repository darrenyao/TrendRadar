"""
Twitter Monitor - Twitter帖子抓取与聚类分析模块

功能：
- 抓取指定Twitter用户的帖子
- 使用LLM对帖子内容进行聚类分析
- 每天早中晚三次推送聚类总结
- Supabase 云端存储与向量检索
"""

from .scraper import TwitterScraper
from .analyzer import PostAnalyzer
from .scheduler import TwitterScheduler
from .storage import TwitterStorage
from .main import TwitterMonitor

# Supabase 存储（可选）
try:
    from .supabase_storage import SupabaseStorage, get_supabase_storage
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    SupabaseStorage = None
    get_supabase_storage = None

__version__ = "1.1.0"
__all__ = [
    "TwitterScraper",
    "PostAnalyzer",
    "TwitterScheduler",
    "TwitterStorage",
    "TwitterMonitor",
    "SupabaseStorage",
    "get_supabase_storage",
    "SUPABASE_AVAILABLE",
]
