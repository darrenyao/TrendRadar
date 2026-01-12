"""Tests for ObsidianStore."""

import os
import tempfile
import pytest
from pathlib import Path

from src.state.obsidian_store import ObsidianStore
from src.state.schemas import Card, Idea, Experiment, CardCategory, IdeaStatus


@pytest.fixture
def temp_vault():
    """Create a temporary vault directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def store(temp_vault):
    """Create an ObsidianStore with temporary vault."""
    return ObsidianStore(vault_path=temp_vault)


class TestObsidianStore:
    """Tests for ObsidianStore class."""

    def test_init_creates_directories(self, store, temp_vault):
        """Test that initialization creates vault directories."""
        assert (Path(temp_vault) / "cards").exists()
        assert (Path(temp_vault) / "ideas").exists()
        assert (Path(temp_vault) / "experiments").exists()
        assert (Path(temp_vault) / "archive").exists()

    def test_write_and_read_card(self, store):
        """Test writing and reading a card."""
        card_data = {
            "title": "Test Card",
            "content": "Test content",
            "source": "test",
            "industry": "tech/ai",
            "category": "change",
            "keywords": ["test", "card"],
            "heat_score": 85,
            "analysis": {
                "change": "Something changed",
                "affected": "Developers",
                "opportunity": "New tools"
            }
        }

        # Write card
        path = store.write_card(card_data)
        assert path is not None
        assert Path(path).exists()

        # Read card back
        cards = store.read_cards()
        assert len(cards) == 1
        assert cards[0]["title"] == "Test Card"
        assert cards[0]["status"] == "pending"

    def test_write_card_generates_id(self, store):
        """Test that write_card generates an ID if not provided."""
        card_data = {"title": "No ID Card", "content": "Test"}
        path = store.write_card(card_data)

        cards = store.read_cards()
        assert len(cards) == 1
        assert cards[0]["id"].startswith("card-")

    def test_read_cards_by_status(self, store):
        """Test filtering cards by status."""
        # Write multiple cards
        store.write_card({"title": "Card 1", "status": "pending"})
        store.write_card({"title": "Card 2", "status": "selected"})
        store.write_card({"title": "Card 3", "status": "pending"})

        pending = store.read_cards(status="pending")
        selected = store.read_cards(status="selected")

        assert len(pending) == 2
        assert len(selected) == 1

    def test_write_and_read_idea(self, store):
        """Test writing and reading an idea."""
        idea_data = {
            "title": "Test Idea",
            "one_liner": "A test idea for testing",
            "target_user": "Testers",
            "problem": "Testing is hard",
            "mvp_time": 30,
            "scores": {
                "feasibility": 8,
                "market": 7,
                "personal_fit": 9,
                "uniqueness": 6,
                "total": 30
            }
        }

        path = store.write_idea(idea_data)
        assert Path(path).exists()

        ideas = store.read_ideas()
        assert len(ideas) == 1
        assert ideas[0]["title"] == "Test Idea"

    def test_write_and_read_experiment(self, store):
        """Test writing and reading an experiment."""
        exp_data = {
            "idea_id": "idea-test-001",
            "idea_title": "Test Idea",
            "estimated_time": 45,
            "tasks": [
                {"id": "task-001", "description": "Task 1", "time_estimate": 15},
                {"id": "task-002", "description": "Task 2", "time_estimate": 30},
            ]
        }

        path = store.write_experiment(exp_data)
        assert Path(path).exists()

        experiments = store.read_experiments()
        assert len(experiments) == 1
        assert experiments[0]["idea_title"] == "Test Idea"

    def test_get_active_experiment(self, store):
        """Test getting active experiment."""
        # No active experiment initially
        assert store.get_active_experiment() is None

        # Create a pending experiment
        store.write_experiment({
            "idea_id": "idea-001",
            "idea_title": "Active Test",
            "status": "in_progress"
        })

        active = store.get_active_experiment()
        assert active is not None
        assert active["idea_title"] == "Active Test"

    def test_update_status(self, store):
        """Test updating item status."""
        path = store.write_card({"title": "Status Test"})
        cards = store.read_cards()
        card_id = cards[0]["id"]

        # Update status
        result = store.update_status(card_id, "selected")
        assert result is True

        # Verify update
        cards = store.read_cards(status="selected")
        assert len(cards) == 1
        assert cards[0]["id"] == card_id

    def test_archive_item(self, store, temp_vault):
        """Test archiving an item."""
        path = store.write_card({"title": "Archive Test"})
        cards = store.read_cards()
        card_id = cards[0]["id"]

        # Archive
        result = store.archive_item(card_id)
        assert result is True

        # Verify moved to archive
        cards = store.read_cards()
        assert len(cards) == 0

        archive_path = Path(temp_vault) / "archive" / "cards" / f"{card_id}.md"
        assert archive_path.exists()


class TestFrontmatterParsing:
    """Tests for frontmatter parsing."""

    def test_parse_frontmatter(self, store):
        """Test parsing YAML frontmatter."""
        content = """---
title: Test
status: pending
---

# Body content
"""
        frontmatter, body = store._parse_frontmatter(content)
        assert frontmatter["title"] == "Test"
        assert frontmatter["status"] == "pending"
        assert "Body content" in body

    def test_parse_no_frontmatter(self, store):
        """Test parsing content without frontmatter."""
        content = "# Just a header\n\nSome content"
        frontmatter, body = store._parse_frontmatter(content)
        assert frontmatter == {}
        assert body == content

    def test_render_markdown(self, store):
        """Test rendering markdown with frontmatter."""
        frontmatter = {"title": "Test", "status": "pending"}
        body = "# Content"

        result = store._render_markdown(frontmatter, body)
        assert result.startswith("---\n")
        assert "title: Test" in result
        assert "---\n\n# Content" in result
