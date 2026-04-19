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

from ox.parse import process_include_directive, process_plugin_directive, process_node
from ox.data import Diagnostic, Note, StoredQuery, TrainingLog, TrainingSession, WeighIn
from ox.db import create_db
from ox.lint import collect_diagnostics
from ox.plugins import (
    PLUGINS,
    USER_PLUGINS,
    PlotResult,
    PluginContext,
    TableResult,
    TextResult,
    load_plugins,
)
from ox.sql_utils import parse_plugin_args, plugin_usage

console = Console()

DEFAULT_TABLE_BOX = box.SIMPLE


def _parse_single_file(
    file_path: Path, parser: Parser
) -> tuple[list, list, list, list, list, list[str], list[str]]:
    """Parse a single .ox file without resolving includes.

    Returns:
        Tuple of (sessions, notes, queries, weigh_ins, diagnostics, include_paths, plugin_paths)
    """
    with open(file_path, "r") as f:
        data = bytes(f.read(), encoding="utf-8")

    tree = parser.parse(data)
    root_node = tree.root_node

    entries = []
    log_notes = []
    log_queries = []
    log_weigh_ins = []
    include_paths = []
    plugin_paths = []
    for child in root_node.children:
        if child.type == "include_directive":
            include_paths.append(process_include_directive(child))
            continue
        if child.type == "plugin_directive":
            plugin_paths.append(process_plugin_directive(child))
            continue
        result = process_node(child)
        if isinstance(result, TrainingSession):
            entries.append(result)
        elif isinstance(result, Note):
            log_notes.append(result)
        elif isinstance(result, StoredQuery):
            log_queries.append(result)
        elif isinstance(result, WeighIn):
            log_weigh_ins.append(result)

    diagnostics = list(collect_diagnostics(tree))
    return (
        entries,
        log_notes,
        log_queries,
        log_weigh_ins,
        diagnostics,
        include_paths,
        plugin_paths,
    )


def _load_recursive(
    file_path: Path,
    parser: Parser,
    visited: set[Path],
) -> tuple[list, list, list, list, list, list]:
    """Recursively load a file and its includes with cycle detection.

    Returns:
        Tuple of (sessions, notes, queries, weigh_ins, diagnostics, plugin_paths)
    """
    abs_path = file_path.resolve()

    if abs_path in visited:
        diag = Diagnostic(
            line=1,
            col=0,
            end_line=1,
            end_col=0,
            message=f"Circular include detected: {file_path}",
            severity="warning",
        )
        return [], [], [], [], [diag], []

    visited.add(abs_path)

    if not abs_path.exists():
        diag = Diagnostic(
            line=1,
            col=0,
            end_line=1,
            end_col=0,
            message=f"Included file not found: {file_path}",
            severity="warning",
        )
        return [], [], [], [], [diag], []

    entries, notes, queries, weigh_ins, diagnostics, include_paths, plugin_paths = (
        _parse_single_file(abs_path, parser)
    )

    for inc_path in include_paths:
        resolved = (abs_path.parent / inc_path).resolve()
        (
            inc_entries,
            inc_notes,
            inc_queries,
            inc_weigh_ins,
            inc_diagnostics,
            inc_plugins,
        ) = _load_recursive(Path(resolved), parser, visited)
        entries.extend(inc_entries)
        notes.extend(inc_notes)
        queries.extend(inc_queries)
        weigh_ins.extend(inc_weigh_ins)
        diagnostics.extend(inc_diagnostics)
        plugin_paths.extend(inc_plugins)

    return entries, notes, queries, weigh_ins, diagnostics, plugin_paths


def parse_file(file_path: Path) -> TrainingLog:
    """Parse a training log file and return TrainingLog object.

    Resolves @include directives recursively with cycle detection.

    Args:
        file_path: Path to the training log file

    Returns:
        TrainingLog object with parsed sessions
    """
    language = Language(tree_sitter_ox.language())
    parser = Parser(language)

    entries, notes, queries, weigh_ins, diagnostics, plugin_paths = _load_recursive(
        file_path, parser, visited=set()
    )

    return TrainingLog(
        tuple(entries),
        tuple(notes),
        tuple(diagnostics),
        tuple(queries),
        tuple(weigh_ins),
        tuple(plugin_paths),
    )


def show_help():
    """Display help message with available commands."""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]")
    console.print(
        "  [green]run[/green] NAME [ARGS]   - Run a plugin (or list all plugins)"
    )
    console.print(
        "  [green]query[/green] SQL          - Run a SQL query or a stored query by name"
    )
    console.print(
        "  [green]tables[/green]             - Show available tables and views"
    )
    console.print("  [green]reload[/green]             - Reload the log file from disk")
    console.print(
        "  [green]lint[/green]               - Show parse errors in the log file"
    )
    console.print("  [green]help[/green]               - Show this help message")
    console.print("  [green]exit[/green] or [green]quit[/green]     - Exit the program")
    console.print()


def show_plugin_list():
    """Show available plugins with descriptions and usage."""
    if not PLUGINS:
        console.print("[yellow]No plugins installed.[/yellow]\n")
        return
    console.print("\n[bold cyan]Available Plugins:[/bold cyan]")
    for name, entry in PLUGINS.items():
        usage = plugin_usage(name, entry)
        console.print(f"  [green]{name}[/green] - {entry['description']}")
        console.print(f"    Usage: {usage}")
    console.print()


def render_result(result):
    """Render a plugin result to the console."""
    if isinstance(result, TableResult):
        if not result.rows:
            console.print("[yellow]No results.[/yellow]\n")
            return
        table = Table(box=DEFAULT_TABLE_BOX)
        for col in result.columns:
            table.add_column(col, style="cyan")
        for row in result.rows:
            table.add_row(*(str(v) for v in row))
        console.print(table)
        console.print(f"\n[dim]{len(result.rows)} row(s)[/dim]\n")
    elif isinstance(result, TextResult):
        console.print(result.text)
    elif isinstance(result, PlotResult):
        for line in result.lines:
            console.print(line)
        console.print()


