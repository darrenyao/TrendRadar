"""Pipeline state machine for creativity pipeline.

Manages state transitions for the creativity pipeline workflow:
Input → Cards Selected → Ideas Generated → Top1 Confirmed → Experiment → Evidence → Archive
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from .obsidian_store import ObsidianStore, obsidian_store
from .schemas import (
    CardStatus, IdeaStatus, ExperimentStatus, DowngradeLevel
)

logger = logging.getLogger(__name__)


class PipelineStateMachine:
    """State machine for the creativity pipeline.

    Manages the workflow state transitions and enforces rules like:
    - WIP=1: Only one active experiment at a time
    - Evidence gate: No evidence = auto-downgrade
    - Three person rule: Each experiment needs 3 user validations
    """

    def __init__(self, store: ObsidianStore = None):
        """Initialize the state machine.

        Args:
            store: ObsidianStore instance. Uses global singleton if not provided.
        """
        self.store = store or obsidian_store

    # ==================== Card Selection ====================

    def get_pending_cards(self) -> List[Dict[str, Any]]:
        """Get all pending cards for today."""
        return self.store.get_today_cards(status="pending")

    def record_selection(self, indices: List[int]) -> List[Dict[str, Any]]:
        """Record user's card selection.

        Args:
            indices: List of 1-based indices of selected cards.

        Returns:
            List of selected card dictionaries.
        """
        today_cards = self.get_pending_cards()
        selected = []

        for idx in indices:
            if 1 <= idx <= len(today_cards):
                card = today_cards[idx - 1]
                card_id = card.get("id")
                if card_id:
                    self.store.update_status(card_id, CardStatus.SELECTED.value)
                    card["status"] = CardStatus.SELECTED.value
                    selected.append(card)

        return selected

    def get_selected_cards(self) -> List[Dict[str, Any]]:
        """Get all selected cards."""
        return self.store.get_cards_by_status(CardStatus.SELECTED.value)

    def mark_cards_processed(self, card_ids: List[str]) -> int:
        """Mark cards as processed after idea generation.

        Args:
            card_ids: List of card IDs to mark as processed.

        Returns:
            Number of cards successfully updated.
        """
        count = 0
        for card_id in card_ids:
            if self.store.update_status(card_id, CardStatus.PROCESSED.value):
                count += 1
        return count

    # ==================== Idea Management ====================

    def get_candidate_ideas(self) -> List[Dict[str, Any]]:
        """Get all candidate ideas for today."""
        return self.store.read_ideas(status="candidate")

    def get_top3_ideas(self) -> List[Dict[str, Any]]:
        """Get top 3 ideas."""
        return self.store.get_top3_ideas()

    def set_top3(self, idea_ids: List[str]) -> bool:
        """Mark ideas as top 3.

        Args:
            idea_ids: List of idea IDs to mark as top 3.

        Returns:
            True if all updates successful.
        """
        success = True
        for idea_id in idea_ids[:3]:  # Limit to 3
            if not self.store.update_status(idea_id, IdeaStatus.TOP3.value):
                success = False
        return success

    def confirm_top1(self, idea_index: int = 1) -> Optional[Dict[str, Any]]:
        """Confirm the selected idea as top 1.

        Args:
            idea_index: 1-based index of the idea to confirm from top 3.

        Returns:
            Confirmed idea dictionary or None.
        """
        top3 = self.get_top3_ideas()

        if not top3:
            logger.warning("No top 3 ideas available")
            return None

        if 1 <= idea_index <= len(top3):
            idea = top3[idea_index - 1]
            idea_id = idea.get("id")
            if idea_id:
                self.store.update_status(idea_id, IdeaStatus.CONFIRMED.value)
                idea["status"] = IdeaStatus.CONFIRMED.value
                return idea

        return None

    def get_confirmed_idea(self) -> Optional[Dict[str, Any]]:
        """Get the confirmed idea for today."""
        return self.store.get_confirmed_idea()

    # ==================== Experiment Management ====================

    def has_active_experiment(self) -> bool:
        """Check if there's an active experiment (WIP=1 rule)."""
        return self.store.get_active_experiment() is not None

    def get_active_experiment(self) -> Optional[Dict[str, Any]]:
        """Get the currently active experiment."""
        return self.store.get_active_experiment()

    def create_experiment(self, idea: Dict[str, Any], tasks: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new experiment from a confirmed idea.

        Args:
            idea: Confirmed idea dictionary.
            tasks: Task package from MVP Runner agent.

        Returns:
            Created experiment dictionary or None if WIP=1 violated.
        """
        # Check WIP=1 rule
        if self.has_active_experiment():
            logger.warning("Cannot create experiment: WIP=1 rule violated")
            return None

        experiment = {
            "idea_id": idea.get("id"),
            "idea_title": idea.get("title"),
            "downgrade_level": DowngradeLevel.NORMAL.value,
            "estimated_time": tasks.get("estimated_time", 45),
            "tasks": tasks.get("tasks", []),
            "three_person_rule": tasks.get("three_person_rule", {}),
            "downgrade_version": tasks.get("downgrade_version", {}),
            "status": ExperimentStatus.PENDING.value,
            "wip_slot": True,
            "evidence": {
                "screenshots": [],
                "feedback": [],
                "retrospective": ""
            }
        }

        path = self.store.write_experiment(experiment)

        # Update idea status
        if idea.get("id"):
            self.store.update_status(idea["id"], IdeaStatus.IN_PROGRESS.value)

        # Read back the written experiment
        experiments = self.store.read_experiments()
        for exp in experiments:
            if exp.get("path") == path:
                return exp

        return experiment

    def start_experiment(self, exp_id: str = None) -> bool:
        """Start an experiment (mark as in_progress).

        Args:
            exp_id: Experiment ID. Uses active experiment if not provided.

        Returns:
            True if successful.
        """
        if not exp_id:
            exp = self.get_active_experiment()
            if exp:
                exp_id = exp.get("id")

        if not exp_id:
            return False

        return self.store.update_status(exp_id, ExperimentStatus.IN_PROGRESS.value)

    def set_awaiting_evidence(self, exp_id: str = None) -> bool:
        """Set experiment to awaiting evidence state.

        Args:
            exp_id: Experiment ID. Uses active experiment if not provided.

        Returns:
            True if successful.
        """
        if not exp_id:
            exp = self.get_active_experiment()
            if exp:
                exp_id = exp.get("id")

        if not exp_id:
            return False

        return self.store.update_status(exp_id, ExperimentStatus.AWAITING_EVIDENCE.value)

    # ==================== Evidence & Completion ====================

    def record_evidence(self, evidence: str, evidence_type: str = "feedback") -> bool:
        """Record evidence for the active experiment.

        Args:
            evidence: Evidence content (text, URL, etc.)
            evidence_type: Type of evidence ('feedback', 'screenshot', 'retrospective')

        Returns:
            True if successful.
        """
        exp = self.get_active_experiment()
        if not exp:
            logger.warning("No active experiment to record evidence for")
            return False

        exp_id = exp.get("id")
        current_evidence = exp.get("evidence", {})

        if evidence_type == "screenshot":
            screenshots = current_evidence.get("screenshots", [])
            screenshots.append(evidence)
            current_evidence["screenshots"] = screenshots
        elif evidence_type == "retrospective":
            current_evidence["retrospective"] = evidence
        else:  # feedback
            feedback = current_evidence.get("feedback", [])
            feedback.append(evidence)
            current_evidence["feedback"] = feedback

        return self.store.update_item(exp_id, {"evidence": current_evidence})

    def complete_experiment(self, exp_id: str = None) -> bool:
        """Mark experiment as completed.

        Args:
            exp_id: Experiment ID. Uses active experiment if not provided.

        Returns:
            True if successful.
        """
        if not exp_id:
            exp = self.get_active_experiment()
            if exp:
                exp_id = exp.get("id")

        if not exp_id:
            return False

        # Update experiment status
        success = self.store.update_status(exp_id, ExperimentStatus.COMPLETED.value)

        # Also update the related idea
        exp = self.store.read_experiments()
        for e in exp:
            if e.get("id") == exp_id:
                idea_id = e.get("idea_id")
                if idea_id:
                    self.store.update_status(idea_id, IdeaStatus.COMPLETED.value)
                break

        return success

    def fail_experiment(self, exp_id: str = None, reason: str = "") -> bool:
        """Mark experiment as failed.

        Args:
            exp_id: Experiment ID.
            reason: Reason for failure.

        Returns:
            True if successful.
        """
        if not exp_id:
            exp = self.get_active_experiment()
            if exp:
                exp_id = exp.get("id")

        if not exp_id:
            return False

        updates = {
            "status": ExperimentStatus.FAILED.value,
            "failure_reason": reason
        }
        return self.store.update_item(exp_id, updates)

    # ==================== Downgrade ====================

    def trigger_downgrade(self, exp_id: str = None) -> Optional[Dict[str, Any]]:
        """Trigger downgrade for an experiment.

        Switches the experiment to its lite/5-minute version.

        Args:
            exp_id: Experiment ID. Uses active experiment if not provided.

        Returns:
            Updated experiment dictionary or None.
        """
        if not exp_id:
            exp = self.get_active_experiment()
            if not exp:
                return None
            exp_id = exp.get("id")
        else:
            experiments = self.store.read_experiments()
            exp = next((e for e in experiments if e.get("id") == exp_id), None)

        if not exp:
            return None

        # Check if already downgraded
        if exp.get("downgrade_level") == DowngradeLevel.LITE.value:
            logger.info("Experiment already downgraded")
            return exp

        # Apply downgrade
        downgrade_version = exp.get("downgrade_version", {})
        updates = {
            "downgrade_level": DowngradeLevel.LITE.value,
            "estimated_time": 5,
            "tasks": [{
                "id": "task-lite-001",
                "description": downgrade_version.get("task", "完成5分钟最小验证"),
                "time_estimate": 5,
                "deliverable": downgrade_version.get("expected_evidence", "提交验证截图"),
                "status": "pending"
            }]
        }

        if self.store.update_item(exp_id, updates):
            # Re-read the experiment
            experiments = self.store.read_experiments()
            return next((e for e in experiments if e.get("id") == exp_id), None)

        return None

    def check_evidence_timeout(self, exp_id: str = None, timeout_hours: int = 24) -> bool:
        """Check if experiment has timed out waiting for evidence.

        Args:
            exp_id: Experiment ID.
            timeout_hours: Hours before auto-downgrade.

        Returns:
            True if timed out.
        """
        if not exp_id:
            exp = self.get_active_experiment()
        else:
            experiments = self.store.read_experiments()
            exp = next((e for e in experiments if e.get("id") == exp_id), None)

        if not exp:
            return False

        if exp.get("status") != ExperimentStatus.AWAITING_EVIDENCE.value:
            return False

        # Check time since last update
        updated = exp.get("updated") or exp.get("created")
        if not updated:
            return False

        try:
            updated_time = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            now = datetime.now(updated_time.tzinfo) if updated_time.tzinfo else datetime.now()
            hours_elapsed = (now - updated_time).total_seconds() / 3600
            return hours_elapsed >= timeout_hours
        except Exception:
            return False

    # ==================== Archive ====================

    def archive_completed(self) -> int:
        """Archive all completed experiments and their related ideas.

        Returns:
            Number of items archived.
        """
        count = 0

        # Archive completed experiments
        experiments = self.store.read_experiments(status=ExperimentStatus.COMPLETED.value)
        for exp in experiments:
            exp_id = exp.get("id")
            if exp_id and self.store.archive_item(exp_id):
                count += 1

                # Also archive related idea
                idea_id = exp.get("idea_id")
                if idea_id:
                    self.store.archive_item(idea_id)
                    count += 1

        # Archive processed cards
        cards = self.store.get_cards_by_status(CardStatus.PROCESSED.value)
        for card in cards:
            card_id = card.get("id")
            if card_id and self.store.archive_item(card_id):
                count += 1

        return count

    # ==================== Pipeline State Query ====================

    def get_pipeline_state(self) -> Dict[str, Any]:
        """Get the current state of the pipeline.

        Returns:
            Dictionary with current pipeline state.
        """
        pending_cards = self.get_pending_cards()
        selected_cards = self.get_selected_cards()
        top3_ideas = self.get_top3_ideas()
        confirmed_idea = self.get_confirmed_idea()
        active_experiment = self.get_active_experiment()

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pending_cards_count": len(pending_cards),
            "selected_cards_count": len(selected_cards),
            "top3_ideas": [{"id": i.get("id"), "title": i.get("title")} for i in top3_ideas],
            "confirmed_idea": {
                "id": confirmed_idea.get("id"),
                "title": confirmed_idea.get("title")
            } if confirmed_idea else None,
            "active_experiment": {
                "id": active_experiment.get("id"),
                "status": active_experiment.get("status"),
                "idea_title": active_experiment.get("idea_title")
            } if active_experiment else None,
            "wip_available": not self.has_active_experiment()
        }

    def record_morning_push(self, cards: List[Dict], ideas: List[Dict]) -> None:
        """Record that morning push was sent.

        Can be used for analytics/tracking.

        Args:
            cards: Cards that were pushed.
            ideas: Ideas that were pushed.
        """
        # TODO: Implement push history tracking if needed
        logger.info(f"Morning push recorded: {len(cards)} cards, {len(ideas)} ideas")

    def record_afternoon_push(self, experiment: Dict) -> None:
        """Record that afternoon push was sent."""
        logger.info(f"Afternoon push recorded: {experiment.get('idea_title', 'Unknown')}")

    def record_evening_push(self, experiment: Dict) -> None:
        """Record that evening push was sent."""
        logger.info(f"Evening push recorded: {experiment.get('idea_title', 'Unknown')}")
