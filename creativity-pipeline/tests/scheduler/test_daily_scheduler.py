"""Tests for DailyScheduler."""
import pytest
from datetime import time, datetime
from unittest.mock import AsyncMock, patch

from src.scheduler.daily_scheduler import DailyScheduler, TouchPoint, generate_crontab


class TestTouchPointTimes:
    """Tests for touch point time configuration."""

    def test_default_times(self):
        """Test scheduler uses default times when no env vars set."""
        scheduler = DailyScheduler()

        assert scheduler.touch_points[TouchPoint.MORNING] == time(9, 0)
        assert scheduler.touch_points[TouchPoint.AFTERNOON] == time(14, 0)
        assert scheduler.touch_points[TouchPoint.EVENING] == time(21, 30)

    def test_custom_times(self):
        """Test scheduler accepts custom times."""
        custom_times = {
            TouchPoint.MORNING: time(8, 0),
            TouchPoint.AFTERNOON: time(13, 0),
            TouchPoint.EVENING: time(20, 0),
        }
        scheduler = DailyScheduler(touch_point_times=custom_times)

        assert scheduler.touch_points[TouchPoint.MORNING] == time(8, 0)
        assert scheduler.touch_points[TouchPoint.AFTERNOON] == time(13, 0)
        assert scheduler.touch_points[TouchPoint.EVENING] == time(20, 0)

    def test_load_times_from_env(self, monkeypatch):
        """Test scheduler loads times from environment variables."""
        monkeypatch.setenv("MORNING_PUSH_TIME", "08:30")
        monkeypatch.setenv("AFTERNOON_PUSH_TIME", "15:00")
        monkeypatch.setenv("EVENING_PUSH_TIME", "22:00")

        scheduler = DailyScheduler()

        assert scheduler.touch_points[TouchPoint.MORNING] == time(8, 30)
        assert scheduler.touch_points[TouchPoint.AFTERNOON] == time(15, 0)
        assert scheduler.touch_points[TouchPoint.EVENING] == time(22, 0)

    def test_invalid_env_time_uses_default(self, monkeypatch):
        """Test invalid env time falls back to default."""
        monkeypatch.setenv("MORNING_PUSH_TIME", "invalid")

        scheduler = DailyScheduler()

        assert scheduler.touch_points[TouchPoint.MORNING] == time(9, 0)

    def test_set_time(self):
        """Test set_time method."""
        scheduler = DailyScheduler()
        scheduler.set_time(TouchPoint.MORNING, time(7, 0))

        assert scheduler.touch_points[TouchPoint.MORNING] == time(7, 0)


class TestIsWithinWindow:
    """Tests for _is_within_window method."""

    def test_within_window(self):
        """Test time within window returns True."""
        scheduler = DailyScheduler()

        current = time(9, 0)
        target = time(9, 0)
        assert scheduler._is_within_window(current, target) is True

    def test_just_outside_window(self):
        """Test time just outside window returns False."""
        scheduler = DailyScheduler()

        current = time(9, 2)
        target = time(9, 0)
        assert scheduler._is_within_window(current, target) is False

    def test_custom_window_size(self):
        """Test custom window size."""
        scheduler = DailyScheduler()

        current = time(9, 3)
        target = time(9, 0)
        assert scheduler._is_within_window(current, target, window_minutes=5) is True


class TestShouldTrigger:
    """Tests for _should_trigger method."""

    def test_should_trigger_when_in_window(self):
        """Test trigger returns True when in window and not already triggered."""
        scheduler = DailyScheduler()
        scheduler.touch_points[TouchPoint.MORNING] = datetime.now().time()

        # First call should trigger
        with patch.object(scheduler, '_is_within_window', return_value=True):
            result = scheduler._should_trigger(TouchPoint.MORNING)
            assert result is True

    def test_should_not_trigger_twice_same_day(self):
        """Test trigger returns False on second call same day."""
        scheduler = DailyScheduler()
        scheduler.touch_points[TouchPoint.MORNING] = datetime.now().time()

        # First call
        with patch.object(scheduler, '_is_within_window', return_value=True):
            scheduler._should_trigger(TouchPoint.MORNING)

        # Second call should not trigger
        with patch.object(scheduler, '_is_within_window', return_value=True):
            result = scheduler._should_trigger(TouchPoint.MORNING)
            assert result is False

    def test_should_not_trigger_outside_window(self):
        """Test trigger returns False when outside window."""
        scheduler = DailyScheduler()

        with patch.object(scheduler, '_is_within_window', return_value=False):
            result = scheduler._should_trigger(TouchPoint.MORNING)
            assert result is False


