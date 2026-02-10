"""
Command-line interface for SortMeOut.

Provides a full-featured CLI for managing file automation rules.
"""

from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint

from sortmeout import SortMeOut, Rule, Condition, Action, __version__
from sortmeout.config.manager import ConfigManager
from sortmeout.utils.logger import setup_logging, get_logger
from sortmeout.macos.trash import get_trash_info, empty_trash, TrashManager

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(__version__, prog_name="SortMeOut")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", "-c", type=click.Path(), help="Path to config file")
@click.pass_context
def main(ctx, verbose: bool, config: Optional[str]):
    """
    SortMeOut - Automated file organization for macOS.

    Watch folders and organize files automatically based on rules you define.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config

    if verbose:
        setup_logging(level="DEBUG")
    else:
        setup_logging(level="INFO")


@main.command()
@click.option("--preview", "-p", is_flag=True, help="Preview mode (don't execute actions)")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground")
@click.pass_context
def start(ctx, preview: bool, foreground: bool):
    """Start watching configured folders."""
    app = SortMeOut(
        config_path=ctx.obj.get("config"),
        preview_mode=preview,
        verbose=ctx.obj.get("verbose", False),
    )

    folders = app.get_folders()
    if not folders:
        console.print(
            "[yellow]No folders configured. Use 'sortmeout folder add' to add folders.[/yellow]"
        )
        return

    console.print(f"[green]Starting SortMeOut...[/green]")
    console.print(f"Watching {len(folders)} folder(s)")

    if preview:
        console.print("[yellow]Preview mode: Actions will not be executed[/yellow]")

    for folder in folders:
        rules = app.get_rules(folder)
        console.print(f"  • {folder} ({len(rules)} rules)")

    if foreground:
        console.print("\nPress Ctrl+C to stop...")
        try:
            app.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping...[/yellow]")
            app.stop()
    else:
        thread = app.start_background()
        console.print("[green]SortMeOut running in background[/green]")


@main.command()
@click.pass_context
def stop(ctx):
    """Stop a running SortMeOut daemon."""
    from sortmeout.app import read_pid, _remove_pid

    pid = read_pid()
    if pid is None:
        console.print("[yellow]No running SortMeOut instance found.[/yellow]")
        return

    console.print(f"[yellow]Stopping SortMeOut (PID {pid})...[/yellow]")
    try:
        os.kill(pid, signal.SIGTERM)
        # Poll for process exit: 0.3s interval × 10 iterations = 3s max
        # graceful-shutdown window. 0.3s balances responsive CLI feedback
        # against unnecessary CPU spinning.
        import time

        for _ in range(10):
            time.sleep(0.3)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
        _remove_pid()
        console.print("[green]Stopped[/green]")
    except ProcessLookupError:
        _remove_pid()
        console.print("[green]Process already stopped, cleaned up PID file.[/green]")
    except PermissionError:
        console.print("[red]Permission denied. Try running with sudo.[/red]")


@main.command()
@click.pass_context
def status(ctx):
    """Show current status."""
    from sortmeout.app import read_pid

    app = SortMeOut(config_path=ctx.obj.get("config"))

    folders = app.get_folders()
    stats = app.get_stats()

    # Check for running daemon
    pid = read_pid()
    running_status = f"Yes (PID {pid})" if pid else "No"

    # Status panel
    console.print(
        Panel.fit(
            f"[bold]SortMeOut Status[/bold]\n\n"
            f"Folders: {len(folders)}\n"
            f"Running: {running_status}\n"
            f"Preview Mode: {'Yes' if app.preview_mode else 'No'}",
            title="Status",
        )
    )

    # Folders table
    if folders:
        table = Table(title="Watched Folders")
        table.add_column("Folder", style="cyan")
        table.add_column("Rules", justify="right")

        for folder in folders:
            rules = app.get_rules(folder)
            table.add_row(folder, str(len(rules)))

        console.print(table)
    else:
        console.print("[yellow]No folders configured[/yellow]")

    # Scheduler info
    try:
        scheduler_status = app.scheduler.get_status()
        schedules = scheduler_status.get("schedules", [])
        scheduler_running = scheduler_status.get("running", False)

        if schedules:
            sched_table = Table(title="Scheduled Rules")
            sched_table.add_column("Name", style="cyan")
            sched_table.add_column("Folder", style="blue")
            sched_table.add_column("Interval", style="magenta")
            sched_table.add_column("Last Run", style="dim")
            sched_table.add_column("Next Run", style="green")
            sched_table.add_column("Runs", justify="right")
            sched_table.add_column("Status", justify="center")

            for s in schedules:
                name = s.get("name", s.get("rule_id", "—"))
                folder_path = s.get("folder", "—")
                folder_short = (
                    os.path.basename(folder_path.rstrip("/")) if folder_path != "—" else "—"
                )
                interval = s.get("interval", "—")
                last_run = s.get("last_run", "—")
                if last_run and last_run != "—":
                    # Show relative time
                    try:
                        from datetime import datetime

                        lr_dt = datetime.fromisoformat(last_run)
                        delta = datetime.now() - lr_dt
                        if delta.days > 0:
                            last_run = f"{delta.days}d ago"
                        elif delta.seconds >= 3600:
                            last_run = f"{delta.seconds // 3600}h ago"
                        elif delta.seconds >= 60:
                            last_run = f"{delta.seconds // 60}m ago"
                        else:
                            last_run = "just now"
                    except (ValueError, TypeError):
                        pass
                next_run = s.get("next_run", "—")
                if next_run and next_run != "—":
                    try:
                        from datetime import datetime

                        nr_dt = datetime.fromisoformat(next_run)
                        delta = nr_dt - datetime.now()
                        if delta.total_seconds() <= 0:
                            next_run = "[bold yellow]due now[/bold yellow]"
                        elif delta.days > 0:
                            next_run = f"in {delta.days}d"
                        elif delta.seconds >= 3600:
                            next_run = f"in {delta.seconds // 3600}h"
                        elif delta.seconds >= 60:
                            next_run = f"in {delta.seconds // 60}m"
                        else:
                            next_run = "in <1m"
                    except (ValueError, TypeError):
                        pass
                run_count = str(s.get("run_count", 0))
                enabled = s.get("enabled", True)
                status_str = "[green]●[/green]" if enabled else "[red]○[/red]"

                sched_table.add_row(
                    name,
                    folder_short,
                    interval,
                    last_run,
                    next_run,
                    run_count,
                    status_str,
                )

            console.print(sched_table)
            sched_status_msg = (
                "[green]running[/green]" if scheduler_running else "[yellow]stopped[/yellow]"
            )
            console.print(f"  Scheduler: {sched_status_msg}")
        else:
            console.print("[dim]No scheduled rules configured[/dim]")
    except Exception as e:
        logger.debug("Could not retrieve scheduler status: %s", e)


# Folder management commands
@main.group()
def folder():
    """Manage watched folders."""
    pass


@folder.command("add")
@click.argument("path", type=click.Path(exists=True))
@click.option("--recursive", "-r", is_flag=True, help="Watch subdirectories")
@click.pass_context
def folder_add(ctx, path: str, recursive: bool):
    """Add a folder to watch."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    try:
        if app.add_folder(path, recursive=recursive):
            console.print(f"[green]Added folder: {path}[/green]")
            if recursive:
                console.print("  (watching subdirectories)")
        else:
            console.print(f"[yellow]Folder already being watched: {path}[/yellow]")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")


