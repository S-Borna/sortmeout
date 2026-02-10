"""
Rule execution engine.

The engine processes files against rules, evaluates conditions,
and executes actions.
"""

from __future__ import annotations

import os
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from sortmeout.core.rule import Rule
from sortmeout.core.action import Action, ActionResult
from sortmeout.core.license import can_execute_automation, LicenseAuthority
from sortmeout.utils.logger import get_logger
from sortmeout.utils.file_info import get_file_info

logger = get_logger(__name__)


def _try_record_history(
    action_result: ActionResult, rule_name: str = "", rule_id: str = "", preview: bool = False
):
    """Try to record action to history, silently ignore failures."""
    try:
        from sortmeout.core.history import record_action

        record_action(
            action_type=(
                action_result.action_type.value
                if hasattr(action_result.action_type, "value")
                else str(action_result.action_type)
            ),
            source_path=action_result.source_path,
            destination_path=action_result.destination_path or "",
            success=action_result.success,
            error=action_result.error,
            rule_name=rule_name,
            rule_id=rule_id,
            preview=preview,
            metadata=action_result.metadata if hasattr(action_result, "metadata") else None,
        )
    except Exception as e:
        # History recording is best-effort but failures should be visible
        # in logs for diagnosing undo/audit-trail issues.
        logger.warning(
            "Failed to record action for rule '%s' on %s: %s",
            rule_name,
            action_result.source_path,
            e,
        )


