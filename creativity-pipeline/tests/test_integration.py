"""End-to-end integration tests for the creativity pipeline.

CP5: Validates the complete flow:
Morning → Card Selection → Afternoon → Execution → Evening → Evidence
"""
import pytest
import tempfile
import os
from datetime import datetime

from src.state.obsidian_store import ObsidianStore
from src.state.state_machine import PipelineStateMachine
from src.state.schemas import CardStatus, IdeaStatus, ExperimentStatus


class TestEndToEndFlow:
    """Test the complete pipeline flow from morning to evening."""

    @pytest.fixture
    def temp_vault(self):
        """Create a temporary vault for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ObsidianStore(tmpdir)
            yield store

    @pytest.fixture
    def pipeline(self, temp_vault):
        """Create a pipeline with temporary storage."""
        return PipelineStateMachine(store=temp_vault)

    def test_morning_to_afternoon_flow(self, pipeline, temp_vault):
        """Test flow from morning push to afternoon experiment creation."""
        # === Morning: Cards are generated ===
        # Simulate InputFeederAgent creating cards
        card1 = {
            "title": "AI价格战",
            "category": "change",
            "industry": "tech/ai",
            "keywords": ["AI", "降价", "大模型"],
            "content": "多家大模型厂商开始降价",
            "analysis": {
                "change": "API价格下降50%",
                "affected": "AI创业者",
                "opportunity": "降低AI应用成本"
            },
            "heat_score": 8500,
        }
        card2 = {
            "title": "短视频带货增长",
            "category": "opportunity",
            "industry": "social",
            "keywords": ["短视频", "电商", "直播"],
            "content": "短视频带货GMV同比增长200%",
            "heat_score": 7200,
        }

        temp_vault.write_card(card1)
        temp_vault.write_card(card2)

        # Verify cards are pending
        pending = pipeline.get_pending_cards()
        assert len(pending) == 2

        # === User selects cards ===
        selected = pipeline.record_selection([1])  # Select first card
        assert len(selected) == 1
        assert selected[0]["title"] == "AI价格战"

        # Verify card status changed
        pending_after = pipeline.get_pending_cards()
        selected_cards = pipeline.get_selected_cards()
        assert len(pending_after) == 1
        assert len(selected_cards) == 1

    def test_idea_generation_and_confirmation(self, pipeline, temp_vault):
        """Test idea generation and top1 confirmation flow."""
        # === IdeaFactoryAgent generates ideas ===
        idea1 = {
            "title": "AI成本计算器",
            "one_liner": "输入用量,输出各家成本对比",
            "target_user": "考虑使用大模型的创业者",
            "problem": "不知道选哪家大模型最划算",
            "unique_angle": "实时价格对比+场景推荐",
            "mvp_time": 30,
            "scores": {"feasibility": 9, "market": 7, "personal_fit": 8, "uniqueness": 6, "total": 30},
            "status": "top3",
        }
        idea2 = {
            "title": "周报自动生成器",
            "one_liner": "从日报聚合周报,一键生成",
            "target_user": "每周写周报的打工人",
            "mvp_time": 45,
            "scores": {"feasibility": 8, "market": 8, "personal_fit": 7, "uniqueness": 5, "total": 28},
            "status": "top3",
        }
        idea3 = {
            "title": "代码Review助手",
            "one_liner": "PR提交后自动生成review建议",
            "target_user": "软件开发团队",
            "mvp_time": 60,
            "scores": {"feasibility": 7, "market": 7, "personal_fit": 9, "uniqueness": 7, "total": 30},
            "status": "top3",
        }

        temp_vault.write_idea(idea1)
        temp_vault.write_idea(idea2)
        temp_vault.write_idea(idea3)

        # Verify top3 ideas
        top3 = pipeline.get_top3_ideas()
        assert len(top3) == 3

        # === User confirms top1 ===
        confirmed = pipeline.confirm_top1(1)  # Confirm first idea
        assert confirmed is not None
        assert confirmed["title"] == "AI成本计算器"

        # Verify confirmed idea
        confirmed_idea = pipeline.get_confirmed_idea()
        assert confirmed_idea is not None
        assert confirmed_idea["title"] == "AI成本计算器"

    def test_experiment_creation_and_wip_rule(self, pipeline, temp_vault):
        """Test experiment creation and WIP=1 rule enforcement."""
        # Create and confirm an idea first
        idea = {
            "title": "测试创意",
            "one_liner": "测试用创意",
            "status": "confirmed",
        }
        temp_vault.write_idea(idea)

        # Get the confirmed idea
        ideas = temp_vault.read_ideas(status="confirmed")
        confirmed_idea = ideas[0] if ideas else {"id": "test-idea", "title": "测试创意"}

        # === Afternoon: Create experiment ===
        tasks_data = {
            "estimated_time": 45,
            "tasks": [
                {"id": "task-001", "description": "创建项目结构", "time_estimate": 10, "status": "pending"},
                {"id": "task-002", "description": "实现核心功能", "time_estimate": 20, "status": "pending"},
                {"id": "task-003", "description": "部署并分享", "time_estimate": 15, "status": "pending"},
            ],
            "three_person_rule": {
                "target_profiles": [
                    {"type": "目标用户", "where_to_find": "社交媒体"},
                ]
            }
        }

        # Verify no active experiment initially
        assert not pipeline.has_active_experiment()

        # Create experiment
        experiment = pipeline.create_experiment(confirmed_idea, tasks_data)
        assert experiment is not None
        assert experiment["idea_title"] == "测试创意"
        assert len(experiment["tasks"]) == 3

        # Verify WIP=1 rule
        assert pipeline.has_active_experiment()

        # Attempt to create another experiment should fail
        second_experiment = pipeline.create_experiment(confirmed_idea, tasks_data)
        assert second_experiment is None  # WIP=1 violated

    def test_evidence_and_completion_flow(self, pipeline, temp_vault):
        """Test evening evidence collection and experiment completion."""
        # Setup: Create an active experiment
        idea = {"id": "idea-test", "title": "测试创意", "status": "confirmed"}
        temp_vault.write_idea(idea)

        experiment = pipeline.create_experiment(
            idea,
            {"estimated_time": 30, "tasks": [{"id": "t1", "description": "测试任务"}]}
        )

        # Start the experiment
        pipeline.start_experiment()

        # === Evening: Set awaiting evidence ===
        active_exp = pipeline.get_active_experiment()
        assert active_exp is not None

        exp_id = active_exp["id"]
        pipeline.set_awaiting_evidence(exp_id)

        # Verify status
        updated_exp = pipeline.get_active_experiment()
        assert updated_exp["status"] == ExperimentStatus.AWAITING_EVIDENCE.value

        # === User submits evidence ===
        pipeline.record_evidence("用户反馈：很好用！", "feedback")
        pipeline.record_evidence("https://example.com/screenshot.png", "screenshot")
        pipeline.record_evidence("学到了快速验证的重要性", "retrospective")

        # Complete experiment
        pipeline.complete_experiment(exp_id)

        # Verify completion - no more active experiment
        assert not pipeline.has_active_experiment()

    def test_downgrade_flow(self, pipeline, temp_vault):
        """Test the downgrade mechanism when user can't complete normal tasks."""
        # Create experiment
        idea = {"id": "idea-down", "title": "降级测试创意", "status": "confirmed"}
        temp_vault.write_idea(idea)

        experiment = pipeline.create_experiment(
            idea,
            {
                "estimated_time": 45,
                "tasks": [
                    {"id": "t1", "description": "复杂任务1", "time_estimate": 20},
                    {"id": "t2", "description": "复杂任务2", "time_estimate": 25},
                ],
                "downgrade_version": {
                    "task": "发1条推文询问用户需求",
                    "expected_evidence": "推文截图"
                }
            }
        )

        # Trigger downgrade
        exp = pipeline.get_active_experiment()
        downgraded = pipeline.trigger_downgrade(exp["id"])

        assert downgraded is not None
        assert downgraded["downgrade_level"] == "lite"
        assert downgraded["estimated_time"] == 5
        assert len(downgraded["tasks"]) == 1

    def test_complete_daily_cycle(self, pipeline, temp_vault):
        """Test a complete daily cycle: morning → afternoon → evening."""
        # === Phase 1: Morning - Input Cards ===
        for i in range(5):
            temp_vault.write_card({
                "title": f"新闻{i+1}",
                "category": "change",
                "heat_score": 1000 * (5-i),
            })

        # User selects 2 cards
        pipeline.record_selection([1, 3])
        assert len(pipeline.get_selected_cards()) == 2

        # === Phase 2: Ideas Generated (simulated) ===
        for i in range(3):
            temp_vault.write_idea({
                "title": f"创意{i+1}",
                "one_liner": f"创意{i+1}的描述",
                "mvp_time": 30 + i*15,
                "status": "top3",
            })

        # User confirms top1
        confirmed = pipeline.confirm_top1(1)
        assert confirmed["title"] == "创意1"

        # === Phase 3: Afternoon - Experiment ===
        experiment = pipeline.create_experiment(
            confirmed,
            {
                "estimated_time": 30,
                "tasks": [
                    {"id": "t1", "description": "任务1", "time_estimate": 15},
                    {"id": "t2", "description": "任务2", "time_estimate": 15},
                ]
            }
        )
        assert experiment is not None

        # Start working
        pipeline.start_experiment()

        # === Phase 4: Evening - Evidence ===
        pipeline.set_awaiting_evidence()

        # Submit evidence
        pipeline.record_evidence("用户说很有用", "feedback")

        # Complete
        pipeline.complete_experiment()

        # === Verify Final State ===
        state = pipeline.get_pipeline_state()
        assert state["wip_available"] is True
        assert state["active_experiment"] is None

        # Archive completed items
        archived_count = pipeline.archive_completed()
        assert archived_count > 0


class TestMainEntryIntegration:
    """Test main.py entry point integration."""

    def test_main_status_command(self):
        """Test that --status command runs without error."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "src.main", "--status"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # Should output status information
        assert "Creativity Pipeline Status" in result.stdout
        assert "Date:" in result.stdout
        assert "WIP Available:" in result.stdout
