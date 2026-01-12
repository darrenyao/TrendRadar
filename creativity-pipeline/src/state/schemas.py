"""Data schemas for creativity pipeline.

Defines the data models for Card, Idea, Experiment using dataclasses.
These schemas match the YAML frontmatter format used in Obsidian files.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class CardStatus(str, Enum):
    """Status of an input card."""
    PENDING = "pending"
    SELECTED = "selected"
    PROCESSED = "processed"
    DISCARDED = "discarded"


class CardCategory(str, Enum):
    """Category of an input card."""
    CHANGE = "change"
    PAIN_POINT = "pain_point"
    OPPORTUNITY = "opportunity"


class IdeaStatus(str, Enum):
    """Status of an idea."""
    CANDIDATE = "candidate"
    TOP3 = "top3"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISCARDED = "discarded"


class ExperimentStatus(str, Enum):
    """Status of an experiment."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_EVIDENCE = "awaiting_evidence"
    COMPLETED = "completed"
    FAILED = "failed"


class DowngradeLevel(str, Enum):
    """Downgrade level for experiments."""
    NORMAL = "normal"
    LITE = "lite"


@dataclass
class CardAnalysis:
    """Analysis section of a card."""
    change: str = ""
    affected: str = ""
    opportunity: str = ""


@dataclass
class Card:
    """Input card schema.

    Represents a piece of news/trend that has been processed into
    a structured "change/pain point" card.
    """
    id: str
    title: str
    content: str = ""
    source: str = ""
    industry: str = "tech/ai"
    category: CardCategory = CardCategory.CHANGE
    keywords: List[str] = field(default_factory=list)
    status: CardStatus = CardStatus.PENDING
    heat_score: int = 0
    created: str = ""
    updated: str = ""
    analysis: CardAnalysis = field(default_factory=CardAnalysis)

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if isinstance(self.category, str):
            self.category = CardCategory(self.category)
        if isinstance(self.status, str):
            self.status = CardStatus(self.status)
        if isinstance(self.analysis, dict):
            self.analysis = CardAnalysis(**self.analysis)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "id": self.id,
            "type": "card",
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "industry": self.industry,
            "category": self.category.value if isinstance(self.category, CardCategory) else self.category,
            "keywords": self.keywords,
            "status": self.status.value if isinstance(self.status, CardStatus) else self.status,
            "heat_score": self.heat_score,
            "created": self.created,
            "updated": self.updated,
            "analysis": {
                "change": self.analysis.change,
                "affected": self.analysis.affected,
                "opportunity": self.analysis.opportunity,
            } if self.analysis else {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Card":
        """Create Card from dictionary."""
        analysis_data = data.pop("analysis", {})
        if isinstance(analysis_data, dict):
            analysis = CardAnalysis(**analysis_data)
        else:
            analysis = CardAnalysis()

        data.pop("type", None)  # Remove type field if present
        return cls(analysis=analysis, **data)


@dataclass
class IdeaScores:
    """Scoring dimensions for an idea."""
    feasibility: int = 0
    market: int = 0
    personal_fit: int = 0
    uniqueness: int = 0
    total: int = 0

    def calculate_total(self) -> int:
        """Calculate total score."""
        self.total = self.feasibility + self.market + self.personal_fit + self.uniqueness
        return self.total


@dataclass
class Idea:
    """Idea schema.

    Represents a creative idea generated from input cards.
    """
    id: str
    title: str
    one_liner: str = ""
    target_user: str = ""
    problem: str = ""
    unique_angle: str = ""
    mvp_time: int = 30  # minutes
    source_cards: List[str] = field(default_factory=list)
    scores: IdeaScores = field(default_factory=IdeaScores)
    status: IdeaStatus = IdeaStatus.CANDIDATE
    downgrade_level: DowngradeLevel = DowngradeLevel.NORMAL
    downgrade_version: str = ""
    created: str = ""
    updated: str = ""

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if isinstance(self.status, str):
            self.status = IdeaStatus(self.status)
        if isinstance(self.downgrade_level, str):
            self.downgrade_level = DowngradeLevel(self.downgrade_level)
        if isinstance(self.scores, dict):
            self.scores = IdeaScores(**self.scores)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "id": self.id,
            "type": "idea",
            "title": self.title,
            "one_liner": self.one_liner,
            "target_user": self.target_user,
            "problem": self.problem,
            "unique_angle": self.unique_angle,
            "mvp_time": self.mvp_time,
            "source_cards": self.source_cards,
            "scores": {
                "feasibility": self.scores.feasibility,
                "market": self.scores.market,
                "personal_fit": self.scores.personal_fit,
                "uniqueness": self.scores.uniqueness,
                "total": self.scores.total,
            } if self.scores else {},
            "status": self.status.value if isinstance(self.status, IdeaStatus) else self.status,
            "downgrade_level": self.downgrade_level.value if isinstance(self.downgrade_level, DowngradeLevel) else self.downgrade_level,
            "downgrade_version": self.downgrade_version,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Idea":
        """Create Idea from dictionary."""
        scores_data = data.pop("scores", {})
        if isinstance(scores_data, dict):
            scores = IdeaScores(**scores_data)
        else:
            scores = IdeaScores()

        data.pop("type", None)
        return cls(scores=scores, **data)


@dataclass
class TaskItem:
    """A single task in an experiment."""
    id: str
    description: str
    time_estimate: int = 10  # minutes
    deliverable: str = ""
    success_criteria: str = ""
    tools: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, completed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "time_estimate": self.time_estimate,
            "deliverable": self.deliverable,
            "success_criteria": self.success_criteria,
            "tools": self.tools,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskItem":
        """Create TaskItem from dictionary."""
        return cls(**data)


@dataclass
class ThreePersonRule:
    """Three person rule for experiment validation."""
    target_profiles: List[Dict[str, str]] = field(default_factory=list)
    recruit_script: str = ""
    feedback_template: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_profiles": self.target_profiles,
            "recruit_script": self.recruit_script,
            "feedback_template": self.feedback_template,
        }


