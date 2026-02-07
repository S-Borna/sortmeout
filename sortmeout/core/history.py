"""
Action history and logging system.

Records all file operations performed by SortMeOut for audit trail,
undo capability, and statistics.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)

# Default database location
DEFAULT_DB_PATH = Path.home() / ".sortmeout" / "history.db"


@dataclass
class HistoryEntry:
    """A single action history entry."""

    id: Optional[int] = None
    timestamp: str = ""
    rule_name: str = ""
    rule_id: str = ""
    action_type: str = ""
    source_path: str = ""
    destination_path: str = ""
    success: bool = True
    error: Optional[str] = None
    preview: bool = False
    metadata: str = ""  # JSON string

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """Parse metadata JSON."""
        if not self.metadata:
            return {}
        try:
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}

    @property
    def timestamp_dt(self) -> datetime:
        """Get timestamp as datetime."""
        return datetime.fromisoformat(self.timestamp)

    @property
    def source_name(self) -> str:
        """Get source file name."""
        return Path(self.source_path).name if self.source_path else ""

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        dt = self.timestamp_dt.strftime("%Y-%m-%d %H:%M")
        return f"[{status}] {dt} | {self.action_type}: {self.source_name}"


class HistoryManager:
    """
    Manages action history in a SQLite database.

    Thread-safe. Supports querying, statistics, and cleanup.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize history manager.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.sortmeout/history.db
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        """Create the database tables if they don't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                rule_name TEXT DEFAULT '',
                rule_id TEXT DEFAULT '',
                action_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                destination_path TEXT DEFAULT '',
                success INTEGER DEFAULT 1,
                error TEXT,
                preview INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_action_type ON history(action_type)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_rule_name ON history(rule_name)
        """)
        self._conn.commit()

    def record(
        self,
        action_type: str,
        source_path: str,
        destination_path: str = "",
        success: bool = True,
        error: Optional[str] = None,
        rule_name: str = "",
        rule_id: str = "",
        preview: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record an action in history.

        Args:
            action_type: Type of action performed.
            source_path: Original file path.
            destination_path: Destination path (if applicable).
            success: Whether action succeeded.
            error: Error message if failed.
            rule_name: Name of the rule that triggered the action.
            rule_id: ID of the rule.
            preview: Whether this was a preview (dry run).
            metadata: Additional metadata dict.

        Returns:
            ID of the new history entry.
        """
        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            rule_name=rule_name,
            rule_id=rule_id,
            action_type=action_type,
            source_path=source_path,
            destination_path=destination_path,
            success=success,
            error=error,
            preview=preview,
            metadata=json.dumps(metadata or {}),
        )

        cursor = self._conn.execute(
            """
            INSERT INTO history
                (timestamp, rule_name, rule_id, action_type, source_path,
                 destination_path, success, error, preview, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.timestamp,
                entry.rule_name,
                entry.rule_id,
                entry.action_type,
                entry.source_path,
                entry.destination_path,
                int(entry.success),
                entry.error,
                int(entry.preview),
                entry.metadata,
            ),
        )
        self._conn.commit()
        entry_id = cursor.lastrowid
        logger.debug("Recorded history entry %d: %s", entry_id, entry)
        return entry_id

    def get_recent(self, limit: int = 50, offset: int = 0) -> List[HistoryEntry]:
        """
        Get recent history entries.

        Args:
            limit: Maximum number of entries.
            offset: Offset for pagination.

        Returns:
            List of HistoryEntry objects (newest first).
        """
        rows = self._conn.execute(
            "SELECT * FROM history ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_by_rule(self, rule_name: str, limit: int = 50) -> List[HistoryEntry]:
        """Get history entries for a specific rule."""
        rows = self._conn.execute(
            "SELECT * FROM history WHERE rule_name = ? ORDER BY timestamp DESC LIMIT ?",
            (rule_name, limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_by_action(self, action_type: str, limit: int = 50) -> List[HistoryEntry]:
        """Get history entries for a specific action type."""
        rows = self._conn.execute(
            "SELECT * FROM history WHERE action_type = ? ORDER BY timestamp DESC LIMIT ?",
            (action_type, limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_by_file(self, file_path: str, limit: int = 50) -> List[HistoryEntry]:
        """Get history entries for a specific file."""
        rows = self._conn.execute(
            """SELECT * FROM history
               WHERE source_path = ? OR destination_path = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (file_path, file_path, limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_errors(self, limit: int = 50) -> List[HistoryEntry]:
        """Get recent error entries."""
        rows = self._conn.execute(
            "SELECT * FROM history WHERE success = 0 ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_date_range(
        self, start: datetime, end: Optional[datetime] = None, limit: int = 1000
    ) -> List[HistoryEntry]:
        """Get entries within a date range."""
        if end is None:
            end = datetime.now()
        rows = self._conn.execute(
            "SELECT * FROM history WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC LIMIT ?",
            (start.isoformat(), end.isoformat(), limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def search(self, query: str, limit: int = 50) -> List[HistoryEntry]:
        """Search history by file name or rule name."""
        pattern = f"%{query}%"
        rows = self._conn.execute(
            """SELECT * FROM history
               WHERE source_path LIKE ? OR destination_path LIKE ?
               OR rule_name LIKE ? OR action_type LIKE ?
               ORDER BY timestamp DESC LIMIT ?""",
            (pattern, pattern, pattern, pattern, limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get statistics for the last N days.

        Returns:
            Dictionary with statistics.
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Total actions
        total = self._conn.execute(
            "SELECT COUNT(*) FROM history WHERE timestamp > ? AND preview = 0",
            (cutoff,),
        ).fetchone()[0]

        # Successful / failed
        successful = self._conn.execute(
            "SELECT COUNT(*) FROM history WHERE timestamp > ? AND success = 1 AND preview = 0",
            (cutoff,),
        ).fetchone()[0]

        errors = total - successful

        # By action type
        by_action = {}
        for row in self._conn.execute(
            """SELECT action_type, COUNT(*) as cnt FROM history
               WHERE timestamp > ? AND preview = 0
               GROUP BY action_type ORDER BY cnt DESC""",
            (cutoff,),
        ).fetchall():
            by_action[row["action_type"]] = row["cnt"]

        # By rule
        by_rule = {}
        for row in self._conn.execute(
            """SELECT rule_name, COUNT(*) as cnt FROM history
               WHERE timestamp > ? AND preview = 0 AND rule_name != ''
               GROUP BY rule_name ORDER BY cnt DESC LIMIT 20""",
            (cutoff,),
        ).fetchall():
            by_rule[row["rule_name"]] = row["cnt"]

        # Files processed per day
        daily = {}
        for row in self._conn.execute(
            """SELECT DATE(timestamp) as day, COUNT(*) as cnt FROM history
               WHERE timestamp > ? AND preview = 0
               GROUP BY day ORDER BY day""",
            (cutoff,),
        ).fetchall():
            daily[row["day"]] = row["cnt"]

        # Most moved destinations
        top_destinations = {}
        for row in self._conn.execute(
            """SELECT destination_path, COUNT(*) as cnt FROM history
               WHERE timestamp > ? AND destination_path != '' AND preview = 0
               GROUP BY destination_path ORDER BY cnt DESC LIMIT 10""",
            (cutoff,),
        ).fetchall():
            top_destinations[row["destination_path"]] = row["cnt"]

        return {
            "period_days": days,
            "total_actions": total,
            "successful": successful,
            "errors": errors,
            "success_rate": round(successful / total * 100, 1) if total else 0,
            "by_action_type": by_action,
            "by_rule": by_rule,
            "daily_counts": daily,
            "top_destinations": top_destinations,
        }

    def cleanup(self, max_age_days: int = 90, max_entries: int = 50000) -> int:
        """
        Clean up old history entries.

        Args:
            max_age_days: Delete entries older than this.
            max_entries: Keep at most this many entries.

        Returns:
            Number of entries deleted.
        """
        deleted = 0

        # Delete by age
        cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        cursor = self._conn.execute(
            "DELETE FROM history WHERE timestamp < ?", (cutoff,)
        )
        deleted += cursor.rowcount

        # Delete excess entries
        count = self._conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        if count > max_entries:
            excess = count - max_entries
            self._conn.execute(
                """DELETE FROM history WHERE id IN
                   (SELECT id FROM history ORDER BY timestamp ASC LIMIT ?)""",
                (excess,),
            )
            deleted += excess

        self._conn.commit()
        logger.info("Cleaned up %d history entries", deleted)
        return deleted

    def export_json(self, file_path: str, days: Optional[int] = None) -> int:
        """
        Export history to JSON file.

        Args:
            file_path: Output file path.
            days: Only export last N days. None for all.

        Returns:
            Number of entries exported.
        """
        if days:
            entries = self.get_date_range(datetime.now() - timedelta(days=days))
        else:
            entries = self.get_recent(limit=100000)

        data = []
        for entry in entries:
            data.append({
                "id": entry.id,
                "timestamp": entry.timestamp,
                "rule_name": entry.rule_name,
                "rule_id": entry.rule_id,
                "action_type": entry.action_type,
                "source_path": entry.source_path,
                "destination_path": entry.destination_path,
                "success": entry.success,
                "error": entry.error,
                "preview": entry.preview,
                "metadata": entry.metadata_dict,
            })

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        return len(data)

    def _row_to_entry(self, row: sqlite3.Row) -> HistoryEntry:
        """Convert a database row to a HistoryEntry."""
        return HistoryEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            rule_name=row["rule_name"],
            rule_id=row["rule_id"],
            action_type=row["action_type"],
            source_path=row["source_path"],
            destination_path=row["destination_path"],
            success=bool(row["success"]),
            error=row["error"],
            preview=bool(row["preview"]),
            metadata=row["metadata"],
        )

    def close(self):
        """Close the database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    # ──────────────────────────────────────────────────────────────
    # UNDO SYSTEM
    # ──────────────────────────────────────────────────────────────

    # Actions that can be reversed
    REVERSIBLE_ACTIONS = {"move", "copy", "rename", "trash", "add_tags", "set_label"}

    def get_entry(self, entry_id: int) -> Optional[HistoryEntry]:
        """Get a specific history entry by ID."""
        row = self._conn.execute(
            "SELECT * FROM history WHERE id = ?", (entry_id,)
        ).fetchone()
        if row:
            return self._row_to_entry(row)
        return None

    def undo_last(self) -> Dict[str, Any]:
        """
        Undo the most recent successful, non-preview action.

        Returns:
            Dict with 'success', 'action', 'message' keys.
        """
        rows = self._conn.execute(
            """SELECT * FROM history
               WHERE success = 1 AND preview = 0
               ORDER BY timestamp DESC LIMIT 1"""
        ).fetchall()

        if not rows:
            return {"success": False, "message": "No actions to undo."}

        entry = self._row_to_entry(rows[0])
        return self._undo_entry(entry)

    def undo_entry(self, entry_id: int) -> Dict[str, Any]:
        """
        Undo a specific history entry by ID.

        Args:
            entry_id: The ID of the history entry to undo.

        Returns:
            Dict with 'success', 'action', 'message' keys.
        """
        entry = self.get_entry(entry_id)
        if entry is None:
            return {"success": False, "message": f"Entry {entry_id} not found."}
        if not entry.success:
            return {"success": False, "message": "Cannot undo a failed action."}
        if entry.preview:
            return {"success": False, "message": "Cannot undo a preview action."}
        return self._undo_entry(entry)

    def _undo_entry(self, entry: HistoryEntry) -> Dict[str, Any]:
        """Perform the actual undo for a history entry."""
        import os
        import shutil
        import subprocess
        from pathlib import Path

        action = entry.action_type.lower()

        if action not in self.REVERSIBLE_ACTIONS:
            return {
                "success": False,
                "message": f"Action '{entry.action_type}' cannot be undone.",
            }

        try:
            if action == "move":
                # Move file back to original location
                if not entry.destination_path or not entry.source_path:
                    return {"success": False, "message": "Missing paths for undo."}

                # The file is now at destination_path, move back to source_path
                dest = Path(entry.destination_path)
                src_dir = Path(entry.source_path).parent
                src_name = Path(entry.source_path).name

                # If destination_path is a directory, the file is inside it
                if dest.is_dir():
                    actual_file = dest / src_name
                else:
                    actual_file = dest

                if not actual_file.exists():
                    return {
                        "success": False,
                        "message": f"File not found at destination: {actual_file}",
                    }

                src_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(actual_file), str(src_dir / src_name))

                self.record(
                    action_type="undo_move",
                    source_path=str(actual_file),
                    destination_path=str(src_dir / src_name),
                    rule_name=f"Undo: {entry.rule_name}",
                    metadata={"undone_entry_id": entry.id},
                )

                return {
                    "success": True,
                    "action": "move",
                    "message": f"Moved back: {src_name} → {src_dir}",
                }

            elif action == "copy":
                # Delete the copy
                if not entry.destination_path:
                    return {"success": False, "message": "Missing destination for undo."}

                dest = Path(entry.destination_path)
                src_name = Path(entry.source_path).name

                if dest.is_dir():
                    copy_path = dest / src_name
                else:
                    copy_path = dest

                if not copy_path.exists():
                    return {
                        "success": False,
                        "message": f"Copy not found: {copy_path}",
                    }

                copy_path.unlink()

                self.record(
                    action_type="undo_copy",
                    source_path=str(copy_path),
                    rule_name=f"Undo: {entry.rule_name}",
                    metadata={"undone_entry_id": entry.id},
                )

                return {
                    "success": True,
                    "action": "copy",
                    "message": f"Deleted copy: {copy_path.name}",
                }

            elif action == "rename":
                # Rename back
                if not entry.destination_path or not entry.source_path:
                    return {"success": False, "message": "Missing paths for undo."}

                new_path = Path(entry.destination_path)
                old_path = Path(entry.source_path)

                if not new_path.exists():
                    return {
                        "success": False,
                        "message": f"File not found: {new_path}",
                    }

                new_path.rename(old_path)

                self.record(
                    action_type="undo_rename",
                    source_path=str(new_path),
                    destination_path=str(old_path),
                    rule_name=f"Undo: {entry.rule_name}",
                    metadata={"undone_entry_id": entry.id},
                )

                return {
                    "success": True,
                    "action": "rename",
                    "message": f"Renamed back: {new_path.name} → {old_path.name}",
                }

            elif action == "trash":
                # Cannot reliably restore from macOS Trash programmatically
                return {
                    "success": False,
                    "message": "Undo trash is not supported. Restore manually from Trash.",
                }

            elif action == "add_tags":
                # Remove tags that were added
                meta = entry.metadata_dict
                tags = meta.get("tags", [])
                if tags and entry.source_path:
                    try:
                        from sortmeout.macos.tags import remove_tags
                        remove_tags(entry.source_path, tags)

                        self.record(
                            action_type="undo_add_tags",
                            source_path=entry.source_path,
                            rule_name=f"Undo: {entry.rule_name}",
                            metadata={"removed_tags": tags, "undone_entry_id": entry.id},
                        )

                        return {
                            "success": True,
                            "action": "add_tags",
                            "message": f"Removed tags: {', '.join(tags)}",
                        }
                    except Exception as e:
                        return {"success": False, "message": f"Failed to remove tags: {e}"}
                return {"success": False, "message": "No tag data available."}

            elif action == "set_label":
                # Reset label to none (0)
                if entry.source_path:
                    try:
                        from sortmeout.macos.tags import set_label
                        set_label(entry.source_path, 0)

                        self.record(
                            action_type="undo_set_label",
                            source_path=entry.source_path,
                            rule_name=f"Undo: {entry.rule_name}",
                            metadata={"undone_entry_id": entry.id},
                        )

                        return {
                            "success": True,
                            "action": "set_label",
                            "message": f"Reset label on {Path(entry.source_path).name}",
                        }
                    except Exception as e:
                        return {"success": False, "message": f"Failed to reset label: {e}"}
                return {"success": False, "message": "No source path."}

        except Exception as e:
            logger.error("Undo failed for entry %d: %s", entry.id, e)
            return {"success": False, "message": f"Undo failed: {e}"}

        return {"success": False, "message": "Unknown error during undo."}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Module-level singleton
_history: Optional[HistoryManager] = None


def get_history() -> HistoryManager:
    """Get the global history manager instance."""
    global _history
    if _history is None:
        _history = HistoryManager()
    return _history


def record_action(
    action_type: str,
    source_path: str,
    destination_path: str = "",
    success: bool = True,
    error: Optional[str] = None,
    rule_name: str = "",
    rule_id: str = "",
    preview: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Convenience function to record an action in the global history."""
    return get_history().record(
        action_type=action_type,
        source_path=source_path,
        destination_path=destination_path,
        success=success,
        error=error,
        rule_name=rule_name,
        rule_id=rule_id,
        preview=preview,
        metadata=metadata,
    )
