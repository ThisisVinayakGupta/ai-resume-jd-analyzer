"""Integration contracts that can run without API access or Streamlit installed."""
import ast
from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1] / "app.py"


def helpers():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    wanted = {"safe_score", "safe_text", "safe_list", "calculate_final_score", "calculate_ats", "normalize_requirements"}
    scope = {}
    module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted], type_ignores=[])
    exec(compile(module, str(APP), "exec"), scope)
    return scope


class AppIntegrationTests(unittest.TestCase):
    def test_requirement_quote_survives_normalization(self):
        rows = [dict(requirement="SQL", status="Found", explanation="Good fit", evidence="Used SQL for reports.", importance="High")]
        result = helpers()["normalize_requirements"](rows)
        self.assertEqual(result[0]["evidence"], rows[0]["evidence"])
        self.assertEqual(result[0]["importance"], "High")

    def test_legacy_requirements_are_accepted(self):
        result = helpers()["normalize_requirements"]([dict(requirement="SQL", status="Partial")])
        self.assertEqual(result[0]["evidence"], "")

    def test_existing_score_weights_unchanged(self):
        calculate = helpers()["calculate_final_score"]
        weights = dict(skills=25, experience=20, responsibilities=20, tools=15, education=10, evidence=10)
        for category, expected in weights.items():
            with self.subTest(category=category):
                self.assertEqual(calculate({key: 100 if key == category else 0 for key in weights}), expected)

    def test_existing_ats_score_unchanged(self):
        self.assertEqual(helpers()["calculate_ats"]([dict(status=s) for s in ("Found", "Partial", "Missing")]), (50, 1, 1, 1))


if __name__ == "__main__":
    unittest.main()