@folder.command("remove")
@click.argument("path")
@click.pass_context
def folder_remove(ctx, path: str):
    """Remove a folder from watching."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    if app.remove_folder(path):
        console.print(f"[green]Removed folder: {path}[/green]")
    else:
        console.print(f"[red]Folder not found: {path}[/red]")


@folder.command("list")
@click.pass_context
def folder_list(ctx):
    """List all watched folders."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    folders = app.get_folders()

    if not folders:
        console.print("[yellow]No folders configured[/yellow]")
        return

    table = Table(title="Watched Folders")
    table.add_column("Path", style="cyan")
    table.add_column("Rules", justify="right")

    for folder in folders:
        rules = app.get_rules(folder)
        table.add_row(folder, str(len(rules)))

    console.print(table)


@folder.command("process")
@click.argument("path")
@click.option("--preview", "-p", is_flag=True, help="Preview only")
@click.pass_context
def folder_process(ctx, path: str, preview: bool):
    """Process all existing files in a folder."""
    app = SortMeOut(config_path=ctx.obj.get("config"), preview_mode=preview)

    try:
        result = app.process_folder(path)
        console.print(f"[green]Processed {result['processed']} files[/green]")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")


# Rule management commands
@main.group()
def rule():
    """Manage rules."""
    pass


