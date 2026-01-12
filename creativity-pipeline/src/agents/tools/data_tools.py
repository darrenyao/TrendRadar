"""MCP tools for Agent data access.

Provides tools for reading raw news data and fetching article summaries.
These tools enable Agent-driven analysis with full context.
"""
import os
import json
import logging
import aiohttp
from datetime import datetime
from typing import Any, Dict

try:
    from claude_agent_sdk import tool
    HAS_CLAUDE_SDK = True
except ImportError:
    HAS_CLAUDE_SDK = False
    # Dummy decorator for when SDK is not available
    def tool(name, description, params):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)


def _get_vault_path() -> str:
    """Get vault path from environment or default."""
    return os.environ.get("VAULT_PATH") or os.environ.get("OBSIDIAN_VAULT_PATH", "./vault")


def _get_store():
    """Get NewsStore instance."""
    from ...data_sources.news_store import NewsStore
    return NewsStore(_get_vault_path())


# ==================== News Data Tools ====================

@tool(
    "read_raw_news",
    "Read raw news data from local storage. Returns full news items with title, summary, URL, source, heat_score, and cross-platform info.",
    {
        "date": str,      # Optional: YYYY-MM-DD, defaults to today
        "time_slot": str, # Optional: morning|afternoon|evening|latest, defaults to latest
    }
)
async def read_raw_news(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read raw news data from local storage.

    Args:
        args: Dictionary with optional date and time_slot.

    Returns:
        MCP response with news data or error.
    """
    try:
        store = _get_store()

        date = args.get("date", "")
        time_slot = args.get("time_slot", "latest")

        if time_slot == "latest" or not time_slot:
            data = store.load_latest()
        elif date:
            data = store.load_by_date(date, time_slot)
        else:
            data = store.load_today(time_slot)

        if not data:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": "No data found. Please run fetch first.",
                        "hint": "Use the data fetcher to populate raw_data/latest.json"
                    }, ensure_ascii=False)
                }]
            }

        # Return summary for large datasets
        total_items = data.get("total_items", 0)
        items = data.get("items", [])

        # For large datasets, return statistics + top items
        if total_items > 50:
            response = {
                "success": True,
                "fetch_time": data.get("fetch_time"),
                "total_items": total_items,
                "statistics": data.get("statistics", {}),
                "items_preview": items[:30],  # First 30 items
                "note": f"Showing 30 of {total_items} items. Use search_news for specific queries."
            }
        else:
            response = {
                "success": True,
                "fetch_time": data.get("fetch_time"),
                "total_items": total_items,
                "statistics": data.get("statistics", {}),
                "items": items,
            }

        return {
            "content": [{
                "type": "text",
                "text": json.dumps(response, ensure_ascii=False, indent=2)
            }]
        }

    except Exception as e:
        logger.error(f"Error reading raw news: {e}")
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": str(e)
                }, ensure_ascii=False)
            }]
        }


@tool(
    "search_news",
    "Search news items by keyword in title.",
    {
        "query": str,     # Required: search keyword
        "date": str,      # Optional: YYYY-MM-DD
        "limit": int,     # Optional: max results, default 20
    }
)
async def search_news(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search news items by keyword.

    Args:
        args: Dictionary with query, optional date and limit.

    Returns:
        MCP response with matching items.
    """
    try:
        store = _get_store()

        query = args.get("query", "")
        if not query:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": "query parameter is required"
                    }, ensure_ascii=False)
                }]
            }

        date = args.get("date", "")
        limit = args.get("limit", 20)

        results = store.search_items(query, date if date else None, limit)

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "query": query,
                    "count": len(results),
                    "items": results
                }, ensure_ascii=False, indent=2)
            }]
        }

    except Exception as e:
        logger.error(f"Error searching news: {e}")
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": str(e)
                }, ensure_ascii=False)
            }]
        }


@tool(
    "get_news_item",
    "Get a specific news item by ID.",
    {
        "item_id": str,  # Required: news item ID (e.g., news-2026-01-12-001)
    }
)
async def get_news_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get a specific news item by ID.

    Args:
        args: Dictionary with item_id.

    Returns:
        MCP response with item data.
    """
    try:
        store = _get_store()

        item_id = args.get("item_id", "")
        if not item_id:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": "item_id parameter is required"
                    }, ensure_ascii=False)
                }]
            }

        item = store.get_item_by_id(item_id)

        if not item:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": f"Item not found: {item_id}"
                    }, ensure_ascii=False)
                }]
            }

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "item": item
                }, ensure_ascii=False, indent=2)
            }]
        }

    except Exception as e:
        logger.error(f"Error getting news item: {e}")
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": str(e)
                }, ensure_ascii=False)
            }]
        }


# ==================== Summary Fetching Tools ====================

@tool(
    "fetch_article_summary",
    "Fetch article content and extract summary from URL. Use this when an item's summary is empty and you need more context.",
    {
        "url": str,           # Required: article URL
        "item_id": str,       # Optional: news item ID to update
        "max_length": int,    # Optional: max summary length, default 500
    }
)
async def fetch_article_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch article content and extract summary.

    Args:
        args: Dictionary with url, optional item_id and max_length.

    Returns:
        MCP response with summary.
    """
    try:
        url = args.get("url", "")
        if not url:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": "url parameter is required"
                    }, ensure_ascii=False)
                }]
            }

        item_id = args.get("item_id", "")
        max_length = args.get("max_length", 500)

        # Fetch article content
        summary = await _fetch_and_extract_summary(url, max_length)

        if not summary:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": "Failed to fetch article content",
                        "url": url
                    }, ensure_ascii=False)
                }]
            }

        # Update item if ID provided
        if item_id:
            store = _get_store()
            store.update_item_summary(item_id, summary, source="webfetch")

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "url": url,
                    "summary": summary,
                    "length": len(summary),
                    "item_updated": bool(item_id)
                }, ensure_ascii=False, indent=2)
            }]
        }

    except Exception as e:
        logger.error(f"Error fetching article summary: {e}")
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": str(e)
                }, ensure_ascii=False)
            }]
        }


async def _fetch_and_extract_summary(url: str, max_length: int = 500) -> str:
    """Fetch URL and extract text summary.

    Args:
        url: Article URL.
        max_length: Maximum summary length.

    Returns:
        Extracted summary text.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeautifulSoup not installed, using basic extraction")
        return ""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status != 200:
                    return ""

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Remove script and style elements
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()

                # Try common article content selectors
                selectors = [
                    'article',
                    '.article-content',
                    '.post-content',
                    '.entry-content',
                    '.content',
                    'main',
                    '.main-content',
                    '#content',
                ]

                for selector in selectors:
                    content = soup.select_one(selector)
                    if content:
                        text = content.get_text(separator=' ', strip=True)
                        if len(text) > 100:  # Minimum content length
                            return text[:max_length] + ('...' if len(text) > max_length else '')

                # Fallback: get body text
                body = soup.body
                if body:
                    text = body.get_text(separator=' ', strip=True)
                    return text[:max_length] + ('...' if len(text) > max_length else '')

                return ""

    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return ""


# ==================== Tool Registration ====================

def get_data_tools() -> list:
    """Get all data tools for MCP server registration.

    Returns:
        List of tool functions.
    """
    return [
        read_raw_news,
        search_news,
        get_news_item,
        fetch_article_summary,
    ]
