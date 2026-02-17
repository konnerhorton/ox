"""Command-line interface for ox."""

import sqlite3

import click
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_ox
from rich.console import Console
from rich import box
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

from ox.parse import process_node
from ox.data import TrainingLog
from ox.db import create_db
from ox.plugins import GENERATOR_PLUGINS, load_plugins
from ox.reports import get_all_reports, parse_report_args, report_usage

console = Console()

DEFAULT_TABLE_BOX = box.SIMPLE


def parse_file(file_path: Path) -> TrainingLog:
    """Parse a training log file and return TrainingLog object.

    Args:
        file_path: Path to the training log file

    Returns:
        TrainingLog object with parsed sessions
    """
    language = Language(tree_sitter_ox.language())
    parser = Parser(language)

    with open(file_path, "r") as f:
        data = bytes(f.read(), encoding="utf-8")

    tree = parser.parse(data)
    root_node = tree.root_node

    entries = []
    for child in root_node.children:
        entry = process_node(child)
        if entry:
            entries.append(entry)

    return TrainingLog(tuple(entries))


def show_help():
    """Display help message with available commands."""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]")
    console.print(
        "  [green]stats[/green]              - Show summary statistics for all exercises"
    )
    console.print(
        "  [green]history[/green] EXERCISE   - Show training history for an exercise"
    )
    console.print(
        "  [green]report[/green]             - List available reports (or run one)"
    )
    console.print(
        "  [green]generate[/green]           - List available generators (or run one)"
    )
    console.print(
        "  [green]query[/green] SQL          - Run a SQL query against your training data"
    )
    console.print(
        "  [green]tables[/green]             - Show available tables and views"
    )
    console.print("  [green]reload[/green]             - Reload the log file from disk")
    console.print("  [green]help[/green]               - Show this help message")
    console.print("  [green]exit[/green] or [green]quit[/green]     - Exit the program")
    console.print()


def show_stats(log: TrainingLog):
    """Show summary statistics for completed exercises.

    Only includes completed sessions (flag="*"), not planned sessions.
    """
    # Collect all unique exercises
    exercises = {}
    for date, movement in log.movements():
        if movement.name not in exercises:
            exercises[movement.name] = []
        exercises[movement.name].append((date, movement))

    table = Table(title="Training Statistics", box=DEFAULT_TABLE_BOX)
    table.add_column("Exercise", style="cyan")
    table.add_column("Sessions", style="magenta")
    table.add_column("Total Reps", style="green")
    table.add_column("Last Session", style="yellow")

    for exercise_name, sessions in sorted(exercises.items()):
        total_reps = sum(m.total_reps for _, m in sessions)
        last_date = max(d for d, _ in sessions)

        table.add_row(
            exercise_name, str(len(sessions)), str(total_reps), str(last_date)
        )

    console.print(table)
    console.print(f"\n[bold]Completed sessions:[/bold] {len(log.completed_sessions)}")
    console.print(f"[bold]Planned sessions:[/bold] {len(log.planned_sessions)}")
    console.print(f"[bold]Unique exercises:[/bold] {len(exercises)}\n")


def show_history(log: TrainingLog, exercise: str):
    """Show training history for a specific exercise."""
    history = log.movement_history(exercise)

    if not history:
        console.print(f"[yellow]No history found for '{exercise}'[/yellow]\n")
        return

    table = Table(title=f"History: {exercise}", box=DEFAULT_TABLE_BOX)
    table.add_column("Date", style="cyan")
    table.add_column("Sets × Reps", style="magenta")
    table.add_column("Top Weight", style="green")
    table.add_column("Volume", style="yellow")

    for date, movement in history:
        sets_reps = " + ".join([str(s.reps) for s in movement.sets])
        top_weight = str(movement.top_set_weight) if movement.top_set_weight else "BW"
        volume = str(movement.total_volume()) if movement.total_volume() else "—"

        table.add_row(str(date), sets_reps, top_weight, volume)

    console.print(table)
    console.print()  # Blank line after table


def show_query(conn: sqlite3.Connection, sql: str):
    """Execute a SQL query and display results as a rich table."""
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        if not rows:
            console.print("[yellow]No results.[/yellow]\n")
            return

        columns = [desc[0] for desc in cursor.description]

        table = Table(box=DEFAULT_TABLE_BOX)
        for col in columns:
            table.add_column(col, style="cyan")

        for row in rows:
            table.add_row(*(str(v) for v in row))

        console.print(table)
        console.print(f"\n[dim]{len(rows)} row(s)[/dim]\n")
    except Exception as e:
        console.print(f"[red]SQL error: {e}[/red]\n")


def show_tables(conn: sqlite3.Connection):
    """Show available tables and views."""
    rows = conn.execute(
        "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name"
    ).fetchall()
    for type_, name in rows:
        console.print(f"  [green]{name}[/green] ({type_})")
    console.print()


def show_report_list():
    """Show available reports with descriptions and usage."""
    console.print("\n[bold cyan]Available Reports:[/bold cyan]")
    for name, entry in get_all_reports().items():
        usage = report_usage(name, entry)
        console.print(f"  [green]{name}[/green] - {entry['description']}")
        console.print(f"    Usage: {usage}")
    console.print()


