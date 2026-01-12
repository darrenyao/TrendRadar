"""Obsidian MCP tools for Agent layer.

Provides MCP tools that wrap ObsidianStore operations for use with Claude Agent SDK.
"""
import os
import json
from typing import Dict, Any, List

from claude_agent_sdk import tool

from ...state import ObsidianStore


def get_store() -> ObsidianStore:
    """Get ObsidianStore instance with configured vault path."""
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "./vault")
    return ObsidianStore(vault_path)


# ==================== Implementation Functions ====================
# These are the raw async functions that can be tested directly


async def _read_cards_impl(args: dict) -> dict:
    """Read all cards from the vault."""
    store = get_store()
    cards = []
    for file_path in store.cards_dir.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = store._parse_frontmatter(f.read())
                cards.append({**frontmatter, "body": body})
        except Exception:
            pass

    return {
        "content": [{"type": "text", "text": json.dumps(cards, ensure_ascii=False)}]
    }


async def _read_ideas_impl(args: dict) -> dict:
    """Read all ideas from the vault."""
    store = get_store()
    ideas = []
    for file_path in store.ideas_dir.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = store._parse_frontmatter(f.read())
                ideas.append({**frontmatter, "body": body})
        except Exception:
            pass

    # Sort by total score descending
    ideas.sort(key=lambda x: x.get("scores", {}).get("total", 0), reverse=True)

    return {
        "content": [{"type": "text", "text": json.dumps(ideas, ensure_ascii=False)}]
    }


async def _read_experiments_impl(args: dict) -> dict:
    """Read all experiments from the vault."""
    store = get_store()
    experiments = []
    for file_path in store.experiments_dir.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = store._parse_frontmatter(f.read())
                experiments.append({**frontmatter, "body": body})
        except Exception:
            pass

    # Sort by created date descending
    experiments.sort(key=lambda x: x.get("created", ""), reverse=True)

    return {
        "content": [{"type": "text", "text": json.dumps(experiments, ensure_ascii=False)}]
    }


async def _create_card_impl(args: dict) -> dict:
    """Create a new card in the vault."""
    store = get_store()

    card_data = {
        "title": args.get("title", ""),
        "content": args.get("content", ""),
        "source": args.get("source", ""),
        "category": args.get("category", "change"),
        "keywords": args.get("keywords", []),
        "heat_score": args.get("heat_score", 0),
        "status": "pending",
        "analysis": {
            "change": args.get("change", ""),
            "affected": args.get("affected", ""),
            "opportunity": args.get("opportunity", "")
        }
    }

    file_path = store.write_card(card_data)

    # Extract the card ID from the file path
    card_id = file_path.split("/")[-1].replace(".md", "")

    return {
        "content": [{"type": "text", "text": f"创建卡片成功: {card_id}"}]
    }


async def _create_idea_impl(args: dict) -> dict:
    """Create a new idea in the vault."""
    store = get_store()

    idea_data = {
        "title": args.get("title", ""),
        "one_liner": args.get("one_liner", ""),
        "target_user": args.get("target_user", ""),
        "problem": args.get("problem", ""),
        "unique_angle": args.get("unique_angle", ""),
        "mvp_time": args.get("mvp_time", 30),
        "source_cards": args.get("source_cards", []),
        "scores": args.get("scores", {}),
        "status": "candidate"
    }

    file_path = store.write_idea(idea_data)

    # Extract the idea ID from the file path
    idea_id = file_path.split("/")[-1].replace(".md", "")

    return {
        "content": [{"type": "text", "text": f"创建创意成功: {idea_id}"}]
    }


async def _create_experiment_impl(args: dict) -> dict:
    """Create a new experiment in the vault."""
    store = get_store()

    exp_data = {
        "idea_id": args.get("idea_id", ""),
        "idea_title": args.get("idea_title", ""),
        "estimated_time": args.get("estimated_time", 45),
        "tasks": args.get("tasks", []),
        "three_person_rule": args.get("three_person_rule", {}),
        "status": "pending"
    }

    file_path = store.write_experiment(exp_data)

    # Extract the experiment ID from the file path
    exp_id = file_path.split("/")[-1].replace(".md", "")

    return {
        "content": [{"type": "text", "text": f"创建实验成功: {exp_id}"}]
    }


async def _update_status_impl(args: dict) -> dict:
    """Update the status of an item."""
    store = get_store()

    item_id = args.get("item_id", "")
    new_status = args.get("new_status", "")

    success = store.update_status(item_id, new_status)

    if success:
        return {
            "content": [{"type": "text", "text": f"成功更新 {item_id} 状态为: {new_status}"}]
        }
    else:
        return {
            "content": [{"type": "text", "text": f"更新失败: {item_id} 不存在或无法更新"}]
        }


# ==================== MCP Tool Wrappers ====================
# These wrap the implementation functions with the @tool decorator


@tool("read_cards", "Read all input cards from Obsidian vault. Returns JSON array of cards.", {})
async def read_cards(args: dict) -> dict:
    return await _read_cards_impl(args)


@tool("read_ideas", "Read all ideas from Obsidian vault. Returns JSON array of ideas.", {})
async def read_ideas(args: dict) -> dict:
    return await _read_ideas_impl(args)


@tool("read_experiments", "Read all experiments from Obsidian vault. Returns JSON array of experiments.", {})
async def read_experiments(args: dict) -> dict:
    return await _read_experiments_impl(args)


@tool(
    "create_card",
    "Create a new input card in Obsidian vault",
    {
        "title": str,
        "content": str,
        "source": str,
        "category": str,
        "keywords": list,
        "heat_score": int
    }
)
async def create_card(args: dict) -> dict:
    return await _create_card_impl(args)


@tool(
    "create_idea",
    "Create a new idea in Obsidian vault",
    {
        "title": str,
        "one_liner": str,
        "target_user": str,
        "problem": str,
        "unique_angle": str,
        "mvp_time": int,
        "source_cards": list,
        "scores": dict
    }
)
async def create_idea(args: dict) -> dict:
    return await _create_idea_impl(args)


@tool(
    "create_experiment",
    "Create a new experiment in Obsidian vault",
    {
        "idea_id": str,
        "idea_title": str,
        "estimated_time": int,
        "tasks": list
    }
)
async def create_experiment(args: dict) -> dict:
    return await _create_experiment_impl(args)


@tool(
    "update_status",
    "Update the status of a card, idea, or experiment",
    {
        "item_id": str,
        "new_status": str
    }
)
async def update_status(args: dict) -> dict:
    return await _update_status_impl(args)


# ==================== Helper Function ====================


def get_all_tools() -> List:
    """Return all Obsidian tools for MCP server.

    Returns:
        List of SdkMcpTool objects to register with the MCP server.
    """
    return [
        read_cards,
        read_ideas,
        read_experiments,
        create_card,
        create_idea,
        create_experiment,
        update_status,
    ]


# Export implementation functions for testing
__all__ = [
    # Implementation functions (for testing)
    "_read_cards_impl",
    "_read_ideas_impl",
    "_read_experiments_impl",
    "_create_card_impl",
    "_create_idea_impl",
    "_create_experiment_impl",
    "_update_status_impl",
    # Tool objects (for MCP server)
    "read_cards",
    "read_ideas",
    "read_experiments",
    "create_card",
    "create_idea",
    "create_experiment",
    "update_status",
    # Helper
    "get_all_tools",
]
