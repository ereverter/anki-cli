"""Anki flashcard management CLI."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from anki_cli.client import AnkiClient, AnkiError

app = typer.Typer(no_args_is_help=True)
console = Console()


def _parse_fields(raw: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for f in raw:
        if "=" not in f:
            console.print(f"[red]Invalid field format:[/red] {f} (expected key=value)")
            raise typer.Exit(1)
        key, value = f.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _deck_table(stats: dict[str, dict], title: str = "Anki Decks") -> Table:
    table = Table(title=title)
    table.add_column("Deck", style="cyan")
    table.add_column("New", justify="right", style="green")
    table.add_column("Learn", justify="right", style="yellow")
    table.add_column("Review", justify="right", style="blue")
    table.add_column("Total", justify="right", style="bold")
    for name in sorted(stats):
        s = stats[name]
        table.add_row(
            name,
            str(s["new_count"]),
            str(s["learn_count"]),
            str(s["review_count"]),
            str(s["total_in_deck"]),
        )
    return table


def _render_note_panel(note: dict[str, Any]) -> Panel:
    content = f"[bold]Model:[/bold] {note['modelName']}\n"
    content += f"[bold]Tags:[/bold] {' '.join(note['tags']) or 'none'}\n\n"
    for name, data in note["fields"].items():
        content += f"[bold cyan]{name}:[/bold cyan]\n{data['value']}\n\n"
    return Panel(content.strip(), title=f"Note {note['noteId']}")


@app.command()
def decks() -> None:
    """List decks with review stats."""
    client = AnkiClient()
    console.print(_deck_table(client.deck_stats()))


@app.command()
def models() -> None:
    """List available note types."""
    client = AnkiClient()
    names = client.model_names()

    table = Table(title="Note Types")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Model", style="cyan")
    for i, name in enumerate(sorted(names), 1):
        table.add_row(str(i), name)
    console.print(table)


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", text)


def _fuzzy_score(query: str, note: dict[str, Any]) -> float:
    from rapidfuzz import fuzz

    searchable = _strip_html(" ".join(v["value"] for v in note["fields"].values())).lower()
    words = searchable.split()
    if not words:
        return 0.0
    query_words = query.lower().split()
    return sum(max(fuzz.ratio(qw, w) for w in words) for qw in query_words) / len(query_words)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Anki search query")],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 20,
    brief: Annotated[bool, typer.Option("--brief", "-B", help="Truncated table view")] = False,
    fuzzy: Annotated[bool, typer.Option("--fuzzy", "-f", help="Fuzzy text search")] = False,
) -> None:
    """Search notes using Anki query syntax."""
    client = AnkiClient()

    if fuzzy:
        all_ids = client.find_notes("deck:*")
        if not all_ids:
            console.print("[yellow]No notes found.[/yellow]")
            return
        all_notes = client.notes_info(all_ids)
        scored = [(note, _fuzzy_score(query, note)) for note in all_notes]
        scored = [(note, score) for note, score in scored if score > 70]
        scored.sort(key=lambda x: x[1], reverse=True)
        if not scored:
            console.print("[yellow]No notes found.[/yellow]")
            return
        infos = [note for note, _ in scored[:limit]]
        total = len(scored)
    else:
        ids = client.find_notes(query)
        if not ids:
            console.print("[yellow]No notes found.[/yellow]")
            return
        infos = client.notes_info(ids[:limit])
        total = len(ids)

    if brief:
        table = Table(title=f"Search: {query} ({total} results)")
        table.add_column("Note ID", style="dim")
        table.add_column("Model", style="magenta")
        table.add_column("Tags", style="green")
        table.add_column("Fields", style="cyan", max_width=60)
        for note in infos:
            fields_preview = " | ".join(
                f"{k}: {v['value'][:40]}" for k, v in note["fields"].items()
            )
            table.add_row(
                str(note["noteId"]),
                note["modelName"],
                " ".join(note["tags"]),
                fields_preview,
            )
        console.print(table)
    else:
        console.print(f"[bold]Search: {query}[/bold] ({total} results)\n")
        for note in infos:
            console.print(_render_note_panel(note))
    if total > limit:
        console.print(f"[dim]Showing {limit} of {total} results.[/dim]")


@app.command()
def show(
    note_ids: Annotated[list[int], typer.Argument(help="Note ID(s) to display")],
) -> None:
    """Show full details of one or more notes."""
    client = AnkiClient()
    infos = client.notes_info(note_ids)
    if not infos:
        console.print("[red]No notes found.[/red]")
        raise typer.Exit(1)

    for note in infos:
        console.print(_render_note_panel(note))


@app.command()
def add(
    deck: Annotated[str, typer.Option("--deck", "-d", help="Target deck")],
    fields: Annotated[list[str], typer.Option("--field", "-f", help="Field as key=value")],
    model: Annotated[str, typer.Option("--model", "-m", help="Note type")] = "Basic",
    tags: Annotated[list[str] | None, typer.Option("--tag", "-t", help="Tags to add")] = None,
) -> None:
    """Add a new note."""
    client = AnkiClient()
    note_id = client.add_note(deck, model, _parse_fields(fields), tags)
    console.print(f"[green]Note created:[/green] {note_id}")


@app.command()
def edit(
    note_id: Annotated[int, typer.Argument(help="Note ID to edit")],
    fields: Annotated[list[str], typer.Option("--field", "-f", help="Field as key=value")],
) -> None:
    """Edit fields of an existing note."""
    client = AnkiClient()
    client.update_note_fields(note_id, _parse_fields(fields))
    console.print(f"[green]Note {note_id} updated.[/green]")


@app.command()
def delete(
    note_id: Annotated[int, typer.Argument(help="Note ID to delete")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a note."""
    if not yes:
        typer.confirm(f"Delete note {note_id}?", abort=True)
    client = AnkiClient()
    client.delete_notes([note_id])
    console.print(f"[green]Note {note_id} deleted.[/green]")