@dataclass
class Evidence:
    """Evidence collected for an experiment."""
    screenshots: List[str] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)
    retrospective: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "screenshots": self.screenshots,
            "feedback": self.feedback,
            "retrospective": self.retrospective,
        }


@dataclass
class Experiment:
    """Experiment schema.

    Represents an MVP experiment for validating an idea.
    """
    id: str
    idea_id: str
    idea_title: str = ""
    downgrade_level: DowngradeLevel = DowngradeLevel.NORMAL
    estimated_time: int = 45  # minutes
    status: ExperimentStatus = ExperimentStatus.PENDING
    wip_slot: bool = True
    tasks: List[TaskItem] = field(default_factory=list)
    three_person_rule: ThreePersonRule = field(default_factory=ThreePersonRule)
    evidence: Evidence = field(default_factory=Evidence)
    downgrade_version: Dict[str, str] = field(default_factory=dict)
    created: str = ""
    updated: str = ""

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if isinstance(self.status, str):
            self.status = ExperimentStatus(self.status)
        if isinstance(self.downgrade_level, str):
            self.downgrade_level = DowngradeLevel(self.downgrade_level)

        # Convert task dicts to TaskItem objects
        if self.tasks and isinstance(self.tasks[0], dict):
            self.tasks = [TaskItem.from_dict(t) for t in self.tasks]

        if isinstance(self.three_person_rule, dict):
            self.three_person_rule = ThreePersonRule(**self.three_person_rule)

        if isinstance(self.evidence, dict):
            self.evidence = Evidence(**self.evidence)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "id": self.id,
            "type": "experiment",
            "idea_id": self.idea_id,
            "idea_title": self.idea_title,
            "downgrade_level": self.downgrade_level.value if isinstance(self.downgrade_level, DowngradeLevel) else self.downgrade_level,
            "estimated_time": self.estimated_time,
            "status": self.status.value if isinstance(self.status, ExperimentStatus) else self.status,
            "wip_slot": self.wip_slot,
            "tasks": [t.to_dict() for t in self.tasks] if self.tasks else [],
            "three_person_rule": self.three_person_rule.to_dict() if self.three_person_rule else {},
            "evidence": self.evidence.to_dict() if self.evidence else {},
            "downgrade_version": self.downgrade_version,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experiment":
        """Create Experiment from dictionary."""
        tasks_data = data.pop("tasks", [])
        tasks = [TaskItem.from_dict(t) if isinstance(t, dict) else t for t in tasks_data]

        tpr_data = data.pop("three_person_rule", {})
        three_person_rule = ThreePersonRule(**tpr_data) if isinstance(tpr_data, dict) else ThreePersonRule()

        evidence_data = data.pop("evidence", {})
        evidence = Evidence(**evidence_data) if isinstance(evidence_data, dict) else Evidence()

        data.pop("type", None)
        return cls(
            tasks=tasks,
            three_person_rule=three_person_rule,
            evidence=evidence,
            **data
        )
