"""
First-run onboarding wizard for SortMeOut.

Walks new users through:
1. Welcome screen
2. Select a folder to watch
3. Choose from starter templates
4. Done — starts watching

Uses rumps alerts for simplicity; works without PyObjC AppKit.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from typing import Callable, Optional

try:
    import rumps
except ImportError:
    rumps = None

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


def run_onboarding(
    sortmeout,
    config_manager,
    refresh_callback: Optional[Callable] = None,
) -> None:
    """
    Run the first-launch onboarding wizard.

    Parameters
    ----------
    sortmeout : SortMeOut
        The core coordinator instance.
    config_manager : ConfigManager
        Config manager to save initial settings.
    refresh_callback : callable, optional
        Called after onboarding to refresh menus, etc.
    """
    if rumps is None:
        logger.warning("Onboarding requires rumps; skipping.")
        return

    _mark_onboarding_done(config_manager, mark_complete=False)

    # ─── Step 1: Welcome ──────────────────────────────────────────

    response = rumps.alert(
        title="Welcome to SortMeOut! 👋",
        message=(
            "SortMeOut automatically organizes your files using smart rules.\n\n"
            "This quick setup will get you started in under a minute:\n\n"
            "  1. Pick a folder to watch (e.g., Downloads)\n"
            "  2. Choose starter rules from templates\n"
            "  3. Start organizing!\n\n"
            "Ready to begin?"
        ),
        ok="Let's Go",
        cancel="Skip Setup",
    )
    if response != 1:
        logger.info("User skipped onboarding")
        _mark_onboarding_done(config_manager)
        return

    # ─── Step 2: Choose folder ────────────────────────────────────

    folder = _pick_folder()
    if not folder:
        rumps.alert(
            title="No Folder Selected",
            message="You can add folders later from the Folders menu.",
        )
        _mark_onboarding_done(config_manager)
        return

    sortmeout.add_folder(folder)
    folder_name = os.path.basename(folder.rstrip("/"))

    # ─── Step 3: Choose templates ─────────────────────────────────

    applied_templates = 0

    try:
        from sortmeout.core.templates import get_onboarding_templates, template_to_rule_dict
        from sortmeout.core.rule import Rule
        from sortmeout.core.condition import Condition
        from sortmeout.core.action import Action

        templates = get_onboarding_templates()
        if templates:
            # Overview of available templates
            template_overview = "\n".join(
                f"  • {t['name']} — {t['description']}" for t in templates
            )

            response = rumps.alert(
                title="Choose Starter Rules",
                message=(
                    f"Great! '{folder_name}' is now being watched.\n\n"
                    f"Available starter rules:\n\n"
                    f"{template_overview}\n\n"
                    "Would you like to pick which rules to apply?"
                ),
                ok="Pick Rules",
                cancel="Skip Templates",
                other="Apply All",
            )

            if response == 1:
                # Interactive per-template picker
                applied = 0
                for tmpl in templates:
                    pick = rumps.alert(
                        title=f"Apply: {tmpl['name']}?",
                        message=(
                            f"{tmpl['description']}\n\n"
                            f"Category: {tmpl.get('category', 'General')}\n"
                            f"Target: {tmpl.get('folder_hint', folder)}"
                        ),
                        ok="Apply",
                        cancel="Skip",
                    )
                    if pick == 1:
                        try:
                            rule_data = template_to_rule_dict(tmpl, folder)
                            conditions = [
                                Condition(c["attribute"], c["operator"], c.get("value", ""))
                                for c in rule_data.get("conditions", [])
                            ]
                            actions = [
                                Action(a["action_type"], **a.get("params", {}))
                                for a in rule_data.get("actions", [])
                            ]
                            rule = Rule(
                                name=rule_data["name"],
                                conditions=conditions,
                                actions=actions,
                            )
                            sortmeout.add_rule(folder, rule)
                            applied += 1
                        except Exception as e:
                            logger.warning("Failed to apply template '%s': %s", tmpl["name"], e)

                if applied:
                    applied_templates = applied
                    rumps.notification(
                        "SortMeOut",
                        "Templates Applied",
                        f"Applied {applied} of {len(templates)} starter rule(s) to {folder_name}.",
                    )
                else:
                    rumps.notification(
                        "SortMeOut",
                        "No Templates Applied",
                        "You can add rules anytime from the menu.",
                    )

            elif response == -1:
                # "Apply All" button
                applied = 0
                for tmpl in templates:
                    try:
                        rule_data = template_to_rule_dict(tmpl, folder)
                        conditions = [
                            Condition(c["attribute"], c["operator"], c.get("value", ""))
                            for c in rule_data.get("conditions", [])
                        ]
                        actions = [
                            Action(a["action_type"], **a.get("params", {}))
                            for a in rule_data.get("actions", [])
                        ]
                        rule = Rule(
                            name=rule_data["name"],
                            conditions=conditions,
                            actions=actions,
                        )
                        sortmeout.add_rule(folder, rule)
                        applied += 1
                    except Exception as e:
                        logger.warning("Failed to apply template '%s': %s", tmpl["name"], e)

                if applied:
                    applied_templates = applied
                    rumps.notification(
                        "SortMeOut",
                        "Templates Applied",
                        f"Applied {applied} starter rule(s) to {folder_name}.",
                    )
    except ImportError:
        logger.info("Templates module not available; skipping template step")

    # ─── Step 4: Done ─────────────────────────────────────────────

    response = rumps.alert(
        title="You're All Set! 🎉",
        message=(
            f"SortMeOut is ready to organize '{folder_name}'.\n\n"
            "Click 'Start Watching' in the menu bar to begin.\n\n"
            "Tips:\n"
            "  • Use 'Quick Add Rule' to create rules fast\n"
            "  • Try 'Organize Now' for a one-time sweep\n"
            "  • Open 'AI Assistant' (Pro) for smart suggestions\n\n"
            "Happy organizing!"
        ),
        ok="Start Watching Now",
        cancel="I'll Start Later",
    )

    _mark_onboarding_done(
        config_manager,
        selected_folder=folder,
        templates_applied=applied_templates,
    )

    if refresh_callback:
        try:
            refresh_callback()
        except Exception as e:
            # Menu refresh is non-critical — app still works, just won't show updated state
            logger.warning("Post-onboarding refresh callback failed: %s", e)

    if response == 1:
        # Auto-start watching
        try:
            sortmeout.start_background()
        except Exception as e:
            logger.error("Failed to auto-start watching: %s", e)


def _pick_folder() -> Optional[str]:
    """Open a native folder picker and return the selected path."""
    script = """
        tell application "System Events"
            activate
            set theFolder to choose folder with prompt "Choose a folder to watch (e.g., Downloads):"
            return POSIX path of theFolder
        end tell
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        logger.error("Folder picker failed: %s", e)
    return None


def _mark_onboarding_done(
    config_manager,
    selected_folder: Optional[str] = None,
    templates_applied: Optional[int] = None,
    mark_complete: bool = True,
) -> None:
    """Record onboarding lifecycle metadata in config."""
    try:
        config = config_manager.load_config()
        if not isinstance(config, dict):
            config = {}

        if not config.get("onboarding_started_at"):
            config["onboarding_started_at"] = datetime.now().isoformat()

        if selected_folder:
            config["onboarding_selected_folder"] = selected_folder

        if templates_applied is not None:
            config["onboarding_templates_applied"] = templates_applied

        if mark_complete:
            config["onboarding_completed"] = True
            config["onboarding_completed_at"] = datetime.now().isoformat()

        config_manager.save_config(config)
    except Exception as e:
        logger.warning("Could not save onboarding flag: %s", e)
