import unittest

from typer.testing import CliRunner

from anki_cli.cli import _fuzzy_score, app

runner = CliRunner()


class SearchCommandTests(unittest.TestCase):
    def test_empty_fuzzy_query_fails_cleanly(self) -> None:
        result = runner.invoke(app, ["search", "", "--fuzzy", "--limit", "1"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Fuzzy search requires a non-empty query.", result.stdout)

    def test_fuzzy_score_empty_query_returns_zero(self) -> None:
        note = {
            "fields": {
                "Front": {"value": "What is Python?"},
                "Back": {"value": "A programming language"},
            }
        }
        self.assertEqual(_fuzzy_score("", note), 0.0)


if __name__ == "__main__":
    unittest.main()
