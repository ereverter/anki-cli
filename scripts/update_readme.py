"""Regenerate the usage section in README.md from `anki --help`."""

from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from anki_cli.cli import app

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"

START = "<!-- usage-start -->"
END = "<!-- usage-end -->"


def main() -> None:
    readme = README.read_text()
    raw = CliRunner().invoke(app, ["--help"]).output.strip()
    help_output = raw.replace("Usage: root ", "Usage: anki ")
    block = f"{START}\n```\n{help_output}\n```\n{END}"
    updated = re.sub(
        rf"{re.escape(START)}.*?{re.escape(END)}",
        block,
        readme,
        flags=re.DOTALL,
    )
    if updated != readme:
        README.write_text(updated)


if __name__ == "__main__":
    main()