@app.command()
def tag(
    note_id: Annotated[int | None, typer.Argument(help="Note ID")] = None,
    query: Annotated[
        str | None, typer.Option("--query", "-q", help="Anki query to select notes")
    ] = None,
    add_tags: Annotated[list[str] | None, typer.Option("--add", "-a", help="Tags to add")] = None,
    remove_tags: Annotated[
        list[str] | None, typer.Option("--remove", "-r", help="Tags to remove")
    ] = None,
) -> None:
    """Add or remove tags on notes."""
    if not add_tags and not remove_tags:
        console.print("[yellow]Specify --add or --remove tags.[/yellow]")
        raise typer.Exit(1)

    if note_id is not None and query is not None:
        console.print("[red]Specify either a note ID or --query, not both.[/red]")
        raise typer.Exit(1)
    if note_id is None and query is None:
        console.print("[red]Specify a note ID or --query.[/red]")
        raise typer.Exit(1)

    client = AnkiClient()

    if query is not None:
        ids = client.find_notes(query)
        if not ids:
            console.print("[yellow]No notes found.[/yellow]")
            return
    else:
        ids = [note_id]

    if add_tags:
        client.add_tags(ids, " ".join(add_tags))
        console.print(f"[green]Added tags to {len(ids)} note(s):[/green] {', '.join(add_tags)}")
    if remove_tags:
        client.remove_tags(ids, " ".join(remove_tags))
        console.print(
            f"[green]Removed tags from {len(ids)} note(s):[/green] {', '.join(remove_tags)}"
        )


@app.command()
def stats() -> None:
    """Show today's review stats."""
    client = AnkiClient()
    reviewed = client.cards_reviewed_today()
    console.print(Panel(f"[bold green]{reviewed}[/bold green] cards reviewed today", title="Today"))
    console.print(_deck_table(client.deck_stats(), title="Per-Deck Breakdown"))


def _flatten_note(note: dict[str, Any]) -> dict[str, Any]:
    return {
        "noteId": note["noteId"],
        "modelName": note["modelName"],
        "tags": " ".join(note["tags"]),
        "fields": {k: v["value"] for k, v in note["fields"].items()},
    }


