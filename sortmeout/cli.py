"""
Command-line interface for SortMeOut.

Provides a full-featured CLI for managing file automation rules.
"""

from __future__ import annotations

import json
import os
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
from sortmeout.utils.logger import setup_logging
from sortmeout.macos.trash import get_trash_info, empty_trash, TrashManager

console = Console()


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
        console.print("[yellow]No folders configured. Use 'sortmeout folder add' to add folders.[/yellow]")
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
    """Stop watching folders."""
    console.print("[yellow]Stopping SortMeOut...[/yellow]")
    # In a real implementation, this would communicate with a running daemon
    console.print("[green]Stopped[/green]")


@main.command()
@click.pass_context
def status(ctx):
    """Show current status."""
    app = SortMeOut(config_path=ctx.obj.get("config"))

    folders = app.get_folders()
    stats = app.get_stats()

    # Status panel
    console.print(Panel.fit(
        f"[bold]SortMeOut Status[/bold]\n\n"
        f"Folders: {len(folders)}\n"
        f"Running: {'Yes' if app.is_running else 'No'}\n"
        f"Preview Mode: {'Yes' if app.preview_mode else 'No'}",
        title="Status",
    ))

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
    console.print(Panel.fit(
        f"[bold]{rule.name}[/bold]\n\n"
        f"Enabled: {'Yes' if rule.enabled else 'No'}\n"
        f"Match Mode: {rule.match_mode.value}\n"
        f"Continue Processing: {'Yes' if rule.continue_processing else 'No'}\n"
        f"Description: {rule.description or 'None'}",
        title="Rule Details",
    ))

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

    console.print(Panel.fit(
        f"[bold]Trash Status[/bold]\n\n"
        f"Items: {info.item_count}\n"
        f"Size: {info.size_human}\n"
        f"Oldest: {info.oldest_item_date.strftime('%Y-%m-%d') if info.oldest_item_date else 'N/A'}\n"
        f"Newest: {info.newest_item_date.strftime('%Y-%m-%d') if info.newest_item_date else 'N/A'}",
        title="Trash",
    ))


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
    console.print(Panel.fit(
        f"[bold]File: {os.path.basename(file)}[/bold]\n\n"
        f"Size: {file_info.get('size_human', 'N/A')}\n"
        f"Extension: {file_info.get('extension', 'N/A')}\n"
        f"Kind: {file_info.get('kind', 'N/A')}",
        title="File Info",
    ))

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


if __name__ == "__main__":
    main()