@rule.command("add")
@click.argument("folder")
@click.argument("name")
@click.option("--condition", "-c", multiple=True, help="Condition (attribute:operator:value)")
@click.option("--action", "-a", multiple=True, help="Action (type:param=value)")
@click.pass_context
def rule_add(ctx, folder: str, name: str, condition: tuple, action: tuple):
    """Add a rule to a folder."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    # Parse conditions
    conditions = []
    for cond_str in condition:
        parts = cond_str.split(":", 2)
        if len(parts) >= 2:
            attr, op = parts[0], parts[1]
            value = parts[2] if len(parts) > 2 else ""
            conditions.append(Condition(attr, op, value))

    # Parse actions
    actions = []
    for action_str in action:
        if ":" in action_str:
            action_type, params_str = action_str.split(":", 1)
            params = {}
            for param in params_str.split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key.strip()] = value.strip()
            actions.append(Action(action_type, **params))
        else:
            actions.append(Action(action_str))

    try:
        rule = Rule(name=name, conditions=conditions, actions=actions)

        if app.add_rule(folder, rule):
            console.print(f"[green]Added rule '{name}' to {folder}[/green]")
        else:
            console.print(f"[yellow]Rule '{name}' already exists[/yellow]")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")


@rule.command("remove")
@click.argument("folder")
@click.argument("name")
@click.pass_context
def rule_remove(ctx, folder: str, name: str):
    """Remove a rule from a folder."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    if app.remove_rule(folder, name):
        console.print(f"[green]Removed rule '{name}' from {folder}[/green]")
    else:
        console.print(f"[red]Rule not found: {name}[/red]")


@rule.command("list")
@click.argument("folder")
@click.pass_context
def rule_list(ctx, folder: str):
    """List rules for a folder."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    rules = app.get_rules(folder)

    if not rules:
        console.print(f"[yellow]No rules for folder: {folder}[/yellow]")
        return

    table = Table(title=f"Rules for {folder}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Enabled", justify="center")
    table.add_column("Conditions")
    table.add_column("Actions")

    for i, rule in enumerate(rules, 1):
        enabled = "✓" if rule.enabled else "✗"
        conditions = str(len(rule.conditions))
        actions = str(len(rule.actions))
        table.add_row(str(i), rule.name, enabled, conditions, actions)

    console.print(table)


@rule.command("show")
@click.argument("folder")
@click.argument("name")
@click.pass_context
def rule_show(ctx, folder: str, name: str):
    """Show details of a rule."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    rules = app.get_rules(folder)
    rule = next((r for r in rules if r.name == name), None)

    if not rule:
        console.print(f"[red]Rule not found: {name}[/red]")
        return

    # Rule details
    console.print(
        Panel.fit(
            f"[bold]{rule.name}[/bold]\n\n"
            f"Enabled: {'Yes' if rule.enabled else 'No'}\n"
            f"Match Mode: {rule.match_mode.value}\n"
            f"Continue Processing: {'Yes' if rule.continue_processing else 'No'}\n"
            f"Description: {rule.description or 'None'}",
            title="Rule Details",
        )
    )

    # Conditions
    if rule.conditions:
        console.print("\n[bold]Conditions:[/bold]")
        for i, cond in enumerate(rule.conditions, 1):
            console.print(f"  {i}. {cond}")

    # Actions
    if rule.actions:
        console.print("\n[bold]Actions:[/bold]")
        for i, action in enumerate(rule.actions, 1):
            console.print(f"  {i}. {action}")


