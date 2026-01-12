"""Daily scheduler for creativity pipeline.

Manages the three daily touch points:
- Morning (09:00): Push input cards and top 3 ideas
- Afternoon (14:00): Push experiment tasks
- Evening (21:30): Collect evidence
"""

import asyncio
import logging
import os
from datetime import datetime, time, timedelta
from typing import Callable, Awaitable, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class TouchPoint(str, Enum):
    """Daily touch points."""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class DailyScheduler:
    """Daily scheduler for the 3-touch-point workflow.

    Triggers handlers at configured times each day:
    - Morning: 09:00 - Generate and push daily cards + ideas
    - Afternoon: 14:00 - Push experiment tasks
    - Evening: 21:30 - Collect evidence and retrospective
    """

    # Default touch point times
    DEFAULT_TOUCH_POINTS = {
        TouchPoint.MORNING: time(9, 0),
        TouchPoint.AFTERNOON: time(14, 0),
        TouchPoint.EVENING: time(21, 30),
    }

    def __init__(
        self,
        morning_handler: Callable[[], Awaitable[None]] = None,
        afternoon_handler: Callable[[], Awaitable[None]] = None,
        evening_handler: Callable[[], Awaitable[None]] = None,
        touch_point_times: Dict[TouchPoint, time] = None,
    ):
        """Initialize the scheduler.

        Args:
            morning_handler: Async function to call at morning touch point.
            afternoon_handler: Async function to call at afternoon touch point.
            evening_handler: Async function to call at evening touch point.
            touch_point_times: Custom times for touch points.
        """
        self.handlers = {
            TouchPoint.MORNING: morning_handler,
            TouchPoint.AFTERNOON: afternoon_handler,
            TouchPoint.EVENING: evening_handler,
        }

        # Load times from environment or use defaults
        self.touch_points = touch_point_times or self._load_times_from_env()

        self._running = False
        self._last_triggered: Dict[str, str] = {}  # Track last trigger date per touch point

    def _load_times_from_env(self) -> Dict[TouchPoint, time]:
        """Load touch point times from environment variables."""
        times = {}

        for tp in TouchPoint:
            env_key = f"{tp.value.upper()}_PUSH_TIME"
            env_value = os.environ.get(env_key)

            if env_value:
                try:
                    parts = env_value.split(":")
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                    times[tp] = time(hour, minute)
                except (ValueError, IndexError):
                    times[tp] = self.DEFAULT_TOUCH_POINTS[tp]
            else:
                times[tp] = self.DEFAULT_TOUCH_POINTS[tp]

        return times

    def set_handler(self, touch_point: TouchPoint, handler: Callable[[], Awaitable[None]]) -> None:
        """Set or update a handler for a touch point.

        Args:
            touch_point: The touch point to set handler for.
            handler: Async handler function.
        """
        self.handlers[touch_point] = handler

    def set_time(self, touch_point: TouchPoint, trigger_time: time) -> None:
        """Set the trigger time for a touch point.

        Args:
            touch_point: The touch point to configure.
            trigger_time: Time to trigger at.
        """
        self.touch_points[touch_point] = trigger_time

    async def run_touch_point(self, touch_point: TouchPoint) -> bool:
        """Execute a specific touch point handler.

        Args:
            touch_point: The touch point to execute.

        Returns:
            True if handler executed successfully.
        """
        handler = self.handlers.get(touch_point)
        if not handler:
            logger.warning(f"No handler for {touch_point.value}")
            return False

        try:
            logger.info(f"Executing {touch_point.value} handler at {datetime.now().strftime('%H:%M:%S')}")
            await handler()
            logger.info(f"{touch_point.value} handler completed")
            return True
        except Exception as e:
            logger.error(f"Error in {touch_point.value} handler: {e}", exc_info=True)
            return False

    def _is_within_window(self, current: time, target: time, window_minutes: int = 1) -> bool:
        """Check if current time is within window of target time.

        Args:
            current: Current time.
            target: Target time.
            window_minutes: Window size in minutes.

        Returns:
            True if within window.
        """
        current_minutes = current.hour * 60 + current.minute
        target_minutes = target.hour * 60 + target.minute
        return abs(current_minutes - target_minutes) < window_minutes

    def _should_trigger(self, touch_point: TouchPoint) -> bool:
        """Check if a touch point should be triggered.

        Prevents multiple triggers on the same day.

        Args:
            touch_point: Touch point to check.

        Returns:
            True if should trigger.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{touch_point.value}_{today}"

        if key in self._last_triggered:
            return False

        now = datetime.now().time()
        target_time = self.touch_points[touch_point]

        if self._is_within_window(now, target_time):
            self._last_triggered[key] = datetime.now().isoformat()
            return True

        return False

    async def check_and_run(self) -> Dict[str, bool]:
        """Check all touch points and run any that are due.

        Returns:
            Dictionary of touch point names to success status.
        """
        results = {}

        for touch_point in TouchPoint:
            if self._should_trigger(touch_point):
                logger.info(f"Triggering {touch_point.value} push")
                results[touch_point.value] = await self.run_touch_point(touch_point)

        return results

    async def start(self, check_interval_seconds: int = 60) -> None:
        """Start the scheduler loop.

        Args:
            check_interval_seconds: How often to check for due touch points.
        """
        self._running = True
        logger.info("Scheduler started with touch points:")
        for tp, t in self.touch_points.items():
            logger.info(f"  - {tp.value}: {t.strftime('%H:%M')}")

        while self._running:
            try:
                await self.check_and_run()
            except Exception as e:
                logger.error(f"Error in check loop: {e}", exc_info=True)

            await asyncio.sleep(check_interval_seconds)

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    # ==================== Manual Triggers ====================

    async def trigger_morning(self) -> bool:
        """Manually trigger morning touch point."""
        return await self.run_touch_point(TouchPoint.MORNING)

    async def trigger_afternoon(self) -> bool:
        """Manually trigger afternoon touch point."""
        return await self.run_touch_point(TouchPoint.AFTERNOON)

    async def trigger_evening(self) -> bool:
        """Manually trigger evening touch point."""
        return await self.run_touch_point(TouchPoint.EVENING)

    # ==================== Time Utilities ====================

    def get_next_touch_point(self) -> Optional[tuple[TouchPoint, datetime]]:
        """Get the next scheduled touch point.

        Returns:
            Tuple of (TouchPoint, datetime) or None if none scheduled today.
        """
        now = datetime.now()
        today = now.date()

        next_tp = None
        next_time = None

        for tp in TouchPoint:
            tp_time = self.touch_points[tp]
            tp_datetime = datetime.combine(today, tp_time)

            # Skip if already triggered today
            key = f"{tp.value}_{today.strftime('%Y-%m-%d')}"
            if key in self._last_triggered:
                continue

            # Skip if time has passed
            if tp_datetime <= now:
                continue

            if next_time is None or tp_datetime < next_time:
                next_tp = tp
                next_time = tp_datetime

        if next_tp:
            return (next_tp, next_time)
        return None

    def get_time_until_next(self) -> Optional[timedelta]:
        """Get time until the next touch point.

        Returns:
            Timedelta until next touch point or None.
        """
        next_tp = self.get_next_touch_point()
        if next_tp:
            return next_tp[1] - datetime.now()
        return None

    def get_schedule_status(self) -> Dict[str, Any]:
        """Get current schedule status.

        Returns:
            Dictionary with schedule information.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().time()

        status = {
            "date": today,
            "current_time": now.strftime("%H:%M:%S"),
            "touch_points": {},
            "next": None
        }

        for tp in TouchPoint:
            key = f"{tp.value}_{today}"
            tp_time = self.touch_points[tp]
            status["touch_points"][tp.value] = {
                "scheduled_time": tp_time.strftime("%H:%M"),
                "triggered": key in self._last_triggered,
                "triggered_at": self._last_triggered.get(key)
            }

        next_tp = self.get_next_touch_point()
        if next_tp:
            status["next"] = {
                "touch_point": next_tp[0].value,
                "time": next_tp[1].strftime("%H:%M"),
                "in_minutes": int((next_tp[1] - datetime.now()).total_seconds() / 60)
            }

        return status


# ==================== Supercronic Integration ====================

def generate_crontab(
    morning_time: time = None,
    afternoon_time: time = None,
    evening_time: time = None,
    command: str = "python -m src.main"
) -> str:
    """Generate crontab content for Supercronic.

    Args:
        morning_time: Morning trigger time.
        afternoon_time: Afternoon trigger time.
        evening_time: Evening trigger time.
        command: Command to execute.

    Returns:
        Crontab file content.
    """
    morning = morning_time or time(9, 0)
    afternoon = afternoon_time or time(14, 0)
    evening = evening_time or time(21, 30)

    return f"""# Creativity Pipeline Scheduler
# Generated at {datetime.now().isoformat()}

# Morning push - daily cards and top 3 ideas
{morning.minute} {morning.hour} * * * {command} --touch-point morning

# Afternoon push - experiment tasks
{afternoon.minute} {afternoon.hour} * * * {command} --touch-point afternoon

# Evening push - evidence collection
{evening.minute} {evening.hour} * * * {command} --touch-point evening
"""
