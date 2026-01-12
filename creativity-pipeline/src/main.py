"""Creativity Pipeline - Main Entry Point.

This module provides the main entry point for the creativity pipeline,
integrating all components: state management, scheduling, agents, and DingTalk.
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Core imports (always available)
from src.state import PipelineStateMachine, obsidian_store
from src.scheduler import DailyScheduler
from src.data_sources import fetch_all_sources, get_top_items

# Agent imports (requires Claude Agent SDK)
from src.agents import HAS_CLAUDE_SDK
if HAS_CLAUDE_SDK:
    from src.agents import InputFeederAgent, IdeaFactoryAgent, MVPRunnerAgent
    logger.info("Claude Agent SDK available - AI agents enabled")
else:
    InputFeederAgent = None
    IdeaFactoryAgent = None
    MVPRunnerAgent = None
    logger.warning("Claude Agent SDK not available - running in demo mode")

# DingTalk imports (requires DingTalk SDK)
from src.dingtalk import DingTalkService, HAS_REPLY
if HAS_REPLY:
    from src.dingtalk import reply_service
    logger.info("DingTalk SDK available - notifications enabled")
else:
    reply_service = None
    logger.warning("DingTalk SDK not available - notifications disabled")


# ==================== Global Instances ====================

# State machine (always available)
state_machine = PipelineStateMachine()

# Agents (initialized lazily if SDK available)
_agents: Dict[str, Any] = {}

# DingTalk service (initialized lazily if SDK available)
_dingtalk_service: Optional[DingTalkService] = None


def get_agents() -> Dict[str, Any]:
    """Get or initialize agents."""
    global _agents
    if not _agents and HAS_CLAUDE_SDK:
        _agents = {
            "input_feeder": InputFeederAgent(),
            "idea_factory": IdeaFactoryAgent(),
            "mvp_runner": MVPRunnerAgent(),
        }
        logger.info("Agents initialized")
    return _agents


def get_dingtalk_service() -> Optional[DingTalkService]:
    """Get or initialize DingTalk service."""
    global _dingtalk_service
    if _dingtalk_service is None and HAS_REPLY and reply_service:
        conversation_id = os.environ.get("DINGTALK_CONVERSATION_ID", "")
        if conversation_id:
            _dingtalk_service = DingTalkService(reply_service, conversation_id)
            logger.info("DingTalk service initialized")
        else:
            logger.warning("DINGTALK_CONVERSATION_ID not set")
    return _dingtalk_service


# ==================== Touch Point Handlers ====================

async def morning_push():
    """Morning touch point handler (09:00).

    1. Fetch news from all sources
    2. Generate input cards (via InputFeederAgent)
    3. Generate ideas from selected cards (via IdeaFactoryAgent)
    4. Send morning push via DingTalk
    """
    logger.info("Morning push starting...")

    # 1. Fetch raw news
    logger.info("Fetching news...")
    raw_news = get_top_items(limit=50, cross_platform_only=True)
    logger.info(f"Got {len(raw_news)} news items")

    # 2. Generate input cards via Agent
    agents = get_agents()
    if agents.get("input_feeder"):
        try:
            logger.info("Generating cards via InputFeederAgent...")
            card_ids = await agents["input_feeder"].process_news(raw_news[:10])
            logger.info(f"Generated {len(card_ids)} cards: {card_ids}")
        except Exception as e:
            logger.error(f"Card generation failed: {e}", exc_info=True)
    else:
        logger.warning("InputFeederAgent not available - skipping card generation")

    # 3. Generate ideas from yesterday's selected cards
    selected_cards = state_machine.get_selected_cards()
    if selected_cards and agents.get("idea_factory"):
        try:
            logger.info("Generating ideas via IdeaFactoryAgent...")
            card_ids = [c.get("id") for c in selected_cards if c.get("id")]
            idea_ids = await agents["idea_factory"].generate_ideas(card_ids, count=3)
            logger.info(f"Generated {len(idea_ids)} ideas: {idea_ids}")

            # Mark generated ideas as top3
            if idea_ids:
                state_machine.set_top3(idea_ids)
        except Exception as e:
            logger.error(f"Idea generation failed: {e}", exc_info=True)
    else:
        if not selected_cards:
            logger.info("No selected cards - skipping idea generation")
        else:
            logger.warning("IdeaFactoryAgent not available - skipping idea generation")

    # 4. Get data for push
    pending_cards = state_machine.get_pending_cards()
    top3_ideas = state_machine.get_top3_ideas()

    # 5. Send DingTalk push
    dingtalk = get_dingtalk_service()
    if dingtalk:
        try:
            await dingtalk.send_morning_push(pending_cards, top3_ideas)
            logger.info("Morning push sent via DingTalk")
        except Exception as e:
            logger.error(f"DingTalk push failed: {e}", exc_info=True)
    else:
        logger.info(f"[Demo] Morning push: {len(pending_cards)} cards, {len(top3_ideas)} ideas")

    state_machine.record_morning_push(pending_cards, top3_ideas)
    logger.info("Morning push completed")


async def afternoon_push():
    """Afternoon touch point handler (14:00).

    1. Get confirmed idea
    2. Generate experiment tasks (via MVPRunnerAgent)
    3. Create experiment
    4. Send afternoon push via DingTalk
    """
    logger.info("Afternoon push starting...")

    # Check for confirmed idea
    confirmed_idea = state_machine.get_confirmed_idea()
    if not confirmed_idea:
        logger.info("No confirmed idea found")
        dingtalk = get_dingtalk_service()
        if dingtalk:
            await dingtalk.send_message("请先在早间消息中选择一个创意（回复1/2/3）")
        return

    # Check WIP rule
    if state_machine.has_active_experiment():
        logger.info("Active experiment exists - skipping")
        return

    # Generate tasks via Agent
    agents = get_agents()
    tasks_data = None

    if agents.get("mvp_runner"):
        try:
            logger.info("Generating tasks via MVPRunnerAgent...")
            tasks_data = await agents["mvp_runner"].generate_tasks(confirmed_idea)
            logger.info(f"Generated tasks: {len(tasks_data.get('tasks', []))} tasks")
        except Exception as e:
            logger.error(f"Task generation failed: {e}", exc_info=True)

    # Use placeholder if agent not available or failed
    if not tasks_data:
        logger.warning("Using placeholder tasks")
        tasks_data = {
            "estimated_time": 45,
            "tasks": [
                {"id": "task-001", "description": "创建项目基础结构", "time_estimate": 10, "status": "pending"},
                {"id": "task-002", "description": "实现核心功能", "time_estimate": 20, "status": "pending"},
                {"id": "task-003", "description": "部署并分享给3人测试", "time_estimate": 15, "status": "pending"},
            ],
            "three_person_rule": {
                "target_profiles": [
                    {"type": "目标用户", "where_to_find": "社交媒体"},
                    {"type": "行业专家", "where_to_find": "专业社区"},
                    {"type": "潜在用户", "where_to_find": "身边朋友"},
                ],
                "recruit_script": "嗨，我在做一个小实验，想邀请你花5分钟试用一下",
                "feedback_template": "用户:\n第一反应:\n是否愿意继续使用:\n改进建议:"
            }
        }

    # Create experiment
    experiment = state_machine.create_experiment(confirmed_idea, tasks_data)

    if experiment:
        # Send DingTalk push
        dingtalk = get_dingtalk_service()
        if dingtalk:
            try:
                await dingtalk.send_afternoon_push(experiment)
                logger.info("Afternoon push sent via DingTalk")
            except Exception as e:
                logger.error(f"DingTalk push failed: {e}", exc_info=True)
        else:
            logger.info(f"[Demo] Afternoon push: experiment {experiment.get('id')}")

        state_machine.record_afternoon_push(experiment)
        logger.info(f"Created experiment: {experiment.get('id')}")
    else:
        logger.error("Failed to create experiment")

    logger.info("Afternoon push completed")


async def evening_push():
    """Evening touch point handler (21:30).

    1. Get active experiment
    2. Set to awaiting evidence
    3. Send evening push via DingTalk
    """
    logger.info("Evening push starting...")

    experiment = state_machine.get_active_experiment()
    if not experiment:
        logger.info("No active experiment - skipping")
        return

    # Set awaiting evidence
    exp_id = experiment.get("id")
    state_machine.set_awaiting_evidence(exp_id)

    # Send DingTalk push
    dingtalk = get_dingtalk_service()
    if dingtalk:
        try:
            await dingtalk.send_evening_push(experiment)
            logger.info("Evening push sent via DingTalk")
        except Exception as e:
            logger.error(f"DingTalk push failed: {e}", exc_info=True)
    else:
        logger.info(f"[Demo] Evening push: awaiting evidence for {experiment.get('idea_title')}")

    state_machine.record_evening_push(experiment)
    logger.info("Evening push completed")


# ==================== Utility Functions ====================

async def check_timeout():
    """Check for experiments that have timed out waiting for evidence."""
    logger.info("Timeout check starting...")

    experiment = state_machine.get_active_experiment()

    if experiment and state_machine.check_evidence_timeout(experiment.get("id")):
        logger.info(f"Experiment {experiment.get('id')} timed out - triggering downgrade")
        state_machine.trigger_downgrade(experiment.get("id"))

        dingtalk = get_dingtalk_service()
        if dingtalk:
            await dingtalk.send_message(
                f"⚠️ 实验「{experiment.get('idea_title')}」已超时，已自动降级为5分钟版本"
            )

    logger.info("Timeout check completed")


async def archive_completed():
    """Archive completed experiments and processed cards."""
    logger.info("Archive starting...")

    count = state_machine.archive_completed()
    logger.info(f"Archived {count} items")

    logger.info("Archive completed")


# ==================== Main Entry Points ====================

async def run_scheduler():
    """Run the scheduler in continuous mode."""
    logger.info("Starting Creativity Pipeline Scheduler...")

    scheduler = DailyScheduler(
        morning_handler=morning_push,
        afternoon_handler=afternoon_push,
        evening_handler=evening_push,
    )

    # Print schedule
    status = scheduler.get_schedule_status()
    logger.info(f"Schedule for {status['date']}:")
    for name, info in status["touch_points"].items():
        logger.info(f"  - {name}: {info['scheduled_time']}")

    await scheduler.start()


async def run_once(touch_point: Optional[str] = None):
    """Run a single touch point or all in sequence."""
    if touch_point:
        handlers = {
            "morning": morning_push,
            "afternoon": afternoon_push,
            "evening": evening_push,
        }
        handler = handlers.get(touch_point)
        if handler:
            await handler()
        else:
            logger.error(f"Unknown touch point: {touch_point}")
    else:
        logger.info("Running all touch points in sequence...")
        await morning_push()
        await afternoon_push()
        await evening_push()


def print_status():
    """Print current pipeline status."""
    status = state_machine.get_pipeline_state()
    print("=" * 50)
    print("Creativity Pipeline Status")
    print("=" * 50)
    print(f"Date:              {status['date']}")
    print(f"Pending Cards:     {status['pending_cards_count']}")
    print(f"Selected Cards:    {status['selected_cards_count']}")
    print(f"Top 3 Ideas:       {len(status['top3_ideas'])}")
    for i, idea in enumerate(status['top3_ideas'], 1):
        print(f"  {i}. {idea.get('title', 'Unknown')}")
    confirmed = status['confirmed_idea']
    print(f"Confirmed Idea:    {confirmed['title'] if confirmed else 'None'}")
    active = status['active_experiment']
    if active:
        print(f"Active Experiment: {active['idea_title']} [{active['status']}]")
    else:
        print("Active Experiment: None")
    print(f"WIP Available:     {status['wip_available']}")
    print("=" * 50)
    print(f"Claude SDK:        {'Enabled' if HAS_CLAUDE_SDK else 'Disabled'}")
    print(f"DingTalk SDK:      {'Enabled' if HAS_REPLY else 'Disabled'}")
    print("=" * 50)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Creativity Pipeline")
    parser.add_argument(
        "--mode",
        choices=["scheduler", "once"],
        default="scheduler",
        help="Run mode: scheduler (continuous) or once",
    )
    parser.add_argument(
        "--touch-point",
        choices=["morning", "afternoon", "evening"],
        help="Specific touch point to run (for --mode once)",
    )
    parser.add_argument(
        "--check-timeout",
        action="store_true",
        help="Check for timed out experiments",
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Archive completed items",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print pipeline status",
    )

    args = parser.parse_args()

    # Handle special commands
    if args.check_timeout:
        asyncio.run(check_timeout())
        return

    if args.archive:
        asyncio.run(archive_completed())
        return

    if args.status:
        print_status()
        return

    # Run main mode
    if args.mode == "scheduler":
        asyncio.run(run_scheduler())
    else:
        asyncio.run(run_once(args.touch_point))


if __name__ == "__main__":
    main()