@rule.command("enable")
@click.argument("folder")
@click.argument("name")
@click.pass_context
def rule_enable(ctx, folder: str, name: str):
    """Enable a rule."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    rules = app.get_rules(folder)
    rule = next((r for r in rules if r.name == name), None)

    if not rule:
        console.print(f"[red]Rule not found: {name}[/red]")
        return

    rule.enabled = True
    app.update_rule(folder, name, rule)
    console.print(f"[green]Enabled rule: {name}[/green]")


@rule.command("disable")
@click.argument("folder")
@click.argument("name")
@click.pass_context
def rule_disable(ctx, folder: str, name: str):
    """Disable a rule."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    rules = app.get_rules(folder)
    rule = next((r for r in rules if r.name == name), None)

    if not rule:
        console.print(f"[red]Rule not found: {name}[/red]")
        return

    rule.enabled = False
    app.update_rule(folder, name, rule)
    console.print(f"[yellow]Disabled rule: {name}[/yellow]")


@rule.command("export")
@click.argument("folder")
@click.argument("output", type=click.Path())
@click.pass_context
def rule_export(ctx, folder: str, output: str):
    """Export rules to a file."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    if app.export_rules(folder, output):
        console.print(f"[green]Exported rules to: {output}[/green]")
    else:
        console.print(f"[red]Failed to export rules[/red]")


@rule.command("import")
@click.argument("folder")
@click.argument("input", type=click.Path(exists=True))
@click.pass_context
def rule_import(ctx, folder: str, input: str):
    """Import rules from a file."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    count = app.import_rules(folder, input)
    console.print(f"[green]Imported {count} rules[/green]")


# Trash management commands
@main.group()
def trash():
    """Manage Trash."""
    pass


@trash.command("status")
def trash_status():
    """Show Trash status."""
    info = get_trash_info()

    console.print(
        Panel.fit(
            f"[bold]Trash Status[/bold]\n\n"
            f"Items: {info.item_count}\n"
            f"Size: {info.size_human}\n"
            f"Oldest: {info.oldest_item_date.strftime('%Y-%m-%d') if info.oldest_item_date else 'N/A'}\n"
            f"Newest: {info.newest_item_date.strftime('%Y-%m-%d') if info.newest_item_date else 'N/A'}",
            title="Trash",
        )
    )


@trash.command("empty")
@click.option("--secure", "-s", is_flag=True, help="Secure empty")
@click.confirmation_option(prompt="Are you sure you want to empty the Trash?")
def trash_empty(secure: bool):
    """Empty the Trash."""
    if empty_trash(secure=secure):
        console.print("[green]Trash emptied[/green]")
    else:
        console.print("[red]Failed to empty Trash[/red]")


@trash.command("clean")
@click.option("--days", "-d", default=30, help="Delete items older than days")
@click.option("--size", "-s", default=10.0, help="Maximum size in GB")
def trash_clean(days: int, size: float):
    """Clean Trash based on age/size limits."""
    manager = TrashManager(max_age_days=days, max_size_gb=size)
    result = manager.run_cleanup()

    deleted_count = len(result["deleted_by_age"]) + len(result["deleted_by_size"])
    console.print(f"[green]Deleted {deleted_count} items[/green]")


# Config management commands
@main.group()
def config():
    """Manage configuration."""
    pass


@config.command("show")
@click.pass_context
def config_show(ctx):
    """Show current configuration."""
    manager = ConfigManager(ctx.obj.get("config"))
    cfg = manager.load_config()

    syntax = Syntax(json.dumps(cfg, indent=2, default=str), "json")
    console.print(syntax)


@config.command("export")
@click.argument("output", type=click.Path())
@click.pass_context
def config_export(ctx, output: str):
    """Export configuration to file."""
    manager = ConfigManager(ctx.obj.get("config"))

    if manager.export_config(output):
        console.print(f"[green]Configuration exported to: {output}[/green]")
    else:
        console.print("[red]Failed to export configuration[/red]")


@config.command("import")
@click.argument("input", type=click.Path(exists=True))
@click.option("--merge", "-m", is_flag=True, help="Merge with existing config")
@click.pass_context
def config_import(ctx, input: str, merge: bool):
    """Import configuration from file."""
    manager = ConfigManager(ctx.obj.get("config"))

    if manager.import_config(input, merge=merge):
        console.print(f"[green]Configuration imported from: {input}[/green]")
    else:
        console.print("[red]Failed to import configuration[/red]")


