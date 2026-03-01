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

from anki_cli.client import AnkiClient, AnkiConnectionError, AnkiError

app = typer.Typer(no_args_is_help=True)
console = Console()


def main() -> None:
    try:
        app()
    except AnkiConnectionError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from None
    except AnkiError as exc:
        console.print(f"[red]Anki error:[/red] {exc}")
        raise SystemExit(1) from None


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
    if not query_words:
        return 0.0
    return sum(max(fuzz.ratio(qw, w) for w in words) for qw in query_words) / len(query_words)


def _render_notes(
    infos: list[dict[str, Any]], total: int, title: str, limit: int, brief: bool
) -> None:
    if brief:
        table = Table(title=f"{title} ({total} results)")
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
        console.print(f"[bold]{title}[/bold] ({total} results)\n")
        for note in infos:
            console.print(_render_note_panel(note))
    if total > limit:
        console.print(f"[dim]Showing {limit} of {total} results.[/dim]")


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Anki search query")],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 20,
    brief: Annotated[bool, typer.Option("--brief", "-B", help="Truncated table view")] = False,
    fuzzy: Annotated[bool, typer.Option("--fuzzy", "-f", help="Fuzzy text search")] = False,
) -> None:
    """Search notes using Anki query syntax."""
    if fuzzy and not query.strip():
        console.print("[red]Fuzzy search requires a non-empty query.[/red]")
        raise typer.Exit(2)

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

    _render_notes(infos, total, f"Search: {query}", limit, brief)