class TestRunTouchPoint:
    """Tests for run_touch_point method."""

    @pytest.mark.asyncio
    async def test_run_with_handler(self):
        """Test run_touch_point executes handler."""
        handler = AsyncMock()
        scheduler = DailyScheduler(morning_handler=handler)

        result = await scheduler.run_touch_point(TouchPoint.MORNING)

        assert result is True
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_without_handler(self):
        """Test run_touch_point returns False when no handler."""
        scheduler = DailyScheduler()

        result = await scheduler.run_touch_point(TouchPoint.MORNING)

        assert result is False

    @pytest.mark.asyncio
    async def test_run_with_handler_exception(self):
        """Test run_touch_point handles exceptions."""
        handler = AsyncMock(side_effect=Exception("Test error"))
        scheduler = DailyScheduler(morning_handler=handler)

        result = await scheduler.run_touch_point(TouchPoint.MORNING)

        assert result is False


class TestManualTriggers:
    """Tests for manual trigger methods."""

    @pytest.mark.asyncio
    async def test_trigger_morning(self):
        """Test trigger_morning calls morning handler."""
        handler = AsyncMock()
        scheduler = DailyScheduler(morning_handler=handler)

        await scheduler.trigger_morning()

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_afternoon(self):
        """Test trigger_afternoon calls afternoon handler."""
        handler = AsyncMock()
        scheduler = DailyScheduler(afternoon_handler=handler)

        await scheduler.trigger_afternoon()

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_evening(self):
        """Test trigger_evening calls evening handler."""
        handler = AsyncMock()
        scheduler = DailyScheduler(evening_handler=handler)

        await scheduler.trigger_evening()

        handler.assert_called_once()


class TestScheduleStatus:
    """Tests for schedule status methods."""

    def test_get_schedule_status(self):
        """Test get_schedule_status returns correct structure."""
        scheduler = DailyScheduler()

        status = scheduler.get_schedule_status()

        assert "date" in status
        assert "current_time" in status
        assert "touch_points" in status
        assert "next" in status

        for tp in TouchPoint:
            assert tp.value in status["touch_points"]
            assert "scheduled_time" in status["touch_points"][tp.value]
            assert "triggered" in status["touch_points"][tp.value]

    def test_get_next_touch_point_before_any(self):
        """Test get_next_touch_point returns morning before all triggers."""
        scheduler = DailyScheduler()
        # Set times to future
        scheduler.touch_points[TouchPoint.MORNING] = time(23, 58)
        scheduler.touch_points[TouchPoint.AFTERNOON] = time(23, 59)
        scheduler.touch_points[TouchPoint.EVENING] = time(23, 59)

        result = scheduler.get_next_touch_point()

        # Should return the earliest future time
        assert result is not None
        assert result[0] == TouchPoint.MORNING

    def test_is_running(self):
        """Test is_running returns correct state."""
        scheduler = DailyScheduler()

        assert scheduler.is_running() is False

        scheduler._running = True
        assert scheduler.is_running() is True

    def test_stop(self):
        """Test stop sets running to False."""
        scheduler = DailyScheduler()
        scheduler._running = True

        scheduler.stop()

        assert scheduler._running is False


class TestGenerateCrontab:
    """Tests for generate_crontab function."""

    def test_default_crontab(self):
        """Test generate_crontab with default times."""
        crontab = generate_crontab()

        assert "0 9 * * *" in crontab  # Morning 09:00
        assert "0 14 * * *" in crontab  # Afternoon 14:00
        assert "30 21 * * *" in crontab  # Evening 21:30

    def test_custom_crontab(self):
        """Test generate_crontab with custom times."""
        crontab = generate_crontab(
            morning_time=time(8, 30),
            afternoon_time=time(13, 15),
            evening_time=time(20, 45)
        )

        assert "30 8 * * *" in crontab
        assert "15 13 * * *" in crontab
        assert "45 20 * * *" in crontab

    def test_custom_command(self):
        """Test generate_crontab with custom command."""
        crontab = generate_crontab(command="python main.py")

        assert "python main.py --touch-point morning" in crontab
        assert "python main.py --touch-point afternoon" in crontab
        assert "python main.py --touch-point evening" in crontab