@config.command("reset")
@click.confirmation_option(prompt="Are you sure you want to reset configuration?")
@click.pass_context
def config_reset(ctx):
    """Reset configuration to defaults."""
    manager = ConfigManager(ctx.obj.get("config"))

    if manager.reset_config():
        console.print("[green]Configuration reset to defaults[/green]")
    else:
        console.print("[red]Failed to reset configuration[/red]")


# ========================================
# License management commands
# ========================================


@main.group()
def license():
    """Manage Pro license."""
    pass


@license.command("status")
def license_status():
    """Show current license status."""
    from sortmeout.core.license import get_license, LicenseState

    lic = get_license()
    state = lic.state

    if state == LicenseState.PRO_ACTIVE:
        console.print(
            Panel.fit(
                "[bold green]Pro License Active[/bold green]\n\n"
                f"AI requests remaining today: {lic.get_ai_remaining()}\n"
                "All features unlocked.",
                title="License Status",
            )
        )
    elif state == LicenseState.TRIAL_ACTIVE:
        days = lic.trial_days_remaining
        console.print(
            Panel.fit(
                f"[bold yellow]Trial Active — {days} day{'s' if days != 1 else ''} remaining[/bold yellow]\n\n"
                f"AI requests remaining today: {lic.get_ai_remaining()}\n"
                "Upgrade to Pro: sortmeout license activate",
                title="License Status",
            )
        )
    else:
        console.print(
            Panel.fit(
                "[bold red]Trial Expired[/bold red]\n\n"
                "File automation still works (freemium).\n"
                "AI features require Pro license.\n\n"
                "Activate: sortmeout license activate YOUR-KEY\n"
                "Purchase: https://sortmeout.saidborna.com/#pricing",
                title="License Status",
            )
        )


@license.command("activate")
@click.argument("key")
def license_activate(key: str):
    """Activate Pro license with a key."""
    from sortmeout.core.license import get_license

    lic = get_license()

    if lic.activate_pro_license(key):
        console.print("[bold green]✓ Pro License Activated![/bold green]")
        console.print("Thank you for supporting SortMeOut!")
        console.print(f"AI requests per day: {lic.get_ai_remaining()}")
    else:
        console.print("[bold red]✗ Invalid license key[/bold red]")
        console.print("Please check your key and try again.")
        console.print("Need a key? Visit: https://sortmeout.saidborna.com/#pricing")


@license.command("verify")
def license_verify():
    """Verify license with the server."""
    from sortmeout.core.license import get_license, LicenseState

    lic = get_license()

    if lic.state != LicenseState.PRO_ACTIVE:
        console.print("[yellow]No active Pro license to verify.[/yellow]")
        return

    console.print("Verifying license with server...")
    result = lic.verify_license_online(lic._pro_license_key)

    if result is None:
        console.print("[yellow]Could not reach server. License is valid offline.[/yellow]")
    elif result.get("valid"):
        console.print(f"[green]✓ License verified — status: {result.get('status')}[/green]")
    else:
        console.print(f"[red]✗ License invalid — {result.get('error', 'unknown')}[/red]")


@license.command("deactivate")
@click.confirmation_option(prompt="Are you sure you want to deactivate your Pro license?")
def license_deactivate():
    """Deactivate Pro license (for license transfer)."""
    from sortmeout.core.license import get_license

    lic = get_license()
    lic.deactivate_pro()
    console.print("[yellow]Pro license deactivated.[/yellow]")
    console.print("You can activate a new key with: sortmeout license activate YOUR-KEY")