@app.command("list")
def list_(
    deck: Annotated[str | None, typer.Option("--deck", "-d", help="Filter by deck")] = None,
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag")] = None,
    flag: Annotated[
        int | None, typer.Option("--flag", "-F", help="Flag color (1-7) or 0 for any")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 20,
    brief: Annotated[bool, typer.Option("--brief", "-B", help="Truncated table view")] = False,
) -> None:
    """List notes, optionally filtered by deck, tag, and/or flag."""
    if flag is not None and not 0 <= flag <= 7:
        console.print("[red]--flag must be 0 (any) or 1-7.[/red]")
        raise typer.Exit(2)

    parts = []
    if deck:
        parts.append(f'"deck:{deck}"')
    if tag:
        parts.append(f'"tag:{tag}"')
    if flag is not None:
        if flag == 0:
            parts.append("(" + " OR ".join(f"flag:{i}" for i in range(1, 8)) + ")")
        else:
            parts.append(f"flag:{flag}")
    query = " ".join(parts) or "deck:*"

    client = AnkiClient()
    ids = client.find_notes(query)
    if not ids:
        console.print("[yellow]No notes found.[/yellow]")
        return
    infos = client.notes_info(ids[:limit])
    title = "Notes"
    if deck:
        title = f"Deck: {deck}"
    if tag:
        title += f" [tag:{tag}]" if deck else f"Tag: {tag}"
    if flag is not None:
        flag_label = "Flagged" if flag == 0 else f"Flag: {flag}"
        if deck or tag:
            title += f" [{flag_label.lower()}]"
        else:
            title = flag_label
    _render_notes(infos, len(ids), title, limit, brief)


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
def stats(
    days: Annotated[int, typer.Option("--days", "-d", help="Show history for last N days")] = 1,
    collection: Annotated[
        bool, typer.Option("--collection", "-c", help="Open full collection stats in browser")
    ] = False,
) -> None:
    """Show review stats."""
    client = AnkiClient()

    if collection:
        import tempfile
        import webbrowser
        from importlib.resources import files

        template = files("anki_cli").joinpath("stats.html").read_text()
        body = client.collection_stats_html()
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(template.replace("{body}", body))
            path = f.name
        webbrowser.open(f"file://{path}")
        console.print("[green]Opened collection stats in browser.[/green]")
        return

    if days == 1:
        reviewed = client.cards_reviewed_today()
        console.print(
            Panel(f"[bold green]{reviewed}[/bold green] cards reviewed today", title="Today")
        )
    else:
        from datetime import date, timedelta

        cutoff = (date.today() - timedelta(days=days)).isoformat()
        history = [(d, c) for d, c in client.cards_reviewed_by_day() if d >= cutoff]
        table = Table(title=f"Reviews — last {days} days")
        table.add_column("Date", style="cyan")
        table.add_column("Cards", justify="right", style="bold green")
        for date_str, count in history:
            table.add_row(date_str, str(count))
        console.print(table)
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
    seen: dict[str, None] = {}
    for note in notes:
        for key in note["fields"]:
            seen.setdefault(key, None)
    field_names = list(seen)
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
    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    ext = file.suffix.lower()
    try:
        if ext == ".json":
            notes = _read_json(file)
        elif ext == ".csv":
            notes = _read_csv(file)
        else:
            console.print(f"[red]Unsupported format:[/red] {ext} (use .json or .csv)")
            raise typer.Exit(1)
    except (json.JSONDecodeError, csv.Error, KeyError, ValueError) as exc:
        console.print(f"[red]Failed to parse {file.name}:[/red] {exc}")
        raise typer.Exit(1) from None

    has_new_notes = any(not n.get("noteId") for n in notes)
    if has_new_notes and not deck:
        console.print("[red]--deck required for new notes (missing noteId)[/red]")
        raise typer.Exit(1)

    client = AnkiClient()
    created = updated = errors = 0

    existing_ids = [n["noteId"] for n in notes if n.get("noteId")]
    current_tags_by_id: dict[int, set[str]] = {}
    if existing_ids:
        for info in client.notes_info(existing_ids):
            current_tags_by_id[info["noteId"]] = set(info["tags"])

    new_note_objects: list[dict[str, Any]] = []

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
            if dry_run:
                console.print(f"  [green]create[/green] {model} → {deck}")
                created += 1
            else:
                obj: dict[str, Any] = {
                    "deckName": deck,
                    "modelName": model,
                    "fields": fields,
                }
                if tags:
                    obj["tags"] = tags
                new_note_objects.append(obj)

    if not dry_run and new_note_objects:
        results = client.add_notes(new_note_objects)
        for new_id in results:
            if new_id is None:
                console.print("  [red]error[/red]: duplicate or invalid note")
                errors += 1
            else:
                console.print(f"  [green]created[/green] {new_id}")
                created += 1

    label = "[dim](dry run)[/dim] " if dry_run else ""
    console.print(
        f"\n{label}[green]{created} created[/green],"
        f" [blue]{updated} updated[/blue],"
        f" [red]{errors} errors[/red]"
    )


@app.command()
def sync() -> None:
    """Trigger an AnkiWeb sync."""
    client = AnkiClient()
    client.sync()
    console.print("[green]Sync triggered.[/green]")


@app.command()
def suspend(
    card_id: Annotated[int | None, typer.Argument(help="Card ID")] = None,
    query: Annotated[
        str | None, typer.Option("--query", "-q", help="Anki query to select cards")
    ] = None,
) -> None:
    """Suspend cards by ID or query."""
    if card_id is not None and query is not None:
        console.print("[red]Specify either a card ID or --query, not both.[/red]")
        raise typer.Exit(1)
    if card_id is None and query is None:
        console.print("[red]Specify a card ID or --query.[/red]")
        raise typer.Exit(1)
    client = AnkiClient()
    ids = client.find_cards(query) if query else [card_id]
    if not ids:
        console.print("[yellow]No cards found.[/yellow]")
        return
    client.suspend(ids)
    console.print(f"[green]Suspended {len(ids)} card(s).[/green]")


@app.command()
def unsuspend(
    card_id: Annotated[int | None, typer.Argument(help="Card ID")] = None,
    query: Annotated[
        str | None, typer.Option("--query", "-q", help="Anki query to select cards")
    ] = None,
) -> None:
    """Unsuspend cards by ID or query."""
    if card_id is not None and query is not None:
        console.print("[red]Specify either a card ID or --query, not both.[/red]")
        raise typer.Exit(1)
    if card_id is None and query is None:
        console.print("[red]Specify a card ID or --query.[/red]")
        raise typer.Exit(1)
    client = AnkiClient()
    ids = client.find_cards(query) if query else [card_id]
    if not ids:
        console.print("[yellow]No cards found.[/yellow]")
        return
    client.unsuspend(ids)
    console.print(f"[green]Unsuspended {len(ids)} card(s).[/green]")


@app.command()
def media(
    file: Annotated[Path, typer.Argument(help="Local file to store")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Filename in collection")] = None,
) -> None:
    """Store a media file in the Anki collection."""
    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)
    client = AnkiClient()
    stored = client.store_media_file(name or file.name, str(file.resolve()))
    console.print(f"[green]Media stored:[/green] {stored}")


@app.command("create-deck")
def create_deck(
    name: Annotated[str, typer.Argument(help="Deck name (use :: for nested)")],
) -> None:
    """Create a new deck."""
    client = AnkiClient()
    deck_id = client.create_deck(name)
    console.print(f"[green]Deck created:[/green] {name} (id={deck_id})")


@app.command("delete-deck")
def delete_deck(
    name: Annotated[str, typer.Argument(help="Deck name to delete")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    keep_cards: Annotated[
        bool, typer.Option("--keep-cards", help="Move cards instead of deleting")
    ] = False,
) -> None:
    """Delete a deck."""
    if not yes:
        typer.confirm(f"Delete deck '{name}'?", abort=True)
    client = AnkiClient()
    client.delete_decks([name], cards_too=not keep_cards)
    console.print(f"[green]Deck deleted:[/green] {name}")


@app.command("change-deck")
def change_deck(
    deck: Annotated[str, typer.Argument(help="Target deck name")],
    query: Annotated[
        str | None, typer.Option("--query", "-q", help="Anki query to select cards")
    ] = None,
    card_ids: Annotated[list[int] | None, typer.Option("--card", "-c", help="Card ID(s)")] = None,
) -> None:
    """Move cards to a different deck."""
    if not query and not card_ids:
        console.print("[red]Specify --query or --card.[/red]")
        raise typer.Exit(1)
    client = AnkiClient()
    ids: list[int] = []
    if query:
        ids = client.find_cards(query)
        if not ids:
            console.print("[yellow]No cards found.[/yellow]")
            return
    if card_ids:
        ids = list(set(ids + card_ids))
    client.change_deck(ids, deck)
    console.print(f"[green]Moved {len(ids)} card(s) to '{deck}'.[/green]")


@app.command("export-deck")
def export_deck(
    deck: Annotated[str, typer.Argument(help="Deck name to export")],
    file: Annotated[Path, typer.Argument(help="Output .apkg path")],
    include_sched: Annotated[
        bool, typer.Option("--include-sched", help="Include scheduling data")
    ] = False,
) -> None:
    """Export a deck to an .apkg file."""
    client = AnkiClient()
    client.export_package(deck, str(file.resolve()), include_sched)
    console.print(f"[green]Exported '{deck}' to {file}[/green]")


@app.command("import-deck")
def import_deck(
    file: Annotated[Path, typer.Argument(help=".apkg file to import")],
) -> None:
    """Import a deck from an .apkg file."""
    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)
    client = AnkiClient()
    client.import_package(str(file.resolve()))
    console.print(f"[green]Imported {file}[/green]")