def render_report(columns: list[str], rows: list[tuple]):
    """Render (columns, rows) as a rich table."""
    if not rows:
        console.print("[yellow]No results.[/yellow]\n")
        return

    table = Table(box=DEFAULT_TABLE_BOX)
    for col in columns:
        table.add_column(col, style="cyan")

    for row in rows:
        table.add_row(*(str(v) for v in row))

    console.print(table)
    console.print(f"\n[dim]{len(rows)} row(s)[/dim]\n")


def run_report(conn: sqlite3.Connection, report_name: str, arg_string: str):
    """Look up and execute a report by name."""
    all_reports = get_all_reports()
    if report_name not in all_reports:
        console.print(f"[red]Unknown report: {report_name}[/red]")
        show_report_list()
        return

    entry = all_reports[report_name]

    if not arg_string.strip() and any(p.get("required") for p in entry["params"]):
        usage = report_usage(report_name, entry)
        console.print(f"[yellow]Usage: {usage}[/yellow]\n")
        return

    try:
        kwargs = parse_report_args(entry["params"], arg_string)
        columns, rows = entry["fn"](conn, **kwargs)
        render_report(columns, rows)
    except ValueError as e:
        console.print(f"[red]{e}[/red]\n")


def show_generator_list():
    """Show available generators with descriptions and usage."""
    if not GENERATOR_PLUGINS:
        console.print("[yellow]No generator plugins installed.[/yellow]\n")
        return
    console.print("\n[bold cyan]Available Generators:[/bold cyan]")
    for name, entry in GENERATOR_PLUGINS.items():
        usage = report_usage(name, entry, command="generate")
        console.print(f"  [green]{name}[/green] - {entry['description']}")
        console.print(f"    Usage: {usage}")
    console.print()


def run_generator(conn: sqlite3.Connection, gen_name: str, arg_string: str):
    """Look up and execute a generator by name."""
    if gen_name not in GENERATOR_PLUGINS:
        console.print(f"[red]Unknown generator: {gen_name}[/red]")
        show_generator_list()
        return

    entry = GENERATOR_PLUGINS[gen_name]

    if not arg_string.strip() and any(p.get("required") for p in entry["params"]):
        usage = report_usage(gen_name, entry, command="generate")
        console.print(f"[yellow]Usage: {usage}[/yellow]\n")
        return

    try:
        kwargs = parse_report_args(entry["params"], arg_string)
        if entry.get("needs_db"):
            output = entry["fn"](conn, **kwargs)
        else:
            output = entry["fn"](**kwargs)
        console.print(output)
    except ValueError as e:
        console.print(f"[red]{e}[/red]\n")


@click.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.version_option(version="0.2.0")
def cli(file):
    """Interactive training log analyzer.

    FILE: Path to training log file
    """
    # Parse the file once
    try:
        console.print(f"[cyan]Loading {file}...[/cyan]")
        log = parse_file(file)
        db = create_db(log)
        load_plugins()
        console.print(
            f"[green]✓[/green] Loaded {len(log.completed_sessions)} completed, "
            f"{len(log.planned_sessions)} planned sessions\n"
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Error loading file: {e}", style="red")
        raise click.Abort()

    # Setup tab completion for commands
    commands = ["history", "stats", "report", "reload", "generate", "query", "tables", "help", "exit", "quit"]
    completer = WordCompleter(commands, ignore_case=True)

    # Create prompt session
    session = PromptSession(completer=completer)

    console.print("Type 'help' for commands, 'exit' to quit\n")

    # Main REPL loop
    while True:
        try:
            user_input = session.prompt("ox> ").strip()

            if not user_input:
                continue  # Empty input, show prompt again

            # Parse the command
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            # Handle commands
            if command == "exit" or command == "quit":
                console.print("[cyan]Goodbye![/cyan]")
                break

            elif command == "help":
                show_help()

            elif command == "stats":
                show_stats(log)

            elif command == "history":
                if not args:
                    console.print("[yellow]Usage: history EXERCISE[/yellow]")
                else:
                    show_history(log, args)

            elif command == "report":
                if not args:
                    show_report_list()
                else:
                    parts2 = args.split(maxsplit=1)
                    report_name = parts2[0]
                    report_args = parts2[1] if len(parts2) > 1 else ""
                    run_report(db, report_name, report_args)

            elif command == "generate":
                if not args:
                    show_generator_list()
                else:
                    parts2 = args.split(maxsplit=1)
                    gen_name = parts2[0]
                    gen_args = parts2[1] if len(parts2) > 1 else ""
                    run_generator(db, gen_name, gen_args)

            elif command == "query":
                if not args:
                    console.print("[yellow]Usage: query SELECT ...[/yellow]")
                else:
                    show_query(db, args)

            elif command == "tables":
                show_tables(db)

            elif command == "reload":
                try:
                    console.print(f"[cyan]Reloading {file}...[/cyan]")
                    log = parse_file(file)
                    db.close()
                    db = create_db(log)
                    console.print(
                        f"[green]✓[/green] Loaded {len(log.completed_sessions)} completed, "
                        f"{len(log.planned_sessions)} planned sessions\n"
                    )
                except Exception as e:
                    console.print(f"[red]✗[/red] Error reloading file: {e}\n")

            else:
                console.print(f"[red]Unknown command: {command}[/red]")
                console.print("Type 'help' for available commands")

        except KeyboardInterrupt:
            continue  # Ctrl+C just cancels current line
        except EOFError:
            break  # Ctrl+D exits

    db.close()


if __name__ == "__main__":
    cli()