# Test command
@main.command("test")
@click.argument("file", type=click.Path(exists=True))
@click.argument("folder")
@click.option("--preview", "-p", is_flag=True, default=True, help="Preview mode")
@click.pass_context
def test_file(ctx, file: str, folder: str, preview: bool):
    """Test rules against a file."""
    app = SortMeOut(config_path=ctx.obj.get("config"), preview_mode=preview)

    from sortmeout.utils.file_info import get_file_info
    from sortmeout.core.engine import RuleEngine

    # Get file info
    file_info = get_file_info(file)
    console.print(
        Panel.fit(
            f"[bold]File: {os.path.basename(file)}[/bold]\n\n"
            f"Size: {file_info.get('size_human', 'N/A')}\n"
            f"Extension: {file_info.get('extension', 'N/A')}\n"
            f"Kind: {file_info.get('kind', 'N/A')}",
            title="File Info",
        )
    )

    # Test rules
    rules = app.get_rules(folder)
    engine = RuleEngine(preview_mode=True)

    console.print("\n[bold]Rule Matching:[/bold]")
    for rule in rules:
        matches = engine.evaluate_rule(rule, file, file_info)
        status = "[green]✓ MATCH[/green]" if matches else "[dim]✗ No match[/dim]"
        console.print(f"  {rule.name}: {status}")

        if matches:
            console.print("    [bold]Actions would execute:[/bold]")
            for action in rule.actions:
                console.print(f"      • {action}")


# ========================================
# History management commands
# ========================================


@main.group()
def history():
    """View and manage action history."""
    pass


@history.command("list")
@click.option("--limit", "-n", default=20, help="Number of entries to show")
@click.option("--errors", "-e", is_flag=True, help="Show only errors")
@click.option("--rule", "-r", type=str, help="Filter by rule name")
@click.option("--action", "-a", type=str, help="Filter by action type")
def history_list(limit: int, errors: bool, rule: str, action: str):
    """List recent action history."""
    from sortmeout.core.history import get_history

    hist = get_history()

    if errors:
        entries = hist.get_errors(limit=limit)
    elif rule:
        entries = hist.get_by_rule(rule, limit=limit)
    elif action:
        entries = hist.get_by_action(action, limit=limit)
    else:
        entries = hist.get_recent(limit=limit)

    if not entries:
        console.print("[yellow]No history entries found.[/yellow]")
        return

    table = Table(title="Action History")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Time", style="cyan")
    table.add_column("Action", style="magenta")
    table.add_column("File", style="white")
    table.add_column("Rule", style="blue")
    table.add_column("Status", justify="center")

    for entry in entries:
        status = "[green]✓[/green]" if entry.success else f"[red]✗ {entry.error or ''}[/red]"
        dt = entry.timestamp_dt.strftime("%Y-%m-%d %H:%M")
        table.add_row(
            str(entry.id),
            dt,
            entry.action_type,
            entry.source_name,
            entry.rule_name or "—",
            status,
        )

    console.print(table)


@history.command("search")
@click.argument("query")
@click.option("--limit", "-n", default=20, help="Max results")
def history_search(query: str, limit: int):
    """Search history by file name, rule, or action type."""
    from sortmeout.core.history import get_history

    hist = get_history()
    entries = hist.search(query, limit=limit)

    if not entries:
        console.print(f"[yellow]No results for: {query}[/yellow]")
        return

    table = Table(title=f"Search Results: '{query}'")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Time", style="cyan")
    table.add_column("Action", style="magenta")
    table.add_column("Source", style="white")
    table.add_column("Destination")
    table.add_column("Status", justify="center")

    for entry in entries:
        status = "[green]✓[/green]" if entry.success else "[red]✗[/red]"
        dt = entry.timestamp_dt.strftime("%Y-%m-%d %H:%M")
        dest = os.path.basename(entry.destination_path) if entry.destination_path else "—"
        table.add_row(str(entry.id), dt, entry.action_type, entry.source_name, dest, status)

    console.print(table)


@history.command("stats")
@click.option("--days", "-d", default=30, help="Period in days")
def history_stats(days: int):
    """Show action statistics."""
    from sortmeout.core.history import get_history

    hist = get_history()
    stats = hist.get_statistics(days=days)

    console.print(
        Panel.fit(
            f"[bold]Action Statistics — Last {days} days[/bold]\n\n"
            f"Total actions: {stats['total_actions']}\n"
            f"Successful: {stats['successful']}\n"
            f"Errors: {stats['errors']}\n"
            f"Success rate: {stats['success_rate']}%",
            title="Statistics",
        )
    )

    if stats.get("by_action_type"):
        console.print("\n[bold]By Action Type:[/bold]")
        for action_type, count in stats["by_action_type"].items():
            console.print(f"  {action_type}: {count}")

    if stats.get("by_rule"):
        console.print("\n[bold]Top Rules:[/bold]")
        for rule_name, count in list(stats["by_rule"].items())[:10]:
            console.print(f"  {rule_name}: {count}")


