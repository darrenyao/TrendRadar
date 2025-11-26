"""
Twitter Scheduler - 早中晚定时调度模块

功能：
- 配置早中晚三个推送时间点
- 检查是否到达推送时间
- 管理推送状态
"""

import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional

import pytz


class PushPeriod(Enum):
    """推送时段"""

    MORNING = "morning"  # 早间
    NOON = "noon"  # 午间
    EVENING = "evening"  # 晚间


@dataclass
class PushScheduleConfig:
    """推送时间配置"""

    morning_time: time  # 早间推送时间
    noon_time: time  # 午间推送时间
    evening_time: time  # 晚间推送时间
    tolerance_minutes: int = 30  # 容差时间（分钟）


class TwitterScheduler:
    """
    Twitter推送调度器

    管理早中晚三次推送的时间检查和调度

    使用方法:
        scheduler = TwitterScheduler()
        period = scheduler.get_current_period()
        if period and scheduler.should_push(period):
            # 执行推送
            scheduler.mark_pushed(period)
    """

    # 默认推送时间配置
    DEFAULT_MORNING_TIME = time(8, 0)  # 早上8点
    DEFAULT_NOON_TIME = time(12, 0)  # 中午12点
    DEFAULT_EVENING_TIME = time(20, 0)  # 晚上8点

    def __init__(
        self,
        config: PushScheduleConfig = None,
        timezone: str = "Asia/Shanghai",
        storage=None,
    ):
        """
        初始化调度器

        Args:
            config: 推送时间配置
            timezone: 时区
            storage: 存储管理器（用于记录推送状态）
        """
        self.timezone = pytz.timezone(timezone)
        self.storage = storage

        # 从环境变量或配置加载推送时间
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()

        # 推送状态缓存（内存中）
        self._push_cache: dict[str, datetime] = {}

    def _load_config_from_env(self) -> PushScheduleConfig:
        """从环境变量加载配置"""
        morning = self._parse_time_env(
            "TWITTER_PUSH_MORNING", self.DEFAULT_MORNING_TIME
        )
        noon = self._parse_time_env("TWITTER_PUSH_NOON", self.DEFAULT_NOON_TIME)
        evening = self._parse_time_env(
            "TWITTER_PUSH_EVENING", self.DEFAULT_EVENING_TIME
        )
        tolerance = int(os.getenv("TWITTER_PUSH_TOLERANCE", "30"))

        return PushScheduleConfig(
            morning_time=morning,
            noon_time=noon,
            evening_time=evening,
            tolerance_minutes=tolerance,
        )

    def _parse_time_env(self, env_key: str, default: time) -> time:
        """解析环境变量中的时间"""
        time_str = os.getenv(env_key, "")
        if not time_str:
            return default

        try:
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return time(hour, minute)
        except (ValueError, IndexError):
            print(f"[警告] 无法解析时间 {env_key}={time_str}，使用默认值")
            return default

    def get_now(self) -> datetime:
        """获取当前时间（带时区）"""
        return datetime.now(self.timezone)

    def get_current_period(self) -> Optional[PushPeriod]:
        """
        获取当前时段

        Returns:
            当前应该推送的时段，如果不在任何推送时段则返回None
        """
        now = self.get_now()
        current_time = now.time()

        # 检查是否在各时段的容差范围内
        for period, schedule_time in [
            (PushPeriod.MORNING, self.config.morning_time),
            (PushPeriod.NOON, self.config.noon_time),
            (PushPeriod.EVENING, self.config.evening_time),
        ]:
            if self._is_in_time_range(current_time, schedule_time):
                return period

        return None

    def _is_in_time_range(self, current: time, target: time) -> bool:
        """检查当前时间是否在目标时间的容差范围内"""
        # 转换为分钟数进行比较
        current_minutes = current.hour * 60 + current.minute
        target_minutes = target.hour * 60 + target.minute

        diff = abs(current_minutes - target_minutes)
        # 处理跨午夜的情况
        diff = min(diff, 24 * 60 - diff)

        return diff <= self.config.tolerance_minutes

    def should_push(self, period: PushPeriod) -> bool:
        """
        检查是否应该推送

        Args:
            period: 推送时段

        Returns:
            是否应该推送
        """
        now = self.get_now()
        today_str = now.strftime("%Y-%m-%d")
        cache_key = f"{today_str}_{period.value}"

        # 检查内存缓存
        if cache_key in self._push_cache:
            return False

        # 检查持久化存储
        if self.storage and self.storage.has_pushed_today(period.value):
            return False

        return True

    def mark_pushed(self, period: PushPeriod, success: bool = True) -> None:
        """
        标记已推送

        Args:
            period: 推送时段
            success: 是否成功
        """
        now = self.get_now()
        today_str = now.strftime("%Y-%m-%d")
        cache_key = f"{today_str}_{period.value}"

        # 更新内存缓存
        if success:
            self._push_cache[cache_key] = now

        # 更新持久化存储
        if self.storage:
            self.storage.record_push(period.value, success)

    def get_next_push_time(self) -> tuple[PushPeriod, datetime]:
        """
        获取下一次推送时间

        Returns:
            (时段, 时间) 元组
        """
        now = self.get_now()
        today = now.date()

        # 构建今天的推送时间列表
        schedules = [
            (
                PushPeriod.MORNING,
                datetime.combine(today, self.config.morning_time),
            ),
            (
                PushPeriod.NOON,
                datetime.combine(today, self.config.noon_time),
            ),
            (
                PushPeriod.EVENING,
                datetime.combine(today, self.config.evening_time),
            ),
        ]

        # 添加时区信息
        schedules = [(p, self.timezone.localize(t)) for p, t in schedules]

        # 找到下一个未执行的推送时间
        for period, push_time in schedules:
            if push_time > now and self.should_push(period):
                return period, push_time

        # 如果今天所有推送都已完成，返回明天早上
        tomorrow = today + timedelta(days=1)
        tomorrow_morning = datetime.combine(tomorrow, self.config.morning_time)
        return PushPeriod.MORNING, self.timezone.localize(tomorrow_morning)

    def get_period_display_name(self, period: PushPeriod) -> str:
        """获取时段的显示名称"""
        names = {
            PushPeriod.MORNING: "早间",
            PushPeriod.NOON: "午间",
            PushPeriod.EVENING: "晚间",
        }
        return names.get(period, "")

    def get_schedule_status(self) -> dict:
        """
        获取调度状态

        Returns:
            调度状态信息
        """
        now = self.get_now()
        today_str = now.strftime("%Y-%m-%d")

        status = {
            "current_time": now.isoformat(),
            "timezone": str(self.timezone),
            "schedule": {
                "morning": self.config.morning_time.strftime("%H:%M"),
                "noon": self.config.noon_time.strftime("%H:%M"),
                "evening": self.config.evening_time.strftime("%H:%M"),
            },
            "tolerance_minutes": self.config.tolerance_minutes,
            "pushed_today": {
                "morning": not self.should_push(PushPeriod.MORNING),
                "noon": not self.should_push(PushPeriod.NOON),
                "evening": not self.should_push(PushPeriod.EVENING),
            },
            "current_period": None,
            "next_push": None,
        }

        current_period = self.get_current_period()
        if current_period:
            status["current_period"] = current_period.value

        next_period, next_time = self.get_next_push_time()
        status["next_push"] = {
            "period": next_period.value,
            "time": next_time.isoformat(),
        }

        return status

    def clear_today_cache(self) -> None:
        """清除今日推送缓存（用于测试）"""
        now = self.get_now()
        today_str = now.strftime("%Y-%m-%d")

        keys_to_remove = [k for k in self._push_cache if k.startswith(today_str)]
        for key in keys_to_remove:
            del self._push_cache[key]


