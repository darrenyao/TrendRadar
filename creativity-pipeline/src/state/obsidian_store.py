"""Obsidian Markdown file storage for creativity pipeline.

Handles reading and writing Markdown files with YAML frontmatter
to an Obsidian vault directory structure.
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from .schemas import Card, Idea, Experiment, CardStatus, IdeaStatus, ExperimentStatus


class ObsidianStore:
    """Obsidian Markdown file storage.

    Manages reading and writing of Card, Idea, and Experiment files
    in an Obsidian vault with YAML frontmatter.
    """

    def __init__(self, vault_path: str = "/vault"):
        """Initialize ObsidianStore.

        Args:
            vault_path: Path to the Obsidian vault directory.
        """
        self.vault_path = Path(vault_path)
        self.cards_dir = self.vault_path / "cards"
        self.ideas_dir = self.vault_path / "ideas"
        self.experiments_dir = self.vault_path / "experiments"
        self.archive_dir = self.vault_path / "archive"

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create vault directories if they don't exist."""
        for dir_path in [self.cards_dir, self.ideas_dir, self.experiments_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    # ==================== Frontmatter Parsing ====================

    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from Markdown content.

        Args:
            content: Raw Markdown file content.

        Returns:
            Tuple of (frontmatter dict, body string).
        """
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                    return frontmatter, body
                except yaml.YAMLError:
                    pass
        return {}, content

    def _render_markdown(self, frontmatter: Dict[str, Any], body: str) -> str:
        """Render Markdown file with YAML frontmatter.

        Args:
            frontmatter: Dictionary to serialize as YAML.
            body: Markdown body content.

        Returns:
            Complete Markdown file content.
        """
        yaml_str = yaml.dump(
            frontmatter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )
        return f"---\n{yaml_str}---\n\n{body}"

    def _get_today_prefix(self) -> str:
        """Get today's date prefix in YYYY-MM-DD format."""
        return datetime.now().strftime("%Y-%m-%d")

    def _next_seq(self, type_name: str) -> str:
        """Generate next sequence number for today.

        Args:
            type_name: Type of item ('cards', 'ideas', 'experiments').

        Returns:
            Three-digit sequence number string.
        """
        today = self._get_today_prefix()
        if type_name == "cards":
            existing = list(self.cards_dir.glob(f"card-{today}*.md"))
        elif type_name == "ideas":
            existing = list(self.ideas_dir.glob(f"idea-{today}*.md"))
        else:
            existing = list(self.experiments_dir.glob(f"exp-{today}*.md"))
        return f"{len(existing) + 1:03d}"

    # ==================== Card Operations ====================

    def read_cards(self, date: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Read cards from the vault.

        Args:
            date: Date prefix to filter by (YYYY-MM-DD). Defaults to today.
            status: Status to filter by.

        Returns:
            List of card dictionaries.
        """
        date = date or self._get_today_prefix()
        cards = []

        for file_path in self.cards_dir.glob(f"card-{date}*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    frontmatter, body = self._parse_frontmatter(f.read())
                    if status is None or frontmatter.get("status") == status:
                        cards.append({
                            **frontmatter,
                            "body": body,
                            "path": str(file_path)
                        })
            except Exception as e:
                print(f"Error reading card {file_path}: {e}")

        return sorted(cards, key=lambda x: x.get("id", ""))

    def write_card(self, card: Union[Card, Dict[str, Any]]) -> str:
        """Write a card to the vault.

        Args:
            card: Card object or dictionary.

        Returns:
            Path to the written file.
        """
        if isinstance(card, Card):
            card_dict = card.to_dict()
        else:
            card_dict = card.copy()

        # Generate ID if not present
        card_id = card_dict.get("id") or f"card-{self._get_today_prefix()}-{self._next_seq('cards')}"
        card_dict["id"] = card_id
        card_dict["type"] = "card"
        card_dict["created"] = card_dict.get("created") or datetime.now().isoformat()
        card_dict["status"] = card_dict.get("status", "pending")

        # Generate body
        body = self._generate_card_body(card_dict)

        # Prepare frontmatter (exclude body-only fields)
        frontmatter = {k: v for k, v in card_dict.items() if k not in ["body", "path"]}

        content = self._render_markdown(frontmatter, body)

        file_path = self.cards_dir / f"{card_id}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def get_cards_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all cards with a specific status.

        Args:
            status: Status to filter by.

        Returns:
            List of card dictionaries.
        """
        cards = []
        for file_path in self.cards_dir.glob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    frontmatter, body = self._parse_frontmatter(f.read())
                    if frontmatter.get("status") == status:
                        cards.append({**frontmatter, "body": body, "path": str(file_path)})
            except Exception as e:
                print(f"Error reading card {file_path}: {e}")
        return cards

    def _generate_card_body(self, card: Dict[str, Any]) -> str:
        """Generate Markdown body for a card."""
        analysis = card.get("analysis", {})
        if isinstance(analysis, dict):
            change = analysis.get("change", "")
            affected = analysis.get("affected", "")
            opportunity = analysis.get("opportunity", "")
        else:
            change = affected = opportunity = ""

        return f"""# {card.get('title', 'Untitled')}

## 原始内容
{card.get('content', '')}

## 变化/痛点分析
- **变化**: {change}
- **影响群体**: {affected}
- **潜在机会**: {opportunity}
"""

    # ==================== Idea Operations ====================

    def read_ideas(self, date: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Read ideas from the vault.

        Args:
            date: Date prefix to filter by (YYYY-MM-DD). Defaults to today.
            status: Status to filter by.

        Returns:
            List of idea dictionaries.
        """
        date = date or self._get_today_prefix()
        ideas = []

        for file_path in self.ideas_dir.glob(f"idea-{date}*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    frontmatter, body = self._parse_frontmatter(f.read())
                    if status is None or frontmatter.get("status") == status:
                        ideas.append({
                            **frontmatter,
                            "body": body,
                            "path": str(file_path)
                        })
            except Exception as e:
                print(f"Error reading idea {file_path}: {e}")

        # Sort by score (total) descending
        return sorted(ideas, key=lambda x: self._get_idea_score(x), reverse=True)

    def write_idea(self, idea: Union[Idea, Dict[str, Any]]) -> str:
        """Write an idea to the vault.

        Args:
            idea: Idea object or dictionary.

        Returns:
            Path to the written file.
        """
        if isinstance(idea, Idea):
            idea_dict = idea.to_dict()
        else:
            idea_dict = idea.copy()

        # Generate ID if not present
        idea_id = idea_dict.get("id") or f"idea-{self._get_today_prefix()}-{self._next_seq('ideas')}"
        idea_dict["id"] = idea_id
        idea_dict["type"] = "idea"
        idea_dict["created"] = idea_dict.get("created") or datetime.now().isoformat()
        idea_dict["status"] = idea_dict.get("status", "candidate")

        # Generate body
        body = self._generate_idea_body(idea_dict)

        # Prepare frontmatter
        frontmatter = {k: v for k, v in idea_dict.items() if k not in ["body", "path"]}

        content = self._render_markdown(frontmatter, body)

        file_path = self.ideas_dir / f"{idea_id}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def get_ideas_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all ideas with a specific status."""
        ideas = []
        for file_path in self.ideas_dir.glob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    frontmatter, body = self._parse_frontmatter(f.read())
                    if frontmatter.get("status") == status:
                        ideas.append({**frontmatter, "body": body, "path": str(file_path)})
            except Exception as e:
                print(f"Error reading idea {file_path}: {e}")
        return sorted(ideas, key=lambda x: self._get_idea_score(x), reverse=True)

    def _get_idea_score(self, idea: Dict[str, Any]) -> int:
        """Safely extract total score from an idea."""
        scores = idea.get("scores")
        if isinstance(scores, dict):
            return scores.get("total", 0)
        return 0

    def _generate_idea_body(self, idea: Dict[str, Any]) -> str:
        """Generate Markdown body for an idea."""
        return f"""# {idea.get('title', 'Untitled')}

## 价值主张
{idea.get('one_liner', '')}

## 目标用户
{idea.get('target_user', '')}

## 解决问题
{idea.get('problem', '')}

## 差异化角度
{idea.get('unique_angle', '')}

## MVP 定义
预计时间: {idea.get('mvp_time', 30)} 分钟

## 降级版本
{idea.get('downgrade_version', '')}
"""

    # ==================== Experiment Operations ====================

    def read_experiments(self, date: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Read experiments from the vault."""
        date = date or self._get_today_prefix()
        experiments = []

        pattern = f"exp-{date}*.md" if date else "*.md"
        for file_path in self.experiments_dir.glob(pattern):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    frontmatter, body = self._parse_frontmatter(f.read())
                    if status is None or frontmatter.get("status") == status:
                        experiments.append({
                            **frontmatter,
                            "body": body,
                            "path": str(file_path)
                        })
            except Exception as e:
                print(f"Error reading experiment {file_path}: {e}")

        return sorted(experiments, key=lambda x: x.get("created", ""), reverse=True)

    def write_experiment(self, experiment: Union[Experiment, Dict[str, Any]]) -> str:
        """Write an experiment to the vault."""
        if isinstance(experiment, Experiment):
            exp_dict = experiment.to_dict()
        else:
            exp_dict = experiment.copy()

        # Generate ID if not present
        exp_id = exp_dict.get("id") or f"exp-{self._get_today_prefix()}-{self._next_seq('experiments')}"
        exp_dict["id"] = exp_id
        exp_dict["type"] = "experiment"
        exp_dict["created"] = exp_dict.get("created") or datetime.now().isoformat()
        exp_dict["status"] = exp_dict.get("status", "pending")

        # Generate body
        body = self._generate_experiment_body(exp_dict)

        # Prepare frontmatter
        frontmatter = {k: v for k, v in exp_dict.items() if k not in ["body", "path"]}

        content = self._render_markdown(frontmatter, body)

        file_path = self.experiments_dir / f"{exp_id}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def get_active_experiment(self) -> Optional[Dict[str, Any]]:
        """Get the currently active experiment (WIP=1 rule).

        Returns:
            Active experiment dictionary or None.
        """
        active_statuses = ["pending", "in_progress", "awaiting_evidence"]

        for file_path in self.experiments_dir.glob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    frontmatter, body = self._parse_frontmatter(f.read())
                    if frontmatter.get("status") in active_statuses:
                        return {**frontmatter, "body": body, "path": str(file_path)}
            except Exception as e:
                print(f"Error reading experiment {file_path}: {e}")

        return None

    def _generate_experiment_body(self, exp: Dict[str, Any]) -> str:
        """Generate Markdown body for an experiment."""
        tasks = exp.get("tasks", [])
        if tasks:
            tasks_md = "\n".join([
                f"- [ ] [{t.get('time_estimate', 10)}分钟] {t.get('description', '')}"
                for t in tasks
            ])
        else:
            tasks_md = "待定义"

        three_person = exp.get("three_person_rule", {})
        if three_person and three_person.get("target_profiles"):
            profiles_md = "\n".join([
                f"- {p.get('type', '')}: {p.get('where_to_find', '')}"
                for p in three_person.get("target_profiles", [])
            ])
        else:
            profiles_md = "待定义"

        return f"""# 实验: {exp.get('idea_title', 'Untitled')}

## 任务清单
{tasks_md}

## 三人法则
{profiles_md}

### 招募话术
```
{three_person.get('recruit_script', '待定义')}
```

### 反馈模板
```
{three_person.get('feedback_template', '待定义')}
```

## 证据区
> 请在此区域提交证据

## 复盘
待补充
"""

    # ==================== Status Updates ====================

    def update_status(self, item_id: str, new_status: str) -> bool:
        """Update the status of an item.

        Args:
            item_id: ID of the item (card-xxx, idea-xxx, exp-xxx).
            new_status: New status value.

        Returns:
            True if successful, False otherwise.
        """
        # Determine directory based on ID prefix
        if item_id.startswith("card-"):
            directory = self.cards_dir
        elif item_id.startswith("idea-"):
            directory = self.ideas_dir
        elif item_id.startswith("exp-"):
            directory = self.experiments_dir
        else:
            print(f"Unknown item type for ID: {item_id}")
            return False

        file_path = directory / f"{item_id}.md"
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = self._parse_frontmatter(f.read())

            frontmatter["status"] = new_status
            frontmatter["updated"] = datetime.now().isoformat()

            content = self._render_markdown(frontmatter, body)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"Error updating status for {item_id}: {e}")
            return False

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update multiple fields of an item.

        Args:
            item_id: ID of the item.
            updates: Dictionary of fields to update.

        Returns:
            True if successful, False otherwise.
        """
        # Determine directory
        if item_id.startswith("card-"):
            directory = self.cards_dir
        elif item_id.startswith("idea-"):
            directory = self.ideas_dir
        elif item_id.startswith("exp-"):
            directory = self.experiments_dir
        else:
            return False

        file_path = directory / f"{item_id}.md"
        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                frontmatter, body = self._parse_frontmatter(f.read())

            frontmatter.update(updates)
            frontmatter["updated"] = datetime.now().isoformat()

            content = self._render_markdown(frontmatter, body)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"Error updating item {item_id}: {e}")
            return False

    # ==================== Archive Operations ====================

    def archive_item(self, item_id: str) -> bool:
        """Move an item to the archive.

        Args:
            item_id: ID of the item to archive.

        Returns:
            True if successful, False otherwise.
        """
        # Determine source directory
        if item_id.startswith("card-"):
            source_dir = self.cards_dir
        elif item_id.startswith("idea-"):
            source_dir = self.ideas_dir
        elif item_id.startswith("exp-"):
            source_dir = self.experiments_dir
        else:
            return False

        source_path = source_dir / f"{item_id}.md"
        if not source_path.exists():
            return False

        # Create archive subdirectory by type
        archive_subdir = self.archive_dir / (item_id.split("-")[0] + "s")
        archive_subdir.mkdir(parents=True, exist_ok=True)

        dest_path = archive_subdir / f"{item_id}.md"

        try:
            # Update status before archiving
            with open(source_path, "r", encoding="utf-8") as f:
                frontmatter, body = self._parse_frontmatter(f.read())

            frontmatter["archived"] = datetime.now().isoformat()

            content = self._render_markdown(frontmatter, body)
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Remove from source
            source_path.unlink()
            return True
        except Exception as e:
            print(f"Error archiving {item_id}: {e}")
            return False

    # ==================== Query Helpers ====================

    def get_today_cards(self, status: str = None) -> List[Dict[str, Any]]:
        """Get today's cards."""
        return self.read_cards(self._get_today_prefix(), status)

    def get_today_ideas(self, status: str = None) -> List[Dict[str, Any]]:
        """Get today's ideas."""
        return self.read_ideas(self._get_today_prefix(), status)

    def get_top3_ideas(self) -> List[Dict[str, Any]]:
        """Get top 3 ideas for today."""
        return self.get_ideas_by_status("top3")[:3]

    def get_confirmed_idea(self) -> Optional[Dict[str, Any]]:
        """Get the confirmed idea for today."""
        ideas = self.get_ideas_by_status("confirmed")
        return ideas[0] if ideas else None


# Global singleton instance (lazy initialization)
_obsidian_store_instance = None


def get_obsidian_store() -> ObsidianStore:
    """Get the global ObsidianStore instance (lazy initialization)."""
    global _obsidian_store_instance
    if _obsidian_store_instance is None:
        vault_path = os.environ.get("VAULT_PATH", "./vault")
        _obsidian_store_instance = ObsidianStore(vault_path=vault_path)
    return _obsidian_store_instance


# For backwards compatibility - this will be lazily initialized
class _LazyObsidianStore:
    """Lazy proxy for ObsidianStore."""

    def __getattr__(self, name):
        return getattr(get_obsidian_store(), name)


obsidian_store = _LazyObsidianStore()