@history.command("export")
@click.argument("output", type=click.Path())
@click.option("--days", "-d", type=int, help="Only export last N days")
def history_export(output: str, days: int):
    """Export history to JSON file."""
    from sortmeout.core.history import get_history

    hist = get_history()
    count = hist.export_json(output, days=days)
    console.print(f"[green]Exported {count} entries to: {output}[/green]")


@history.command("cleanup")
@click.option("--days", "-d", default=90, help="Delete entries older than N days")
@click.confirmation_option(prompt="Delete old history entries?")
def history_cleanup(days: int):
    """Clean up old history entries."""
    from sortmeout.core.history import get_history

    hist = get_history()
    deleted = hist.cleanup(max_age_days=days)
    console.print(f"[green]Deleted {deleted} old entries.[/green]")


@history.command("undo")
@click.option("--id", "entry_id", type=int, help="Undo specific entry by ID")
def history_undo(entry_id: int):
    """Undo the last action (or a specific one by ID)."""
    from sortmeout.core.history import get_history

    hist = get_history()

    if entry_id:
        result = hist.undo_entry(entry_id)
    else:
        result = hist.undo_last()

    if result["success"]:
        console.print(f"[green]✓ {result['message']}[/green]")
    else:
        console.print(f"[red]✗ {result['message']}[/red]")


# ========================================
# Template commands
# ========================================


@main.group()
def template():
    """Browse and apply rule templates."""
    pass


@template.command("list")
@click.option("--category", "-c", type=str, help="Filter by category")
def template_list(category: str):
    """List available rule templates."""
    from sortmeout.core.templates import get_templates

    templates = get_templates()
    if category:
        templates = [t for t in templates if t["category"].lower() == category.lower()]

    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return

    table = Table(title="Rule Templates")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Description")

    for i, tmpl in enumerate(templates, 1):
        table.add_row(str(i), tmpl["name"], tmpl["category"], tmpl["description"])

    console.print(table)


@template.command("show")
@click.argument("name")
def template_show(name: str):
    """Show details of a template."""
    from sortmeout.core.templates import get_templates

    templates = get_templates()
    tmpl = next((t for t in templates if t["name"].lower() == name.lower()), None)

    if not tmpl:
        # Try partial match
        tmpl = next((t for t in templates if name.lower() in t["name"].lower()), None)

    if not tmpl:
        console.print(f"[red]Template not found: {name}[/red]")
        return

    console.print(
        Panel.fit(
            f"[bold]{tmpl['name']}[/bold]\n\n"
            f"Category: {tmpl['category']}\n"
            f"Description: {tmpl['description']}\n"
            f"Match mode: {tmpl.get('match_mode', 'all')}\n"
            f"Suggested folder: {tmpl.get('folder_hint', '~/Downloads')}\n\n"
            f"Conditions: {len(tmpl.get('conditions', []))}\n"
            f"Actions: {len(tmpl.get('actions', []))}",
            title="Template Details",
        )
    )

    if tmpl.get("conditions"):
        console.print("\n[bold]Conditions:[/bold]")
        for c in tmpl["conditions"]:
            console.print(
                f"  • {c.get('attribute', '?')} {c.get('operator', '?')} {c.get('value', '')}"
            )

    if tmpl.get("actions"):
        console.print("\n[bold]Actions:[/bold]")
        for a in tmpl["actions"]:
            params = a.get("params", {})
            param_str = ", ".join(f"{k}={v}" for k, v in params.items())
            console.print(f"  • {a.get('action_type', '?')} ({param_str})")