class CronExpressionGenerator:
    """
    Cron表达式生成器

    根据配置生成适合早中晚推送的cron表达式
    """

    @staticmethod
    def generate_for_schedule(config: PushScheduleConfig) -> str:
        """
        生成cron表达式

        Args:
            config: 推送配置

        Returns:
            cron表达式
        """
        # 生成在三个时间点运行的cron表达式
        hours = [
            config.morning_time.hour,
            config.noon_time.hour,
            config.evening_time.hour,
        ]
        minutes = [
            config.morning_time.minute,
            config.noon_time.minute,
            config.evening_time.minute,
        ]

        # 如果分钟数都相同，可以简化表达式
        if len(set(minutes)) == 1:
            return f"{minutes[0]} {','.join(map(str, hours))} * * *"

        # 否则生成多个规则
        rules = [f"{m} {h} * * *" for m, h in zip(minutes, hours)]
        return " | ".join(rules)  # 表示多个规则

    @staticmethod
    def generate_frequent_check(interval_minutes: int = 30) -> str:
        """
        生成频繁检查的cron表达式

        用于更频繁地检查是否到达推送时间

        Args:
            interval_minutes: 检查间隔（分钟）

        Returns:
            cron表达式
        """
        if interval_minutes <= 0:
            interval_minutes = 30

        if 60 % interval_minutes == 0:
            return f"*/{interval_minutes} * * * *"
        else:
            return f"0,{interval_minutes} * * * *"


# 测试函数
def _test_scheduler():
    """测试调度器"""
    scheduler = TwitterScheduler()

    print("调度器状态:")
    status = scheduler.get_schedule_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n当前时段:", scheduler.get_current_period())

    next_period, next_time = scheduler.get_next_push_time()
    print(f"下次推送: {next_period.value} at {next_time}")

    # 测试cron生成
    cron = CronExpressionGenerator.generate_for_schedule(scheduler.config)
    print(f"\nCron表达式: {cron}")

    frequent_cron = CronExpressionGenerator.generate_frequent_check(30)
    print(f"频繁检查Cron: {frequent_cron}")


if __name__ == "__main__":
    _test_scheduler()
