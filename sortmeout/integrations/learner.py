"""Behavior learning engine for SortMeOut.

Tracks file operations performed by the user (both manual and AI-assisted),
identifies patterns, and suggests automation rules.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LEARN_FILE = os.path.expanduser("~/.config/sortmeout/learned_patterns.json")


class BehaviorLearner:
    """Learns from user file operations and suggests automation rules."""

    def __init__(self):
        self._patterns: dict = {}
        self._load()

    def _load(self):
        """Load learned patterns from disk."""
        try:
            if os.path.exists(LEARN_FILE):
                with open(LEARN_FILE, "r") as f:
                    self._patterns = json.load(f)
            else:
                self._patterns = {
                    "extension_destinations": {},  # ext -> {dest: count}
                    "name_pattern_destinations": {},  # pattern -> {dest: count}
                    "time_based_actions": [],  # [{action, time, day_of_week}]
                    "frequent_actions": {},  # action_key -> count
                    "suggested_rules": [],  # rules we've already suggested
                    "dismissed_suggestions": [],  # suggestions user rejected
                }
        except Exception as e:
            logger.debug(f"Could not load patterns: {e}")
            self._patterns = {
                "extension_destinations": {},
                "name_pattern_destinations": {},
                "time_based_actions": [],
                "frequent_actions": {},
                "suggested_rules": [],
                "dismissed_suggestions": [],
            }

    def _save(self):
        """Save learned patterns to disk."""
        try:
            os.makedirs(os.path.dirname(LEARN_FILE), exist_ok=True)
            with open(LEARN_FILE, "w") as f:
                json.dump(self._patterns, f, indent=2, default=str)
        except Exception as e:
            logger.debug(f"Could not save patterns: {e}")

    def record_action(
        self,
        action_type: str,
        source: str,
        destination: str = "",
        rule_name: str = "",
        metadata: dict | None = None,
    ):
        """Record a file operation for pattern learning.

        Args:
            action_type: move, copy, rename, trash, tag, etc.
            source: Source file path
            destination: Destination path (for move/copy)
            rule_name: Rule that triggered this (empty for manual)
            metadata: Additional context
        """
        try:
            src_path = Path(source)
            now = datetime.now()

            # Track extension → destination patterns
            if action_type in ("move", "copy") and destination:
                ext = src_path.suffix.lower()
                if ext:
                    ext_dests = self._patterns.setdefault("extension_destinations", {})
                    ext_entry = ext_dests.setdefault(ext, {})
                    dest_dir = str(
                        Path(destination).parent if Path(destination).is_file() else destination
                    )
                    ext_entry[dest_dir] = ext_entry.get(dest_dir, 0) + 1

                # Track name patterns → destination
                name = src_path.stem.lower()
                # Look for common prefixes/patterns
                for pattern_type, pattern in self._extract_name_patterns(name):
                    pat_dests = self._patterns.setdefault("name_pattern_destinations", {})
                    pat_entry = pat_dests.setdefault(f"{pattern_type}:{pattern}", {})
                    dest_dir = str(
                        Path(destination).parent if Path(destination).is_file() else destination
                    )
                    pat_entry[dest_dir] = pat_entry.get(dest_dir, 0) + 1

            # Track time-based actions
            time_actions = self._patterns.setdefault("time_based_actions", [])
            time_actions.append(
                {
                    "action": action_type,
                    "hour": now.hour,
                    "day_of_week": now.strftime("%A"),
                    "source_ext": src_path.suffix.lower(),
                    "timestamp": now.isoformat(),
                }
            )
            # Keep only last 500 entries
            if len(time_actions) > 500:
                self._patterns["time_based_actions"] = time_actions[-500:]

            # Track action frequency
            action_key = f"{action_type}:{src_path.suffix.lower()}:{destination}"
            freq = self._patterns.setdefault("frequent_actions", {})
            freq[action_key] = freq.get(action_key, 0) + 1

            self._save()

        except Exception as e:
            logger.debug(f"Could not record action: {e}")

    def _extract_name_patterns(self, name: str) -> list:
        """Extract recognizable patterns from a filename."""
        import re

        patterns = []

        # Date patterns (YYYY-MM-DD, YYYYMMDD)
        if re.search(r"\d{4}[-_]?\d{2}[-_]?\d{2}", name):
            patterns.append(("date_prefix", "has_date"))

        # Screenshot patterns
        if name.startswith("screenshot") or name.startswith("screen shot"):
            patterns.append(("prefix", "screenshot"))

        # Invoice/receipt patterns
        for kw in ["invoice", "receipt", "faktura", "kvitto", "bill"]:
            if kw in name:
                patterns.append(("keyword", kw))

        # Common prefixes (first word)
        parts = re.split(r"[-_\s]", name)
        if parts and len(parts[0]) >= 3:
            patterns.append(("prefix", parts[0]))

        return patterns

    def get_suggestions(self, min_occurrences: int = 3) -> list:
        """Get rule suggestions based on learned patterns.

        Returns a list of suggested rules with enough evidence.
        """
        suggestions = []
        dismissed = set(self._patterns.get("dismissed_suggestions", []))
        already_suggested = set(self._patterns.get("suggested_rules", []))

        # Extension-based suggestions
        ext_dests = self._patterns.get("extension_destinations", {})
        for ext, dests in ext_dests.items():
            for dest, count in dests.items():
                if count >= min_occurrences:
                    suggestion_id = f"ext:{ext}→{dest}"
                    if suggestion_id not in dismissed and suggestion_id not in already_suggested:
                        suggestions.append(
                            {
                                "id": suggestion_id,
                                "type": "extension_rule",
                                "description": f"Auto-move {ext} files to {dest}",
                                "condition": f"extension == '{ext}'",
                                "action": f"move to '{dest}'",
                                "evidence": f"You've done this {count} times",
                                "confidence": min(count / 10.0, 1.0),
                            }
                        )

        # Name-pattern suggestions
        pat_dests = self._patterns.get("name_pattern_destinations", {})
        for pattern_key, dests in pat_dests.items():
            for dest, count in dests.items():
                if count >= min_occurrences:
                    suggestion_id = f"pat:{pattern_key}→{dest}"
                    if suggestion_id not in dismissed and suggestion_id not in already_suggested:
                        pattern_type, pattern = pattern_key.split(":", 1)
                        suggestions.append(
                            {
                                "id": suggestion_id,
                                "type": "name_pattern_rule",
                                "description": f"Auto-move files with '{pattern}' pattern to {dest}",
                                "condition": f"name contains '{pattern}'",
                                "action": f"move to '{dest}'",
                                "evidence": f"You've done this {count} times",
                                "confidence": min(count / 10.0, 1.0),
                            }
                        )

        # Sort by confidence
        suggestions.sort(key=lambda s: s["confidence"], reverse=True)
        return suggestions[:10]

    def accept_suggestion(self, suggestion_id: str):
        """Mark a suggestion as accepted (rule created)."""
        suggested = self._patterns.setdefault("suggested_rules", [])
        if suggestion_id not in suggested:
            suggested.append(suggestion_id)
        self._save()

    def dismiss_suggestion(self, suggestion_id: str):
        """Mark a suggestion as dismissed (user doesn't want it)."""
        dismissed = self._patterns.setdefault("dismissed_suggestions", [])
        if suggestion_id not in dismissed:
            dismissed.append(suggestion_id)
        self._save()

    def get_stats(self) -> dict:
        """Get learning statistics."""
        return {
            "total_actions_tracked": sum(self._patterns.get("frequent_actions", {}).values()),
            "extension_patterns": len(self._patterns.get("extension_destinations", {})),
            "name_patterns": len(self._patterns.get("name_pattern_destinations", {})),
            "time_entries": len(self._patterns.get("time_based_actions", [])),
            "suggestions_available": len(self.get_suggestions()),
            "suggestions_accepted": len(self._patterns.get("suggested_rules", [])),
            "suggestions_dismissed": len(self._patterns.get("dismissed_suggestions", [])),
        }

    def get_insights(self) -> str:
        """Get human-readable insights about user behavior."""
        lines = []
        stats = self.get_stats()

        lines.append(f"📊 **Behavior Learning Stats**")
        lines.append(f"Total actions tracked: {stats['total_actions_tracked']}")
        lines.append(f"Extension patterns: {stats['extension_patterns']}")
        lines.append(f"Name patterns: {stats['name_patterns']}")

        # Most common extensions moved
        ext_dests = self._patterns.get("extension_destinations", {})
        if ext_dests:
            lines.append(f"\n**Most organized file types:**")
            sorted_exts = sorted(
                ext_dests.items(),
                key=lambda x: sum(x[1].values()),
                reverse=True,
            )
            for ext, dests in sorted_exts[:5]:
                total = sum(dests.values())
                top_dest = max(dests, key=dests.get)
                lines.append(f"  • {ext} → {top_dest} ({total} times)")

        # Time-based insights
        time_actions = self._patterns.get("time_based_actions", [])
        if time_actions:
            hours = defaultdict(int)
            for ta in time_actions:
                hours[ta.get("hour", 0)] += 1
            if hours:
                peak_hour = max(hours, key=lambda h: hours[h])
                lines.append(f"\n**Peak organizing hour:** {peak_hour}:00")

        suggestions = self.get_suggestions()
        if suggestions:
            lines.append(f"\n**💡 {len(suggestions)} rule suggestion(s) available**")
            for s in suggestions[:3]:
                lines.append(f"  • {s['description']} ({s['evidence']})")

        return "\n".join(lines)


# ── Singleton accessor ──
_learner_instance: Optional[BehaviorLearner] = None


def get_learner() -> BehaviorLearner:
    """Get or create the singleton learner instance."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = BehaviorLearner()
    return _learner_instance
