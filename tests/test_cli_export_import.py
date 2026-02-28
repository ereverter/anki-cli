"""Tests for CSV export (mixed models) and import (error handling, --deck validation)."""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from anki_cli.cli import _write_csv, app

runner = CliRunner()


class TestWriteCsvMixedModels(unittest.TestCase):
    """CSV export should include the union of all field names across note models."""

    def test_union_of_fields_in_header(self) -> None:
        notes = [
            {
                "noteId": 1,
                "modelName": "Basic",
                "tags": "",
                "fields": {"Front": "q1", "Back": "a1"},
            },
            {
                "noteId": 2,
                "modelName": "Cloze",
                "tags": "",
                "fields": {"Text": "c1", "Extra": "e1"},
            },
        ]
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            _write_csv(notes, path)
            text = path.read_text()
            reader = csv.reader(io.StringIO(text))
            header = next(reader)
            expected = ["noteId", "modelName", "tags", "Front", "Back", "Text", "Extra"]
            self.assertEqual(header, expected)
            rows = list(reader)
            self.assertEqual(rows[0], ["1", "Basic", "", "q1", "a1", "", ""])
            self.assertEqual(rows[1], ["2", "Cloze", "", "", "", "c1", "e1"])
        finally:
            path.unlink(missing_ok=True)

    def test_empty_notes_writes_nothing(self) -> None:
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            _write_csv([], path)
            self.assertEqual(path.read_text(), "")
        finally:
            path.unlink(missing_ok=True)


class TestImportErrorHandling(unittest.TestCase):
    """Import should produce clean errors for missing files and malformed input."""

    def test_missing_file(self) -> None:
        result = runner.invoke(app, ["import", "/nonexistent/file.json"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("File not found", result.stdout)

    def test_malformed_json(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{not valid json!!")
            path = f.name
        try:
            result = runner.invoke(app, ["import", path])
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Failed to parse", result.stdout)
        finally:
            Path(path).unlink(missing_ok=True)


class TestImportDeckValidation(unittest.TestCase):
    """--deck check should fire before any AnkiClient calls."""

    def test_fails_before_api_calls(self) -> None:
        notes = [{"fields": {"Front": "q", "Back": "a"}, "modelName": "Basic"}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(notes, f)
            path = f.name
        try:
            with patch("anki_cli.cli.AnkiClient") as mock_client:
                result = runner.invoke(app, ["import", path])
                self.assertEqual(result.exit_code, 1)
                self.assertIn("--deck required", result.stdout)
                mock_client.assert_not_called()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_passes_with_deck_and_existing_notes(self) -> None:
        """Notes with noteId should not require --deck."""
        notes = [{"noteId": 123, "fields": {"Front": "q"}, "modelName": "Basic", "tags": ""}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(notes, f)
            path = f.name
        try:
            with patch("anki_cli.cli.AnkiClient") as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.notes_info.return_value = [{"noteId": 123, "tags": []}]
                result = runner.invoke(app, ["import", path])
                self.assertEqual(result.exit_code, 0)
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
