"""Tests for the scheduler system."""

import time
from datetime import datetime, timedelta

import pytest

from sortmeout.core.scheduler import Scheduler, ScheduledRule, ScheduleInterval


class TestScheduledRule:
    """Tests for ScheduledRule."""

    def test_create_scheduled_rule(self):
        sr = ScheduledRule(
            rule_id="test-rule-1",
            folder="~/Downloads",
            interval=ScheduleInterval.DAILY,
            name="Daily Downloads Cleanup",
        )
        assert sr.rule_id == "test-rule-1"
        assert sr.interval == ScheduleInterval.DAILY
        assert sr.enabled is True
        assert sr.run_count == 0

    def test_interval_from_string(self):
        sr = ScheduledRule(rule_id="r1", folder="/tmp", interval="hourly")
        assert sr.interval == ScheduleInterval.HOURLY

    def test_is_due_new_rule(self):
        sr = ScheduledRule(
            rule_id="r1",
            folder="/tmp",
            interval=ScheduleInterval.DAILY,
        )
        # New rules with next_run in the future should not be due yet
        # But let's force it to be due
        sr.next_run = datetime.now() - timedelta(seconds=1)
        assert sr.is_due is True

    def test_is_not_due(self):
        sr = ScheduledRule(
            rule_id="r1",
            folder="/tmp",
            interval=ScheduleInterval.DAILY,
        )
        sr.next_run = datetime.now() + timedelta(hours=23)
        assert sr.is_due is False

    def test_disabled_rule_not_due(self):
        sr = ScheduledRule(
            rule_id="r1",
            folder="/tmp",
            interval=ScheduleInterval.EVERY_5_MINUTES,
            enabled=False,
        )
        sr.next_run = datetime.now() - timedelta(hours=1)
        assert sr.is_due is False

    def test_record_run(self):
        sr = ScheduledRule(rule_id="r1", folder="/tmp", interval=ScheduleInterval.HOURLY)
        assert sr.run_count == 0
        assert sr.last_run is None

        sr.record_run()
        assert sr.run_count == 1
        assert sr.last_run is not None
        assert sr.next_run > datetime.now()

    def test_to_dict(self):
        sr = ScheduledRule(
            rule_id="r1",
            folder="/tmp/test",
            interval=ScheduleInterval.DAILY,
            name="Test Schedule",
        )
        d = sr.to_dict()
        assert d["rule_id"] == "r1"
        assert d["folder"] == "/tmp/test"
        assert d["interval"] == "daily"
        assert d["name"] == "Test Schedule"

    def test_from_dict(self):
        data = {
            "rule_id": "r1",
            "folder": "/tmp/test",
            "interval": "weekly",
            "name": "Weekly Cleanup",
            "run_count": 5,
        }
        sr = ScheduledRule.from_dict(data)
        assert sr.rule_id == "r1"
        assert sr.interval == ScheduleInterval.WEEKLY
        assert sr.run_count == 5

    def test_time_until_next(self):
        sr = ScheduledRule(rule_id="r1", folder="/tmp", interval=ScheduleInterval.DAILY)
        sr.next_run = datetime.now() + timedelta(hours=12)
        delta = sr.time_until_next
        assert delta is not None
        assert delta.total_seconds() > 0


class TestScheduler:
    """Tests for Scheduler."""

    def test_create_scheduler(self):
        s = Scheduler()
        assert not s.running
        assert len(s.schedules) == 0

    def test_add_schedule(self):
        s = Scheduler()
        sr = ScheduledRule(rule_id="r1", folder="/tmp", name="Test")
        s.add_schedule(sr)
        assert len(s.schedules) == 1

    def test_remove_schedule(self):
        s = Scheduler()
        sr = ScheduledRule(rule_id="r1", folder="/tmp")
        s.add_schedule(sr)
        assert s.remove_schedule("r1") is True
        assert len(s.schedules) == 0
        assert s.remove_schedule("nonexistent") is False

    def test_get_schedule(self):
        s = Scheduler()
        sr = ScheduledRule(rule_id="r1", folder="/tmp", name="Find Me")
        s.add_schedule(sr)
        found = s.get_schedule("r1")
        assert found is not None
        assert found.name == "Find Me"

    def test_check_and_execute(self):
        executed_rules = []

        def on_exec(schedule):
            executed_rules.append(schedule.rule_id)

        s = Scheduler(on_execute=on_exec)
        sr = ScheduledRule(rule_id="r1", folder="/tmp", interval=ScheduleInterval.EVERY_5_MINUTES)
        sr.next_run = datetime.now() - timedelta(minutes=1)  # Make it due
        s.add_schedule(sr)

        result = s.check_and_execute()
        assert len(result) == 1
        assert "r1" in executed_rules
        assert sr.run_count == 1

    def test_skip_not_due(self):
        executed_rules = []

        def on_exec(schedule):
            executed_rules.append(schedule.rule_id)

        s = Scheduler(on_execute=on_exec)
        sr = ScheduledRule(rule_id="r1", folder="/tmp", interval=ScheduleInterval.DAILY)
        sr.next_run = datetime.now() + timedelta(hours=23)
        s.add_schedule(sr)

        result = s.check_and_execute()
        assert len(result) == 0
        assert len(executed_rules) == 0

    def test_get_status(self):
        s = Scheduler()
        sr = ScheduledRule(rule_id="r1", folder="/tmp", name="Test", interval=ScheduleInterval.HOURLY)
        s.add_schedule(sr)

        status = s.get_status()
        assert status["running"] is False
        assert status["schedule_count"] == 1
        assert len(status["schedules"]) == 1
        assert status["schedules"][0]["name"] == "Test"

    def test_export_import_schedules(self):
        s = Scheduler()
        s.add_schedule(ScheduledRule(rule_id="r1", folder="/tmp", name="Rule 1", interval=ScheduleInterval.DAILY))
        s.add_schedule(ScheduledRule(rule_id="r2", folder="/home", name="Rule 2", interval=ScheduleInterval.WEEKLY))

        exported = s.export_schedules()
        assert len(exported) == 2

        s2 = Scheduler()
        count = s2.import_schedules(exported)
        assert count == 2
        assert len(s2.schedules) == 2

    def test_start_stop(self):
        s = Scheduler(check_interval=1)
        assert not s.running
        s.start()
        assert s.running
        s.stop()
        assert not s.running