@dataclass
class ProcessingResult:
    """
    Result of processing a file through rules.

    Attributes:
        file_path: Path to the processed file.
        matched_rules: Names of rules that matched.
        executed_actions: Results of executed actions.
        errors: Any errors that occurred.
        processing_time: Time taken to process.
    """

    file_path: str
    matched_rules: List[str] = field(default_factory=list)
    executed_actions: List[ActionResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    stopped: bool = False  # Processing was stopped by a rule

    @property
    def success(self) -> bool:
        """Check if processing was successful (no errors)."""
        return len(self.errors) == 0

    @property
    def matched(self) -> bool:
        """Check if any rules matched."""
        return len(self.matched_rules) > 0

    @property
    def rules_applied(self) -> int:
        """Number of rules that matched and were applied."""
        return len(self.matched_rules)

    def __str__(self) -> str:
        return (
            f"ProcessingResult(file={Path(self.file_path).name}, "
            f"matched={len(self.matched_rules)}, "
            f"actions={len(self.executed_actions)}, "
            f"errors={len(self.errors)})"
        )


class RuleEngine:
    """
    Engine for processing files against rules.

    The engine:
    1. Gathers file information
    2. Evaluates each rule's conditions
    3. Executes actions for matching rules
    4. Handles errors and continues/stops as configured

    Attributes:
        preview_mode: If True, actions are not actually executed.
        stop_on_error: If True, stop processing on first error.
    """

    def __init__(
        self,
        rules: Optional[List[Rule]] = None,
        preview_mode: bool = False,
        stop_on_error: bool = False,
        max_rules_per_file: int = 100,
    ):
        """
        Initialize the rule engine.

        Args:
            rules: Initial list of rules.
            preview_mode: Don't actually execute actions.
            stop_on_error: Stop on first error.
            max_rules_per_file: Maximum rules to process per file (safety limit).
        """
        self.rules: List[Rule] = rules or []
        self.preview_mode = preview_mode
        self.stop_on_error = stop_on_error
        self.max_rules_per_file = max_rules_per_file

        # Statistics
        self._stats = {
            "files_processed": 0,
            "rules_evaluated": 0,
            "rules_matched": 0,
            "actions_executed": 0,
            "errors": 0,
        }

    # ========================================
    # RULE MANAGEMENT
    # ========================================

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                del self.rules[i]
                return True
        return False

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule by ID."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule by ID."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def get_rules_sorted(self) -> List[Rule]:
        """Get rules sorted by priority (highest first)."""
        return sorted(self.rules, key=lambda r: r.priority, reverse=True)

    def set_rule_priority(self, rule_id: str, priority: int) -> bool:
        """Set rule priority."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.priority = priority
            return True
        return False

    def find_matching_rules(self, file_info: Dict[str, Any]) -> List[Rule]:
        """Find all rules that match the given file info."""
        return [rule for rule in self.rules if rule.enabled and rule.matches(file_info)]

    def process_file(
        self,
        file_path: str,
        rules: Optional[List[Rule]] = None,
        file_info: Optional[Dict[str, Any]] = None,
        preview: bool = False,
    ) -> ProcessingResult:
        """
        Process a file against a list of rules.

        Args:
            file_path: Path to the file to process.
            rules: List of rules to evaluate.
            file_info: Pre-computed file information (optional).

        Returns:
            ProcessingResult with matched rules and action results.
        """
        start_time = datetime.now()
        result = ProcessingResult(file_path=file_path)

        # Use internal rules if none provided
        if rules is None:
            rules = self.rules

        # Handle preview mode
        old_preview = self.preview_mode
        if preview:
            self.preview_mode = True

        try:
            return self._do_process_file(file_path, rules, file_info, result, start_time)
        finally:
            self.preview_mode = old_preview

    def _do_process_file(
        self,
        file_path: str,
        rules: List[Rule],
        file_info: Optional[Dict[str, Any]],
        result: ProcessingResult,
        start_time: datetime,
    ) -> ProcessingResult:
        """Internal file processing implementation."""

        # LICENSE GATE: Automation requires active license
        if not can_execute_automation():
            result.errors.append(LicenseAuthority.get_expired_message())
            return result

        # Check if file still exists
        if not os.path.exists(file_path):
            result.errors.append(f"File does not exist: {file_path}")
            return result

        # Get file information
        if file_info is None:
            try:
                file_info = get_file_info(file_path)
            except Exception as e:
                result.errors.append(f"Failed to get file info: {e}")
                return result

        logger.debug("Processing file: %s", file_path)
        logger.debug("File info: %s", file_info)

        # Track current file path (may change during processing)
        current_path = file_path
        rules_processed = 0

        # Process each rule
        for rule in rules:
            if rules_processed >= self.max_rules_per_file:
                logger.warning("Max rules limit reached for file: %s", file_path)
                break

            rules_processed += 1
            self._stats["rules_evaluated"] += 1

            # Skip disabled rules
            if not rule.enabled:
                continue

            # Check if rule matches
            try:
                matches = rule.matches(file_info)
            except Exception as e:
                logger.error("Error evaluating rule '%s': %s", rule.name, e)
                result.errors.append(f"Rule '{rule.name}' evaluation error: {e}")
                if self.stop_on_error:
                    break
                continue

            if not matches:
                continue

            # Rule matched!
            logger.info("Rule '%s' matched file: %s", rule.name, current_path)
            result.matched_rules.append(rule.name)
            self._stats["rules_matched"] += 1

            # Execute actions
            action_results, new_path, stop = self._execute_actions(
                rule.actions,
                current_path,
                file_info,
            )

            result.executed_actions.extend(action_results)

            # Record to history
            for ar in action_results:
                _try_record_history(
                    ar, rule_name=rule.name, rule_id=rule.id, preview=self.preview_mode
                )

            # Record rule run
            rule.record_run()

            # Check for action errors
            for ar in action_results:
                if not ar.success:
                    result.errors.append(f"Action failed: {ar.error}")
                    self._stats["errors"] += 1

            # Update current path if file was moved/renamed
            if new_path and new_path != current_path:
                current_path = new_path
                # Update file_info for subsequent rules
                try:
                    file_info = get_file_info(current_path)
                except Exception as e:
                    # If we can't read the new file, subsequent rules will
                    # operate on stale data. Log and stop processing this file.
                    logger.error(
                        "Cannot read moved file %s for subsequent rules: %s", current_path, e
                    )
                    result.errors.append(f"Could not re-read file after move: {e}")
                    break

            # Check if we should stop processing
            if stop or not rule.continue_processing:
                result.stopped = True
                break

            # Stop on error if configured
            if result.errors and self.stop_on_error:
                break

        # Calculate processing time
        result.processing_time = (datetime.now() - start_time).total_seconds()
        self._stats["files_processed"] += 1

        logger.debug("Finished processing: %s", result)
        return result

    def _execute_actions(
        self,
        actions: List[Action],
        file_path: str,
        file_info: Dict[str, Any],
    ) -> tuple[List[ActionResult], Optional[str], bool]:
        """
        Execute a list of actions on a file.

        Args:
            actions: Actions to execute.
            file_path: Current file path.
            file_info: File information.

        Returns:
            Tuple of (action_results, new_path, should_stop).
        """
        results = []
        current_path = file_path
        should_stop = False

        for action in actions:
            if not action.enabled:
                continue

            # Check if file still exists (may have been deleted by previous action)
            if not os.path.exists(current_path):
                logger.warning("File no longer exists, stopping actions: %s", current_path)
                break

            # Execute the action
            try:
                result = action.execute(
                    current_path,
                    file_info,
                    preview=self.preview_mode,
                )
                results.append(result)
                self._stats["actions_executed"] += 1

                # Update path if action moved/renamed the file
                if result.success and result.destination_path:
                    current_path = result.destination_path

                # Stop on error if action is configured to do so
                if not result.success and action.stop_on_error:
                    logger.warning("Action failed, stopping: %s", result.error)
                    should_stop = True
                    break

            except Exception as e:
                logger.error("Action execution error: %s", e)
                results.append(
                    ActionResult(
                        success=False,
                        action_type=action.action_type,
                        source_path=current_path,
                        error=str(e),
                    )
                )

                if action.stop_on_error:
                    should_stop = True
                    break

        return results, current_path if current_path != file_path else None, should_stop

    def evaluate_rule(
        self,
        rule: Rule,
        file_path: str,
        file_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Evaluate a single rule against a file without executing actions.

        Args:
            rule: Rule to evaluate.
            file_path: Path to the file.
            file_info: Pre-computed file information.

        Returns:
            True if the rule matches.
        """
        if file_info is None:
            file_info = get_file_info(file_path)

        return rule.matches(file_info)

    def preview_rule(
        self,
        rule: Rule,
        file_path: str,
        file_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Preview what actions a rule would perform on a file.

        Args:
            rule: Rule to preview.
            file_path: Path to the file.
            file_info: Pre-computed file information.

        Returns:
            Dictionary with 'matches', 'rule', and 'actions' keys.
        """
        if file_info is None:
            file_info = get_file_info(file_path)

        matches = rule.matches(file_info)
        actions = []

        if matches:
            for action in rule.actions:
                if action.enabled:
                    result = action.execute(file_path, file_info, preview=True)
                    actions.append(result)

        return {
            "matches": matches,
            "rule": rule.name,
            "actions": actions,
        }

    def get_stats(self) -> Dict[str, int]:
        """Get engine statistics."""
        stats = self._stats.copy()
        stats["total_processed"] = stats["files_processed"]
        stats["total_matched"] = stats["rules_matched"]
        return stats

    def reset_stats(self) -> None:
        """Reset engine statistics."""
        self._stats = {
            "files_processed": 0,
            "rules_evaluated": 0,
            "rules_matched": 0,
            "actions_executed": 0,
            "errors": 0,
        }

    def export_rules(self, path: str) -> None:
        """Export rules to a file."""
        import json

        data = [rule.to_dict() for rule in self.rules]
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def import_rules(self, path: str) -> None:
        """Import rules from a file."""
        import json

        with open(path, "r") as f:
            data = json.load(f)
        self.rules = [Rule.from_dict(r) for r in data]


class BatchProcessor:
    """
    Process multiple files in batch.

    Useful for processing existing files in a folder when rules are first added.
    """

    def __init__(self, engine: RuleEngine):
        """
        Initialize batch processor.

        Args:
            engine: Rule engine to use for processing.
        """
        self.engine = engine

    def process_folder(
        self,
        folder_path: str,
        rules: List[Rule],
        recursive: bool = False,
        file_filter: Optional[callable] = None,
    ) -> List[ProcessingResult]:
        """
        Process all files in a folder.

        Args:
            folder_path: Path to the folder.
            rules: Rules to apply.
            recursive: Process subdirectories.
            file_filter: Optional function to filter files.

        Returns:
            List of ProcessingResults.
        """
        results = []
        folder = Path(folder_path)

        if recursive:
            files = folder.rglob("*")
        else:
            files = folder.glob("*")

        for path in files:
            if not path.is_file():
                continue

            if file_filter and not file_filter(str(path)):
                continue

            result = self.engine.process_file(str(path), rules)
            results.append(result)

        return results

    def process_files(
        self,
        file_paths: List[str],
        rules: List[Rule],
    ) -> List[ProcessingResult]:
        """
        Process a list of specific files.

        Args:
            file_paths: Paths to files.
            rules: Rules to apply.

        Returns:
            List of ProcessingResults.
        """
        results = []

        for file_path in file_paths:
            result = self.engine.process_file(file_path, rules)
            results.append(result)

        return results

    def process_directory(
        self,
        folder_path: str,
        recursive: bool = False,
        extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process all files in a directory and return summary.

        Args:
            folder_path: Path to the folder.
            recursive: Process subdirectories.
            extensions: Only process files with these extensions.

        Returns:
            Dictionary with total, matched, processed, errors counts.
        """
        folder = Path(folder_path)

        if recursive:
            files = list(folder.rglob("*"))
        else:
            files = list(folder.glob("*"))

        files = [f for f in files if f.is_file()]

        if extensions:
            normalized = [e if e.startswith(".") else f".{e}" for e in extensions]
            files = [f for f in files if f.suffix in normalized]

        results = []
        for path in files:
            result = self.engine.process_file(str(path))
            results.append(result)

        matched = sum(1 for r in results if r.matched)
        processed = sum(1 for r in results if r.matched and r.success)

        return {
            "total": len(results),
            "matched": matched,
            "processed": processed,
            "errors": sum(1 for r in results if not r.success),
        }
