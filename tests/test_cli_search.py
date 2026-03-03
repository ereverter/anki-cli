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


class ListFlagTests(unittest.TestCase):
    def test_flag_rejects_out_of_range(self) -> None:
        result = runner.invoke(app, ["list", "--flag", "9"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("--flag must be 0 (any), 1-7, or a color name.", result.stdout)

    def test_flag_rejects_negative(self) -> None:
        result = runner.invoke(app, ["list", "--flag", "-1"])
        self.assertNotEqual(result.exit_code, 0)


class FlagCommandTests(unittest.TestCase):
    def test_flag_rejects_out_of_range(self) -> None:
        result = runner.invoke(app, ["flag", "9", "--card", "123"])
        self.assertEqual(result.exit_code, 2)

    def test_flag_rejects_invalid_name(self) -> None:
        result = runner.invoke(app, ["flag", "nope", "--card", "123"])
        self.assertEqual(result.exit_code, 2)

    def test_flag_requires_card_or_query(self) -> None:
        result = runner.invoke(app, ["flag", "red"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Specify --card or --query.", result.stdout)

    def test_flag_rejects_both_card_and_query(self) -> None:
        result = runner.invoke(app, ["flag", "red", "--card", "123", "--query", "deck:*"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not both", result.stdout)


if __name__ == "__main__":
    unittest.main()
