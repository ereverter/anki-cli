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

```
anki decks                          # list decks with review stats
anki models                         # list note types
anki search <query> [-l LIMIT] [-B]  # search notes (-B for brief table)
anki show <note-id> [<note-id> ...] # show note details
anki add -d DECK -f key=value       # add a note
anki edit <note-id> -f key=value    # edit a note
anki delete <note-id>               # delete a note
anki tag [<note-id>] [-q QUERY] -a/-r # add/remove tags
anki stats                          # today's review stats
anki export <query> <file>          # export to JSON/CSV
anki import <file> -d DECK          # import from JSON/CSV
```
