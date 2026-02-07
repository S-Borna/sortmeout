"""
Scheduled rules system.

Allows rules to run on a schedule (daily, hourly, etc.)
instead of only being triggered by file system events.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


class ScheduleInterval(Enum):
    """Available schedule intervals."""
    EVERY_5_MINUTES = "5min"
    EVERY_15_MINUTES = "15min"
    EVERY_30_MINUTES = "30min"
    HOURLY = "hourly"
    EVERY_2_HOURS = "2hours"
    EVERY_6_HOURS = "6hours"
    EVERY_12_HOURS = "12hours"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# Interval to seconds mapping
INTERVAL_SECONDS = {
    ScheduleInterval.EVERY_5_MINUTES: 300,
    ScheduleInterval.EVERY_15_MINUTES: 900,
    ScheduleInterval.EVERY_30_MINUTES: 1800,
    ScheduleInterval.HOURLY: 3600,
    ScheduleInterval.EVERY_2_HOURS: 7200,
    ScheduleInterval.EVERY_6_HOURS: 21600,
    ScheduleInterval.EVERY_12_HOURS: 43200,
    ScheduleInterval.DAILY: 86400,
    ScheduleInterval.WEEKLY: 604800,
    ScheduleInterval.MONTHLY: 2592000,
}


@dataclass
class ScheduledRule:
    """
    A rule paired with a schedule.

    Attributes:
        rule_id: ID of the rule to execute.
        folder: Folder to scan when the schedule triggers.
        interval: How often to run.
        enabled: Whether the schedule is active.
        last_run: When the scheduled rule last ran.
        next_run: When the scheduled rule will next run.
        run_count: Number of times this scheduled rule has run.
        name: Display name for the schedule.
    """

    rule_id: str
    folder: str
    interval: ScheduleInterval = ScheduleInterval.DAILY
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    name: str = ""

    def __post_init__(self):
        if isinstance(self.interval, str):
            self.interval = ScheduleInterval(self.interval)
        if self.next_run is None:
            self._compute_next_run()

    def _compute_next_run(self):
        """Compute the next run time."""
        base = self.last_run or datetime.now()
        seconds = INTERVAL_SECONDS[self.interval]
        self.next_run = base + timedelta(seconds=seconds)

    @property
    def is_due(self) -> bool:
        """Check if this scheduled rule is due to run."""
        if not self.enabled:
            return False
        if self.next_run is None:
            return True
        return datetime.now() >= self.next_run

    @property
    def time_until_next(self) -> Optional[timedelta]:
        """Time until next run."""
        if self.next_run is None:
            return None
        delta = self.next_run - datetime.now()
        return delta if delta.total_seconds() > 0 else timedelta(0)

    def record_run(self):
        """Record that this scheduled rule has run."""
        self.last_run = datetime.now()
        self.run_count += 1
        self._compute_next_run()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_id": self.rule_id,
            "folder": self.folder,
            "interval": self.interval.value,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledRule":
        """Deserialize from dictionary."""
        last_run = None
        if data.get("last_run"):
            last_run = datetime.fromisoformat(data["last_run"])

        return cls(
            rule_id=data["rule_id"],
            folder=data["folder"],
            interval=data.get("interval", "daily"),
            enabled=data.get("enabled", True),
            last_run=last_run,
            run_count=data.get("run_count", 0),
            name=data.get("name", ""),
        )


class Scheduler:
    """
    Manages scheduled rules execution.

    Runs a background thread that checks for due schedules
    and executes them.
    """

    def __init__(
        self,
        on_execute: Optional[Callable[[ScheduledRule], None]] = None,
        check_interval: int = 60,
    ):
        """
        Initialize the scheduler.

        Args:
            on_execute: Callback when a scheduled rule is due.
                        Receives the ScheduledRule to execute.
            check_interval: How often to check for due rules (seconds).
        """
        self._schedules: List[ScheduledRule] = []
        self._on_execute = on_execute
        self._check_interval = check_interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        """Whether the scheduler is running."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def schedules(self) -> List[ScheduledRule]:
        """Get all scheduled rules."""
        with self._lock:
            return list(self._schedules)

    def add_schedule(self, schedule: ScheduledRule) -> None:
        """Add a scheduled rule."""
        with self._lock:
            self._schedules.append(schedule)
        logger.info("Added schedule: %s (every %s)", schedule.name, schedule.interval.value)

    def remove_schedule(self, rule_id: str) -> bool:
        """Remove a scheduled rule by its rule_id."""
        with self._lock:
            for i, sched in enumerate(self._schedules):
                if sched.rule_id == rule_id:
                    del self._schedules[i]
                    return True
        return False

    def get_schedule(self, rule_id: str) -> Optional[ScheduledRule]:
        """Get a scheduled rule by its rule_id."""
        with self._lock:
            for sched in self._schedules:
                if sched.rule_id == rule_id:
                    return sched
        return None

    def start(self):
        """Start the scheduler background thread."""
        if self.running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started (check every %ds)", self._check_interval)

    def stop(self):
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Scheduler stopped")

    def check_and_execute(self) -> List[ScheduledRule]:
        """
        Check all schedules and execute due ones.

        Returns:
            List of schedules that were executed.
        """
        executed = []

        with self._lock:
            for schedule in self._schedules:
                if schedule.is_due:
                    try:
                        if self._on_execute:
                            self._on_execute(schedule)
                        schedule.record_run()
                        executed.append(schedule)
                        logger.info(
                            "Executed scheduled rule: %s (run #%d)",
                            schedule.name,
                            schedule.run_count,
                        )
                    except Exception as e:
                        logger.error(
                            "Error executing scheduled rule %s: %s",
                            schedule.name,
                            e,
                        )

        return executed

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        with self._lock:
            schedules_info = []
            for s in self._schedules:
                schedules_info.append({
                    "name": s.name,
                    "rule_id": s.rule_id,
                    "folder": s.folder,
                    "interval": s.interval.value,
                    "enabled": s.enabled,
                    "last_run": s.last_run.isoformat() if s.last_run else None,
                    "next_run": s.next_run.isoformat() if s.next_run else None,
                    "is_due": s.is_due,
                    "run_count": s.run_count,
                })

        return {
            "running": self.running,
            "schedule_count": len(schedules_info),
            "schedules": schedules_info,
        }

    def export_schedules(self) -> List[Dict[str, Any]]:
        """Export all schedules as a list of dicts."""
        with self._lock:
            return [s.to_dict() for s in self._schedules]

    def import_schedules(self, data: List[Dict[str, Any]]) -> int:
        """Import schedules from a list of dicts."""
        count = 0
        for item in data:
            try:
                schedule = ScheduledRule.from_dict(item)
                self.add_schedule(schedule)
                count += 1
            except Exception as e:
                logger.error("Failed to import schedule: %s", e)
        return count

    def _run_loop(self):
        """Background thread loop."""
        while not self._stop_event.is_set():
            try:
                self.check_and_execute()
            except Exception as e:
                logger.error("Scheduler loop error: %s", e)

            self._stop_event.wait(timeout=self._check_interval)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