def _write_json(notes: list[dict], path: Path) -> None:
    with path.open("w") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def _write_csv(notes: list[dict], path: Path) -> None:
    if not notes:
        return
    field_names = list(notes[0]["fields"].keys())
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["noteId", "modelName", "tags"] + field_names)
        for note in notes:
            writer.writerow(
                [note["noteId"], note["modelName"], note["tags"]]
                + [note["fields"].get(k, "") for k in field_names]
            )


def _read_json(path: Path) -> list[dict]:
    with path.open() as f:
        return json.load(f)


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        meta_cols = {"noteId", "modelName", "tags"}
        notes = []
        for row in reader:
            field_keys = [k for k in row if k not in meta_cols]
            notes.append(
                {
                    "noteId": int(row["noteId"]) if row.get("noteId") else None,
                    "modelName": row.get("modelName", ""),
                    "tags": row.get("tags", ""),
                    "fields": {k: row[k] for k in field_keys},
                }
            )
        return notes


@app.command()
def export(
    query: Annotated[str, typer.Argument(help="Anki search query")],
    file: Annotated[Path, typer.Argument(help="Output file (.json or .csv)")],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max notes")] = 0,
) -> None:
    """Export notes to JSON or CSV."""
    client = AnkiClient()
    ids = client.find_notes(query)
    if not ids:
        console.print("[yellow]No notes found.[/yellow]")
        return

    if limit:
        ids = ids[:limit]
    notes = [_flatten_note(n) for n in client.notes_info(ids)]

    ext = file.suffix.lower()
    if ext == ".json":
        _write_json(notes, file)
    elif ext == ".csv":
        _write_csv(notes, file)
    else:
        console.print(f"[red]Unsupported format:[/red] {ext} (use .json or .csv)")
        raise typer.Exit(1)

    console.print(f"[green]Exported {len(notes)} notes to {file}[/green]")


@app.command("import")
def import_(
    file: Annotated[Path, typer.Argument(help="Input file (.json or .csv)")],
    deck: Annotated[str | None, typer.Option("--deck", "-d", help="Deck for new notes")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without applying")] = False,
) -> None:
    """Import notes from JSON or CSV."""
    ext = file.suffix.lower()
    if ext == ".json":
        notes = _read_json(file)
    elif ext == ".csv":
        notes = _read_csv(file)
    else:
        console.print(f"[red]Unsupported format:[/red] {ext} (use .json or .csv)")
        raise typer.Exit(1)

    client = AnkiClient()
    created = updated = errors = 0

    existing_ids = [n["noteId"] for n in notes if n.get("noteId")]
    current_tags_by_id: dict[int, set[str]] = {}
    if existing_ids:
        for info in client.notes_info(existing_ids):
            current_tags_by_id[info["noteId"]] = set(info["tags"])

    for note in notes:
        note_id = note.get("noteId")
        fields = note["fields"]
        tags = note.get("tags", "").split() if note.get("tags") else []

        if note_id:
            if dry_run:
                console.print(f"  [blue]update[/blue] {note_id}")
            else:
                try:
                    client.update_note_fields(note_id, fields)
                    current = current_tags_by_id.get(note_id, set())
                    desired = set(tags)
                    to_add = desired - current
                    to_remove = current - desired
                    if to_add:
                        client.add_tags([note_id], " ".join(to_add))
                    if to_remove:
                        client.remove_tags([note_id], " ".join(to_remove))
                except AnkiError as exc:
                    console.print(f"  [red]error[/red] {note_id}: {exc}")
                    errors += 1
                    continue
            updated += 1
        else:
            model = note.get("modelName", "Basic")
            if not deck:
                console.print("[red]--deck required for new notes (missing noteId)[/red]")
                raise typer.Exit(1)
            if dry_run:
                console.print(f"  [green]create[/green] {model} → {deck}")
            else:
                try:
                    new_id = client.add_note(deck, model, fields, tags or None)
                    console.print(f"  [green]created[/green] {new_id}")
                except AnkiError as exc:
                    console.print(f"  [red]error[/red]: {exc}")
                    errors += 1
                    continue
            created += 1

    label = "[dim](dry run)[/dim] " if dry_run else ""
    console.print(
        f"\n{label}[green]{created} created[/green],"
        f" [blue]{updated} updated[/blue],"
        f" [red]{errors} errors[/red]"
    )