@template.command("apply")
@click.argument("name")
@click.argument("folder", type=click.Path(exists=True))
@click.pass_context
def template_apply(ctx, name: str, folder: str):
    """Apply a template to a folder."""
    from sortmeout.core.templates import get_templates, template_to_rule_dict

    templates = get_templates()
    tmpl = next((t for t in templates if t["name"].lower() == name.lower()), None)
    if not tmpl:
        tmpl = next((t for t in templates if name.lower() in t["name"].lower()), None)

    if not tmpl:
        console.print(f"[red]Template not found: {name}[/red]")
        return

    app = SortMeOut(config_path=ctx.obj.get("config"))
    app.add_folder(folder)

    rule_data = template_to_rule_dict(tmpl, folder)

    rule = Rule(
        name=rule_data["name"],
        conditions=[
            Condition(c["attribute"], c["operator"], c.get("value", ""))
            for c in rule_data.get("conditions", [])
        ],
        actions=[
            Action(a["action_type"], **a.get("params", {})) for a in rule_data.get("actions", [])
        ],
    )

    if app.add_rule(folder, rule):
        console.print(f"[green]Applied template '{tmpl['name']}' to {folder}[/green]")
    else:
        console.print(f"[yellow]Template may already be applied.[/yellow]")


# ========================================
# Schedule commands
# ========================================


@main.group()
def schedule():
    """Manage scheduled rules."""
    pass


@schedule.command("list")
@click.pass_context
def schedule_list(ctx):
    """List all scheduled rules."""
    from sortmeout.core.scheduler import Scheduler, ScheduledRule

    sched = Scheduler()

    if not sched.schedules:
        console.print("[yellow]No scheduled rules configured.[/yellow]")
        return

    table = Table(title="Scheduled Rules")
    table.add_column("Rule", style="cyan")
    table.add_column("Folder")
    table.add_column("Interval", style="magenta")
    table.add_column("Enabled", justify="center")
    table.add_column("Last Run")
    table.add_column("Runs", justify="right")

    for s in sched.schedules:
        enabled = "[green]✓[/green]" if s.enabled else "[red]✗[/red]"
        last = s.last_run.strftime("%Y-%m-%d %H:%M") if s.last_run else "Never"
        table.add_row(
            s.name or s.rule_id,
            os.path.basename(s.folder),
            s.interval.value,
            enabled,
            last,
            str(s.run_count),
        )

    console.print(table)


@schedule.command("add")
@click.argument("rule_id")
@click.argument("folder", type=click.Path(exists=True))
@click.option(
    "--interval",
    "-i",
    default="daily",
    type=click.Choice(
        [
            "5min",
            "15min",
            "30min",
            "hourly",
            "2hours",
            "6hours",
            "12hours",
            "daily",
            "weekly",
            "monthly",
        ]
    ),
    help="Schedule interval",
)
@click.option("--name", "-n", type=str, help="Display name")
def schedule_add(rule_id: str, folder: str, interval: str, name: str):
    """Add a scheduled rule."""
    from sortmeout.core.scheduler import Scheduler, ScheduledRule, ScheduleInterval

    sched = Scheduler()
    scheduled = ScheduledRule(
        rule_id=rule_id,
        folder=folder,
        interval=ScheduleInterval(interval),
        name=name or rule_id,
    )
    sched.add_schedule(scheduled)
    console.print(f"[green]Scheduled '{name or rule_id}' to run {interval}.[/green]")


@schedule.command("remove")
@click.argument("rule_id")
def schedule_remove(rule_id: str):
    """Remove a scheduled rule."""
    from sortmeout.core.scheduler import Scheduler

    sched = Scheduler()
    if sched.remove_schedule(rule_id):
        console.print(f"[green]Removed schedule for: {rule_id}[/green]")
    else:
        console.print(f"[red]Schedule not found: {rule_id}[/red]")


@schedule.command("status")
def schedule_status():
    """Show scheduler status."""
    from sortmeout.core.scheduler import Scheduler

    sched = Scheduler()
    running = sched.is_running if hasattr(sched, "is_running") else False

    console.print(
        Panel.fit(
            f"[bold]Scheduler Status[/bold]\n\n"
            f"Running: {'Yes' if running else 'No'}\n"
            f"Scheduled rules: {len(sched.schedules)}",
            title="Scheduler",
        )
    )


# Image Studio
@main.command("images")
def images_command():
    """Open the Image Studio (AI generation + editing)."""
    try:
        from sortmeout.gui.image_window import main as image_main

        image_main()
    except ImportError as e:
        console.print(f"[red]Image Studio requires PyObjC: {e}[/red]")
        console.print("Install with: pip install pyobjc-framework-Cocoa")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