def run_plugin(ctx: PluginContext, plugin_name: str, arg_string: str):
    """Look up and execute a plugin by name."""
    if plugin_name not in PLUGINS:
        console.print(f"[red]Unknown plugin: {plugin_name}[/red]")
        show_plugin_list()
        return

    entry = PLUGINS[plugin_name]

    if not arg_string.strip() and any(p.get("required") for p in entry["params"]):
        usage = plugin_usage(plugin_name, entry)
        console.print(f"[yellow]Usage: {usage}[/yellow]\n")
        return

    try:
        kwargs = parse_plugin_args(entry["params"], arg_string)
        result = entry["fn"](ctx, **kwargs)
        render_result(result)
    except ValueError as e:
        console.print(f"[red]{e}[/red]\n")


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


def show_tables(conn: sqlite3.Connection, headers: bool = False):
    """Show available tables and views."""
    rows = conn.execute(
        "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name"
    ).fetchall()
    for type_, name in rows:
        console.print(f"  [green]{name}[/green] ({type_})")
        if headers:
            cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
            for col in cols:
                # col: (cid, name, type, notnull, dflt_value, pk)
                console.print(f"    [dim]{col[1]}[/dim]  {col[2]}")
    console.print()


@click.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.version_option(version="0.3.0")
def cli(file):
    """Interactive training log analyzer.

    FILE: Path to training log file
    """
    # Parse the file once
    try:
        console.print(f"[cyan]Loading {file}...[/cyan]")
        log = parse_file(file)
        db = create_db(log)
        load_plugins(log, file)
        ctx = PluginContext(db=db, log=log)
        console.print(
            f"[green]✓[/green] Loaded {len(log.completed_sessions)} completed, "
            f"{len(log.planned_sessions)} planned sessions, "
            f"{len(log.weigh_ins)} weigh-in(s)"
        )
        if USER_PLUGINS:
            console.print(
                f"[green]✓[/green] Loaded user plugins: {', '.join(sorted(USER_PLUGINS))}\n"
            )
        else:
            console.print()
        if log.diagnostics:
            console.print(
                f"[yellow]Warning: {len(log.diagnostics)} parse error(s). "
                "Run 'lint' for details.[/yellow]\n"
            )
    except Exception as e:
        console.print(f"[red]✗[/red] Error loading file: {e}", style="red")
        raise click.Abort()

    # Setup tab completion for commands + plugin names
    commands = [
        "run",
        "query",
        "tables",
        "reload",
        "lint",
        "help",
        "exit",
        "quit",
    ] + list(PLUGINS.keys())
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

            elif command == "run":
                if not args:
                    show_plugin_list()
                else:
                    parts2 = args.split(maxsplit=1)
                    plugin_name = parts2[0]
                    plugin_args = parts2[1] if len(parts2) > 1 else ""
                    run_plugin(ctx, plugin_name, plugin_args)

            elif command == "query":
                if not args:
                    console.print(
                        "[yellow]Usage: query <name> | query SELECT ...[/yellow]"
                    )
                elif " " not in args.strip():
                    rows = db.execute(
                        "SELECT sql FROM queries WHERE name = ?", (args.strip(),)
                    ).fetchall()
                    if rows:
                        show_query(db, rows[0][0])
                    else:
                        available = [
                            r[0]
                            for r in db.execute(
                                "SELECT name FROM queries ORDER BY name"
                            ).fetchall()
                        ]
                        if available:
                            console.print(
                                f"[red]Unknown query '{args.strip()}'. Available: {', '.join(available)}[/red]"
                            )
                        else:
                            console.print(
                                "[red]No stored queries found in log file.[/red]"
                            )
                else:
                    show_query(db, args)

            elif command == "tables":
                show_tables(db, headers="-h" in args.split())

            elif command == "reload":
                try:
                    console.print(f"[cyan]Reloading {file}...[/cyan]")
                    log = parse_file(file)
                    db.close()
                    db = create_db(log)
                    load_plugins(log, file)
                    ctx = PluginContext(db=db, log=log)
                    console.print(
                        f"[green]✓[/green] Loaded {len(log.completed_sessions)} completed, "
                        f"{len(log.planned_sessions)} planned sessions, "
                        f"{len(log.weigh_ins)} weigh-in(s)"
                    )
                    if USER_PLUGINS:
                        console.print(
                            f"[green]✓[/green] Loaded user plugins: {', '.join(sorted(USER_PLUGINS))}"
                        )
                    else:
                        console.print()
                    if log.diagnostics:
                        console.print(
                            f"[yellow]Warning: {len(log.diagnostics)} parse error(s). "
                            "Run 'lint' for details.[/yellow]\n"
                        )
                    # Update completer with any new plugins
                    commands = [
                        "run",
                        "query",
                        "tables",
                        "reload",
                        "lint",
                        "help",
                        "exit",
                        "quit",
                    ] + list(PLUGINS.keys())
                    session.completer = WordCompleter(commands, ignore_case=True)
                except Exception as e:
                    console.print(f"[red]✗[/red] Error reloading file: {e}\n")

            elif command == "lint":
                if not log.diagnostics:
                    console.print("[green]No parse errors found.[/green]\n")
                else:
                    for d in log.diagnostics:
                        console.print(f"Line {d.line}, col {d.col}: {d.message}")
                    console.print()

            elif command in PLUGINS:
                # Allow running plugins directly by name without "run" prefix
                run_plugin(ctx, command, args)

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
