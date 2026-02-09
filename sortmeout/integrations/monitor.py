"""Proactive monitoring system for SortMeOut.

Runs background checks on mail, calendar, and deadlines,
and sends macOS notifications when relevant events occur.
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Default intervals (seconds) ──
CHECK_INTERVAL_MAIL = 300  # 5 minutes
CHECK_INTERVAL_CALENDAR = 600  # 10 minutes
CHECK_INTERVAL_DEADLINES = 1800  # 30 minutes
MEETING_ALERT_MINUTES = 15  # Notify N minutes before meetings


def _send_notification(title: str, message: str, sound: bool = True):
    """Send a macOS notification."""
    import subprocess

    sound_flag = 'sound name "Glass"' if sound else ""
    script = f'display notification "{message}" with title "{title}" {sound_flag}'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
    except Exception as e:
        logger.debug(f"Notification failed: {e}")


class ProactiveMonitor:
    """Background monitor that checks integrations and sends notifications."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_mail_count: int = 0
        self._last_notified_events: set = set()  # event IDs already notified
        self._checks_enabled = {
            "mail": True,
            "calendar": True,
            "deadlines": True,
        }
        self._last_check = {
            "mail": 0.0,
            "calendar": 0.0,
            "deadlines": 0.0,
        }

    def start(self):
        """Start the background monitoring thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ProactiveMonitor")
        self._thread.start()
        logger.info("ProactiveMonitor started")

    def stop(self):
        """Stop the background monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("ProactiveMonitor stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def _run_loop(self):
        """Main monitoring loop."""
        # Wait a bit for app to fully initialize
        time.sleep(10)

        while self._running:
            now = time.time()

            try:
                if (
                    self._checks_enabled["mail"]
                    and (now - self._last_check["mail"]) >= CHECK_INTERVAL_MAIL
                ):
                    self._check_mail()
                    self._last_check["mail"] = now

                if (
                    self._checks_enabled["calendar"]
                    and (now - self._last_check["calendar"]) >= CHECK_INTERVAL_CALENDAR
                ):
                    self._check_upcoming_meetings()
                    self._last_check["calendar"] = now

                if (
                    self._checks_enabled["deadlines"]
                    and (now - self._last_check["deadlines"]) >= CHECK_INTERVAL_DEADLINES
                ):
                    self._check_deadlines()
                    self._last_check["deadlines"] = now

            except Exception as e:
                logger.debug(f"Monitor check error: {e}")

            # Sleep in small increments so we can stop quickly
            for _ in range(30):  # 30 seconds total
                if not self._running:
                    break
                time.sleep(1)

    def _check_mail(self):
        """Check for new unread emails."""
        try:
            from sortmeout.integrations.mail import MailIntegration

            mail = MailIntegration()
            count = mail.get_unread_count()

            if count > self._last_mail_count and self._last_mail_count >= 0:
                new_count = count - self._last_mail_count
                if new_count > 0 and self._last_mail_count > 0:  # Skip first check
                    # Get the newest unread emails
                    recent = mail.get_recent_emails(new_count, unread_only=True)
                    if recent:
                        first = recent[0]
                        sender = first.get("sender", "Unknown")
                        subject = first.get("subject", "(no subject)")
                        if new_count == 1:
                            _send_notification(
                                "📧 New Email",
                                f"From: {sender}\n{subject}",
                            )
                        else:
                            _send_notification(
                                f"📧 {new_count} New Emails",
                                f"Latest from: {sender}\n{subject}",
                            )

            self._last_mail_count = count

        except Exception as e:
            logger.debug(f"Mail check failed: {e}")

    def _check_upcoming_meetings(self):
        """Check for meetings starting soon and send alerts."""
        try:
            from sortmeout.integrations.calendar import CalendarIntegration

            cal = CalendarIntegration()
            events = cal.get_events_today()

            now = datetime.now()
            alert_window = timedelta(minutes=MEETING_ALERT_MINUTES)

            for event in events:
                event_id = f"{event.get('summary', '')}_{event.get('startDate', '')}"

                if event_id in self._last_notified_events:
                    continue

                # Parse start time (ISO format from calendar integration)
                start_str = event.get("startDate", "")
                if not start_str:
                    continue

                try:
                    # Calendar returns ISO format: 2026-02-09T14:00:00.000Z
                    event_time = datetime.fromisoformat(
                        start_str.replace("Z", "+00:00")
                    ).replace(tzinfo=None)

                    time_until = event_time - now
                    if timedelta(0) < time_until <= alert_window:
                        minutes_left = int(time_until.total_seconds() / 60)
                        title = event.get("summary", "Untitled Event")
                        location = event.get("location", "")
                        loc_str = f"\n📍 {location}" if location else ""

                        _send_notification(
                            f"📅 Meeting in {minutes_left} min",
                            f"{title}{loc_str}",
                        )
                        self._last_notified_events.add(event_id)

                except Exception:
                    continue

            # Clean old event IDs (from previous days)
            if len(self._last_notified_events) > 100:
                self._last_notified_events.clear()

        except Exception as e:
            logger.debug(f"Calendar check failed: {e}")

    def _check_deadlines(self):
        """Check for upcoming deadlines (today and tomorrow)."""
        try:
            from sortmeout.integrations.calendar import CalendarIntegration

            cal = CalendarIntegration()
            deadlines = cal.get_deadlines(days_ahead=2)

            if deadlines:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                urgent = [
                    d for d in deadlines
                    if d.get("startDate", "")[:10] == today_str
                ]
                if urgent:
                    names = ", ".join(d.get("summary", "?") for d in urgent[:3])
                    _send_notification(
                        f"⏰ {len(urgent)} Deadline(s) Today",
                        names,
                    )

        except Exception as e:
            logger.debug(f"Deadline check failed: {e}")


# ── Singleton accessor ──
_monitor_instance: Optional[ProactiveMonitor] = None


def get_monitor() -> ProactiveMonitor:
    """Get or create the singleton monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ProactiveMonitor()
    return _monitor_instance
