"""Tests for PipelineStateMachine."""

import tempfile
import pytest

from src.state.obsidian_store import ObsidianStore
from src.state.state_machine import PipelineStateMachine
from src.state.schemas import CardStatus, IdeaStatus, ExperimentStatus


@pytest.fixture
def temp_vault():
    """Create a temporary vault directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def store(temp_vault):
    """Create an ObsidianStore with temporary vault."""
    return ObsidianStore(vault_path=temp_vault)


@pytest.fixture
def state_machine(store):
    """Create a PipelineStateMachine with temporary store."""
    return PipelineStateMachine(store=store)


class TestCardSelection:
    """Tests for card selection functionality."""

    def test_record_selection(self, state_machine, store):
        """Test recording card selection."""
        # Create some cards
        store.write_card({"title": "Card 1"})
        store.write_card({"title": "Card 2"})
        store.write_card({"title": "Card 3"})

        # Select cards 1 and 3
        selected = state_machine.record_selection([1, 3])
        assert len(selected) == 2

        # Verify status updated
        selected_cards = state_machine.get_selected_cards()
        assert len(selected_cards) == 2

    def test_record_selection_invalid_indices(self, state_machine, store):
        """Test selection with invalid indices."""
        store.write_card({"title": "Card 1"})

        # Try to select non-existent cards
        selected = state_machine.record_selection([1, 5, 10])
        assert len(selected) == 1  # Only card 1 selected


class TestIdeaManagement:
    """Tests for idea management."""

    def test_set_top3(self, state_machine, store):
        """Test setting top 3 ideas."""
        # Create ideas
        store.write_idea({"title": "Idea 1", "status": "candidate"})
        store.write_idea({"title": "Idea 2", "status": "candidate"})
        store.write_idea({"title": "Idea 3", "status": "candidate"})

        ideas = store.read_ideas()
        idea_ids = [i["id"] for i in ideas]

        # Set top 3
        result = state_machine.set_top3(idea_ids)
        assert result is True

        top3 = state_machine.get_top3_ideas()
        assert len(top3) == 3

    def test_confirm_top1(self, state_machine, store):
        """Test confirming top 1 idea."""
        # Create and set top 3
        store.write_idea({"title": "Idea 1", "status": "top3"})
        store.write_idea({"title": "Idea 2", "status": "top3"})
        store.write_idea({"title": "Idea 3", "status": "top3"})

        # Confirm first idea
        confirmed = state_machine.confirm_top1(1)
        assert confirmed is not None
        assert confirmed["status"] == "confirmed"

        # Verify only one confirmed
        confirmed_idea = state_machine.get_confirmed_idea()
        assert confirmed_idea is not None


class TestExperimentManagement:
    """Tests for experiment management."""

    def test_create_experiment(self, state_machine, store):
        """Test creating an experiment."""
        idea = {"id": "idea-test-001", "title": "Test Idea"}
        tasks = {
            "estimated_time": 45,
            "tasks": [
                {"id": "task-001", "description": "Task 1", "time_estimate": 45}
            ]
        }

        experiment = state_machine.create_experiment(idea, tasks)
        assert experiment is not None
        assert experiment["idea_id"] == "idea-test-001"

    def test_wip_rule(self, state_machine, store):
        """Test WIP=1 rule enforcement."""
        idea1 = {"id": "idea-001", "title": "Idea 1"}
        idea2 = {"id": "idea-002", "title": "Idea 2"}
        tasks = {"estimated_time": 30, "tasks": []}

        # Create first experiment
        exp1 = state_machine.create_experiment(idea1, tasks)
        assert exp1 is not None

        # Try to create second - should fail
        exp2 = state_machine.create_experiment(idea2, tasks)
        assert exp2 is None

    def test_has_active_experiment(self, state_machine, store):
        """Test checking for active experiment."""
        assert state_machine.has_active_experiment() is False

        store.write_experiment({
            "idea_id": "idea-001",
            "idea_title": "Test",
            "status": "in_progress"
        })

        assert state_machine.has_active_experiment() is True

    def test_complete_experiment(self, state_machine, store):
        """Test completing an experiment."""
        store.write_experiment({
            "idea_id": "idea-001",
            "idea_title": "Test",
            "status": "in_progress"
        })

        experiments = store.read_experiments()
        exp_id = experiments[0]["id"]

        result = state_machine.complete_experiment(exp_id)
        assert result is True

        # Should allow new experiment now
        assert state_machine.has_active_experiment() is False


class TestDowngrade:
    """Tests for downgrade functionality."""

    def test_trigger_downgrade(self, state_machine, store):
        """Test triggering downgrade."""
        store.write_experiment({
            "idea_id": "idea-001",
            "idea_title": "Test",
            "status": "awaiting_evidence",
            "downgrade_level": "normal",
            "downgrade_version": {
                "task": "Post on social media",
                "expected_evidence": "Screenshot"
            }
        })

        experiments = store.read_experiments()
        exp_id = experiments[0]["id"]

        result = state_machine.trigger_downgrade(exp_id)
        assert result is not None
        assert result["downgrade_level"] == "lite"
        assert result["estimated_time"] == 5


class TestEvidence:
    """Tests for evidence recording."""

    def test_record_evidence(self, state_machine, store):
        """Test recording evidence."""
        store.write_experiment({
            "idea_id": "idea-001",
            "idea_title": "Test",
            "status": "awaiting_evidence",
            "evidence": {"screenshots": [], "feedback": [], "retrospective": ""}
        })

        result = state_machine.record_evidence("User said it was useful", "feedback")
        assert result is True

        # Verify evidence recorded
        exp = state_machine.get_active_experiment()
        assert len(exp["evidence"]["feedback"]) == 1


class TestPipelineState:
    """Tests for pipeline state query."""

    def test_get_pipeline_state(self, state_machine, store):
        """Test getting pipeline state."""
        # Create some data
        store.write_card({"title": "Card 1"})
        store.write_card({"title": "Card 2", "status": "selected"})
        store.write_idea({"title": "Idea 1", "status": "top3"})

        state = state_machine.get_pipeline_state()

        assert state["pending_cards_count"] == 1
        assert state["selected_cards_count"] == 1
        assert len(state["top3_ideas"]) == 1
        assert state["wip_available"] is True
