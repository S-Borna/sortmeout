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
from sortmeout.utils.logger import get_logger
from sortmeout.utils.file_info import get_file_info

logger = get_logger(__name__)


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
        preview_mode: bool = False,
        stop_on_error: bool = False,
        max_rules_per_file: int = 100,
    ):
        """
        Initialize the rule engine.

        Args:
            preview_mode: Don't actually execute actions.
            stop_on_error: Stop on first error.
            max_rules_per_file: Maximum rules to process per file (safety limit).
        """
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

    def process_file(
        self,
        file_path: str,
        rules: List[Rule],
        file_info: Optional[Dict[str, Any]] = None,
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
                except:
                    pass

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
                results.append(ActionResult(
                    success=False,
                    action_type=action.action_type,
                    source_path=current_path,
                    error=str(e),
                ))

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
    ) -> List[ActionResult]:
        """
        Preview what actions a rule would perform on a file.

        Args:
            rule: Rule to preview.
            file_path: Path to the file.
            file_info: Pre-computed file information.

        Returns:
            List of ActionResults (with preview=True).
        """
        if file_info is None:
            file_info = get_file_info(file_path)

        if not rule.matches(file_info):
            return []

        results = []
        for action in rule.actions:
            if action.enabled:
                result = action.execute(file_path, file_info, preview=True)
                results.append(result)

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get engine statistics."""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset engine statistics."""
        self._stats = {
            "files_processed": 0,
            "rules_evaluated": 0,
            "rules_matched": 0,
            "actions_executed": 0,
            "errors": 0,
        }


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
