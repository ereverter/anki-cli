# anki-cli

CLI for managing Anki flashcards via [AnkiConnect](https://foosoft.net/projects/anki-connect/).

## Requirements

- Python 3.12+
- [Anki](https://apps.ankiweb.net/) running with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon installed

## Install

```
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

## Usage

<!-- usage-start -->
```
Usage: anki [OPTIONS] COMMAND [ARGS]...                                        
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ decks   List decks with review stats.                                        │
│ models  List available note types.                                           │
│ search  Search notes using Anki query syntax.                                │
│ show    Show full details of one or more notes.                              │
│ add     Add a new note.                                                      │
│ edit    Edit fields of an existing note.                                     │
│ delete  Delete a note.                                                       │
│ tag     Add or remove tags on notes.                                         │
│ stats   Show today's review stats.                                           │
│ export  Export notes to JSON or CSV.                                         │
│ import  Import notes from JSON or CSV.                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```
<!-- usage-end -->

## write-note skill

Includes a [Claude Code skill](.claude/skills/write-note/SKILL.md) (`/write-note`) for creating cards that follow the opinionated guidelines from [An Opinionated Guide to Using Anki Correctly](https://www.lesswrong.com/posts/mGfpALAjbRvGRAJhJ/an-opinionated-guide-to-using-anki-correctly).

```
/write-note are these notes <paste notes> good based on the content <paste content>
```
