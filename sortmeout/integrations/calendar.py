"""
macOS Calendar.app integration via AppleScript/JXA.

Capabilities:
    - List calendars
    - Get today's events / upcoming events / this week
    - Search events by keyword
    - Create new events (with time, location, notes, alerts)
    - Get deadlines and important dates
    - Check for conflicts before scheduling
    - Get daily/weekly briefing summary
"""

from __future__ import annotations

import subprocess
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


class CalendarIntegration:
    """Interface to macOS Calendar.app via JXA."""

    def _run_jxa(self, script: str) -> str:
        """Execute JXA and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("JXA error: %s", result.stderr.strip())
                return ""
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error("JXA timed out")
            return ""
        except Exception as e:
            logger.error("JXA failed: %s", e)
            return ""

    def _run_applescript(self, script: str) -> str:
        """Execute AppleScript and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("AppleScript error: %s", result.stderr.strip())
                return ""
            return result.stdout.strip()
        except Exception as e:
            logger.error("AppleScript failed: %s", e)
            return ""

    @staticmethod
    def _escape_applescript(s: str) -> str:
        """Escape a string for safe insertion into AppleScript."""
        if not s:
            return ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")

    # ──────────────────────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────────────────────

    def get_calendars(self) -> List[Dict[str, str]]:
        """List all calendars with name and color."""
        jxa_script = """
        (() => {
            const Cal = Application("Calendar");
            const cals = Cal.calendars();
            const results = cals.map(c => ({
                name: c.name(),
                description: c.description() || "",
            }));
            return JSON.stringify(results);
        })()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return []
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    def get_events_today(self) -> List[Dict[str, Any]]:
        """Get all events for today."""
        return self.get_events_range(0, 0)

    def get_events_tomorrow(self) -> List[Dict[str, Any]]:
        """Get all events for tomorrow."""
        return self.get_events_range(1, 1)

    def get_events_this_week(self) -> List[Dict[str, Any]]:
        """Get all events for the current week (Mon-Sun)."""
        today = datetime.now()
        days_since_monday = today.weekday()
        days_until_sunday = 6 - today.weekday()
        return self.get_events_range(-days_since_monday, days_until_sunday)

    def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for the next N days."""
        return self.get_events_range(0, days)

    def get_events_range(self, days_from: int, days_to: int) -> List[Dict[str, Any]]:
        """Get events within a date range (days offset from today)."""
        jxa_script = f"""
        (() => {{
            const Cal = Application("Calendar");
            const now = new Date();
            const startDate = new Date(now);
            startDate.setDate(startDate.getDate() + ({days_from}));
            startDate.setHours(0, 0, 0, 0);

            const endDate = new Date(now);
            endDate.setDate(endDate.getDate() + ({days_to}));
            endDate.setHours(23, 59, 59, 999);

            const results = [];
            const calendars = Cal.calendars();

            for (let c = 0; c < calendars.length; c++) {{
                const cal = calendars[c];
                const calName = cal.name();
                const events = cal.events.whose({{
                    _and: [
                        {{startDate: {{_greaterThan: startDate}}}},
                        {{startDate: {{_lessThan: endDate}}}}
                    ]
                }})();

                for (let i = 0; i < events.length; i++) {{
                    try {{
                        const e = events[i];
                        results.push({{
                            summary: e.summary() || "(no title)",
                            startDate: e.startDate().toISOString(),
                            endDate: e.endDate().toISOString(),
                            allDay: e.alldayEvent(),
                            location: e.location() || "",
                            notes: (e.description() || "").substring(0, 500),
                            calendar: calName,
                            url: e.url() || "",
                        }});
                    }} catch(err) {{}}
                }}
            }}

            // Sort by start date
            results.sort((a, b) => new Date(a.startDate) - new Date(b.startDate));
            return JSON.stringify(results);
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return []
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    def search_events(self, query: str, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Search events by keyword in title, location, or notes."""
        jxa_script = f"""
        (() => {{
            const Cal = Application("Calendar");
            const now = new Date();
            const endDate = new Date(now);
            endDate.setDate(endDate.getDate() + {days_ahead});

            const query = "{query}".toLowerCase();
            const results = [];
            const calendars = Cal.calendars();

            for (let c = 0; c < calendars.length; c++) {{
                const cal = calendars[c];
                const events = cal.events.whose({{
                    _and: [
                        {{startDate: {{_greaterThan: now}}}},
                        {{startDate: {{_lessThan: endDate}}}}
                    ]
                }})();

                for (let i = 0; i < events.length; i++) {{
                    try {{
                        const e = events[i];
                        const summary = (e.summary() || "").toLowerCase();
                        const location = (e.location() || "").toLowerCase();
                        const notes = (e.description() || "").toLowerCase();

                        if (summary.includes(query) || location.includes(query) || notes.includes(query)) {{
                            results.push({{
                                summary: e.summary() || "(no title)",
                                startDate: e.startDate().toISOString(),
                                endDate: e.endDate().toISOString(),
                                allDay: e.alldayEvent(),
                                location: e.location() || "",
                                notes: (e.description() || "").substring(0, 300),
                                calendar: cal.name(),
                            }});
                        }}
                    }} catch(err) {{}}
                }}
            }}

            results.sort((a, b) => new Date(a.startDate) - new Date(b.startDate));
            return JSON.stringify(results);
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return []
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    # ──────────────────────────────────────────────────────────────
    # WRITE
    # ──────────────────────────────────────────────────────────────

    def create_event(
        self,
        title: str,
        start: str,
        end: Optional[str] = None,
        calendar_name: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        all_day: bool = False,
        alert_minutes: Optional[int] = 15,
    ) -> Dict[str, Any]:
        """Create a new calendar event.

        Args:
            title: Event title
            start: ISO format datetime string (e.g. "2026-02-10T14:00:00")
            end: ISO format datetime string (defaults to 1 hour after start)
            calendar_name: Target calendar name (defaults to first calendar)
            location: Event location
            notes: Event notes/description
            all_day: Whether this is an all-day event
            alert_minutes: Minutes before event to show alert (None for no alert)
        """
        # Build properties — escape all user input
        safe_title = self._escape_applescript(title)

        if all_day:
            pass  # handled below

        location_prop = f', location:"{self._escape_applescript(location)}"' if location else ""
        notes_prop = f', description:"{self._escape_applescript(notes)}"' if notes else ""

        # Calendar selection
        cal_target = ""
        if calendar_name:
            cal_target = f'of calendar "{self._escape_applescript(calendar_name)}"'
        else:
            cal_target = "of first calendar"

        # AppleScript for event creation (more reliable for writes)
        script = f"""
        tell application "Calendar"
            set startDate to current date
            set year of startDate to {start[:4]}
            set month of startDate to {start[5:7]}
            set day of startDate to {start[8:10]}
            set hours of startDate to {start[11:13] if len(start) > 10 else 9}
            set minutes of startDate to {start[14:16] if len(start) > 13 else 0}
            set seconds of startDate to 0

            {"set endDate to startDate + (1 * hours)" if not end else f'''
            set endDate to current date
            set year of endDate to {end[:4]}
            set month of endDate to {end[5:7]}
            set day of endDate to {end[8:10]}
            set hours of endDate to {end[11:13] if len(end) > 10 else 10}
            set minutes of endDate to {end[14:16] if len(end) > 13 else 0}
            set seconds of endDate to 0'''}

            set newEvent to make new event {cal_target} with properties {{summary:"{safe_title}", start date:startDate, end date:endDate{location_prop}{notes_prop}}}

            {"" if alert_minutes is None else f'''
            tell newEvent
                make new display alarm at end of display alarms with properties {{trigger interval:-{alert_minutes}}}
            end tell'''}
        end tell
        """
        self._run_applescript(script)
        return {
            "success": True,
            "action": "created",
            "title": title,
            "start": start,
            "end": end,
            "calendar": calendar_name or "default",
        }

    def edit_event(
        self,
        event_title: str,
        new_title: Optional[str] = None,
        new_start: Optional[str] = None,
        new_end: Optional[str] = None,
        new_location: Optional[str] = None,
        new_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Edit an existing calendar event by title.

        Args:
            event_title: Current title of the event to find
            new_title: New title (optional)
            new_start: New start time ISO format (optional)
            new_end: New end time ISO format (optional)
            new_location: New location (optional)
            new_notes: New notes (optional)
        """
        # Build property updates
        updates = []
        if new_title:
            updates.append(f'set summary of targetEvent to "{new_title}"')
        if new_location:
            updates.append(f'set location of targetEvent to "{new_location}"')
        if new_notes:
            updates.append(f'set description of targetEvent to "{new_notes}"')

        start_block = ""
        if new_start and len(new_start) >= 10:
            start_block = f"""
            set newStart to current date
            set year of newStart to {new_start[:4]}
            set month of newStart to {new_start[5:7]}
            set day of newStart to {new_start[8:10]}
            set hours of newStart to {new_start[11:13] if len(new_start) > 10 else 9}
            set minutes of newStart to {new_start[14:16] if len(new_start) > 13 else 0}
            set seconds of newStart to 0
            set start date of targetEvent to newStart
            """

        end_block = ""
        if new_end and len(new_end) >= 10:
            end_block = f"""
            set newEnd to current date
            set year of newEnd to {new_end[:4]}
            set month of newEnd to {new_end[5:7]}
            set day of newEnd to {new_end[8:10]}
            set hours of newEnd to {new_end[11:13] if len(new_end) > 10 else 10}
            set minutes of newEnd to {new_end[14:16] if len(new_end) > 13 else 0}
            set seconds of newEnd to 0
            set end date of targetEvent to newEnd
            """

        updates_str = "\n            ".join(updates)

        script = f"""
        tell application "Calendar"
            set found to false
            repeat with cal in calendars
                set eventList to (events of cal whose summary is "{event_title}")
                if (count of eventList) > 0 then
                    set targetEvent to item 1 of eventList
                    {updates_str}
                    {start_block}
                    {end_block}
                    set found to true
                    exit repeat
                end if
            end repeat
            if found then
                return "ok"
            else
                return "not found"
            end if
        end tell
        """
        result = self._run_applescript(script)
        if result == "ok":
            return {"success": True, "action": "edited", "title": event_title}
        return {"error": f"Event '{event_title}' not found"}

    def delete_event(self, event_title: str) -> Dict[str, Any]:
        """Delete a calendar event by title.

        Args:
            event_title: Title of the event to delete
        """
        script = f"""
        tell application "Calendar"
            set found to false
            repeat with cal in calendars
                set eventList to (events of cal whose summary is "{event_title}")
                if (count of eventList) > 0 then
                    delete item 1 of eventList
                    set found to true
                    exit repeat
                end if
            end repeat
            if found then
                return "ok"
            else
                return "not found"
            end if
        end tell
        """
        result = self._run_applescript(script)
        if result == "ok":
            return {"success": True, "action": "deleted", "title": event_title}
        return {"error": f"Event '{event_title}' not found"}

    # ──────────────────────────────────────────────────────────────
    # ANALYSIS
    # ──────────────────────────────────────────────────────────────

    def get_deadlines(self, days_ahead: int = 14) -> List[Dict[str, Any]]:
        """Find events that look like deadlines (keywords in title/notes)."""
        events = self.get_upcoming_events(days_ahead)
        deadline_keywords = [
            "deadline",
            "due",
            "submit",
            "inlämning",
            "sista dag",
            "förfaller",
            "expires",
            "exam",
            "tenta",
            "final",
            "presentation",
            "demo",
            "launch",
            "release",
        ]
        deadlines = []
        for event in events:
            text = f"{event.get('summary', '')} {event.get('notes', '')}".lower()
            if any(kw in text for kw in deadline_keywords):
                event["is_deadline"] = True
                deadlines.append(event)
        return deadlines

    def check_conflicts(self, start: str, end: str) -> List[Dict[str, Any]]:
        """Check if a time slot has conflicting events."""
        # Get events for that day
        from datetime import datetime

        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end) if end else start_dt + timedelta(hours=1)

        today = datetime.now()
        day_offset = (start_dt.date() - today.date()).days
        events = self.get_events_range(day_offset, day_offset)

        conflicts = []
        for event in events:
            event_start = datetime.fromisoformat(event["startDate"].replace("Z", "+00:00"))
            event_end = datetime.fromisoformat(event["endDate"].replace("Z", "+00:00"))

            # Naive overlap check
            if (
                event_start.replace(tzinfo=None) < end_dt
                and event_end.replace(tzinfo=None) > start_dt
            ):
                conflicts.append(event)

        return conflicts

    def get_daily_briefing(self) -> Dict[str, Any]:
        """Get a comprehensive daily briefing for the proactive assistant."""
        today_events = self.get_events_today()
        tomorrow_events = self.get_events_tomorrow()
        deadlines = self.get_deadlines(days_ahead=7)

        return {
            "date": datetime.now().strftime("%A, %B %d %Y"),
            "today_count": len(today_events),
            "today_events": today_events,
            "tomorrow_count": len(tomorrow_events),
            "tomorrow_preview": tomorrow_events[:3],
            "upcoming_deadlines": deadlines,
            "next_event": today_events[0] if today_events else None,
            "busy_day": len(today_events) > 5,
        }
