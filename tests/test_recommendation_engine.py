import copy
import unittest

from recommendation_engine import build_recommendations


class RecommendationTests(unittest.TestCase):
    def recommend(self, keyword, resume, status="Found", **extra):
        row = dict(keyword=keyword, importance="High", status=status, **extra)
        return build_recommendations([row], [], resume)[0]

    def test_missing_skill_is_true_gap(self):
        result = self.recommend("Tableau", "Built dashboards using Power BI.", "Missing")
        self.assertEqual(result["gap_type"], "True Gap")
        self.assertIn("only if", result["action"].lower())

    def test_skill_list_is_proof_gap(self):
        self.assertEqual(self.recommend("Python", "Skills: Python, SQL")["gap_type"], "Proof Gap")

    def test_training_is_proof_gap(self):
        result = self.recommend("Machine Learning", "Completed a Machine Learning course.", "Partial")
        self.assertEqual(result["gap_type"], "Proof Gap")
        self.assertIn("training", result["explanation"].lower())

    def test_actual_application_is_strong(self):
        resume = "Used SQL to extract and validate operational datasets."
        result = self.recommend("SQL", resume)
        self.assertEqual(result["gap_type"], "Strong Match")
        self.assertEqual(result["evidence"], resume)
        self.assertEqual(result["priority"], "Maintain")

    def test_best_application_beats_skill_list(self):
        resume = "Skills: SQL\nUsed SQL to validate customer records."
        self.assertEqual(self.recommend("SQL", resume)["evidence"], resume.splitlines()[1])

    def test_training_does_not_hide_real_application(self):
        resume = "Completed a SQL course.\nBuilt SQL queries for inventory reports."
        self.assertEqual(self.recommend("SQL", resume)["gap_type"], "Strong Match")

    def test_wording_gap_has_genuine_support(self):
        resume = "Created interactive dashboards using Power BI."
        result = self.recommend("Data visualization", resume, "Missing")
        self.assertEqual(result["gap_type"], "Wording Gap")
        self.assertEqual(result["evidence"], resume)
        self.assertIn("accurately", result["action"])

    def test_related_tool_is_not_equivalent(self):
        self.assertEqual(self.recommend("Tableau", "Created dashboards using Power BI.")["gap_type"], "True Gap")

    def test_unsubstantiated_ai_evidence_is_rejected(self):
        result = self.recommend("Python", "Skills: Excel", evidence="Built Python pipelines.")
        self.assertEqual(result["gap_type"], "True Gap")
        self.assertEqual(result["evidence"], "")

    def test_generic_evidence_does_not_count(self):
        result = self.recommend("Python", "Skills: Excel", evidence='Found evidence for "Python" in the resume.')
        self.assertEqual(result["gap_type"], "True Gap")

    def test_whole_word_matching(self):
        self.assertEqual(self.recommend("SQL", "Used SQLAlchemy to build services.")["gap_type"], "True Gap")

    def test_negation_cannot_be_strong(self):
        for text in ("Never used Python.", "No experience using Python.", "Have not used Python."):
            with self.subTest(text=text):
                self.assertEqual(self.recommend("Python", text)["gap_type"], "True Gap")

    def test_plans_do_not_become_experience(self):
        result = self.recommend("Python", "Plan to build a Python project.")
        self.assertEqual(result["gap_type"], "True Gap")

    def test_requirement_exact_quote_is_verified(self):
        text = "Used SQL to validate sales records."
        requirement = dict(requirement="SQL experience", status="Found", evidence=text)
        result = build_recommendations([], [requirement], text)[0]
        self.assertEqual(result["gap_type"], "Strong Match")
        self.assertEqual(result["source"], "Requirement")

    def test_requirement_explanation_is_not_evidence(self):
        req = dict(requirement="SQL experience", status="Found", explanation="The candidate used SQL.")
        result = build_recommendations([], [req], "Skills: Python")[0]
        self.assertEqual(result["gap_type"], "Proof Gap")
        self.assertEqual(result["evidence"], "")

    def test_partial_requirement_cannot_become_strong(self):
        text = "Used SQL to validate sales records."
        req = dict(requirement="Five years of SQL experience", status="Partial", evidence=text)
        self.assertEqual(build_recommendations([], [req], text)[0]["gap_type"], "Proof Gap")

    def test_found_cannot_hide_unproven_duration_or_second_tool(self):
        text = "Used SQL to validate sales records."
        for requirement in ("Five years of SQL experience", "SQL and Tableau experience"):
            req = dict(requirement=requirement, status="Found", evidence=text)
            with self.subTest(requirement=requirement):
                self.assertEqual(build_recommendations([], [req], text)[0]["gap_type"], "Proof Gap")

    def test_quote_cannot_remove_negation(self):
        req = dict(requirement="Python experience", status="Found", evidence="used Python")
        result = build_recommendations([], [req], "I have never used Python.")[0]
        self.assertEqual(result["gap_type"], "Proof Gap")
        self.assertEqual(result["evidence"], "")

    def test_unrelated_requirement_quote_rejected(self):
        text = "Built Python pipelines."
        req = dict(requirement="Tableau experience", status="Found", evidence=text)
        result = build_recommendations([], [req], text)[0]
        self.assertNotEqual(result["gap_type"], "Strong Match")
        self.assertEqual(result["evidence"], "")

    def test_missing_requirement_without_quote_is_true_gap(self):
        req = dict(requirement="Tableau experience", status="Missing")
        self.assertEqual(build_recommendations([], [req], "Skills: Python")[0]["gap_type"], "True Gap")

    def test_empty_and_malformed_input(self):
        self.assertEqual(build_recommendations(None, None, None), [])
        self.assertEqual(build_recommendations([None, {}, {"keyword": " "}], [None, {}], ""), [])

    def test_priority_order_and_truth_guards(self):
        rows = [dict(keyword="Tableau", importance="Low"), dict(keyword="SQL", importance="High")]
        result = build_recommendations(rows, [], "")
        self.assertEqual([r["priority"] for r in result], ["High", "Low"])
        for r in result:
            self.assertTrue(r["truth_guard"])
            self.assertTrue({"priority", "gap_type", "evidence", "explanation", "action", "truth_guard"} <= r.keys())

    def test_inputs_unchanged(self):
        rows = [dict(keyword="SQL", importance="High", status="Found")]
        before = copy.deepcopy(rows)
        build_recommendations(rows, [], "Used SQL to build reports.")
        self.assertEqual(rows, before)

    def test_reverse_alias_is_supported_for_recommendations(self):
        text = "Used machine learning to classify support tickets."
        self.assertEqual(self.recommend("ML", text)["gap_type"], "Strong Match")

class WordingRegressionTests(unittest.TestCase):
    def test_use_sql_matches_used_sql_evidence(self):
        resume = "Used SQL to extract and validate operational datasets."
        requirement = {
            "requirement": "Use SQL to extract and validate operational datasets.",
            "status": "Found",
            "importance": "High",
            "evidence": resume,
        }

        result = build_recommendations([], [requirement], resume)[0]

        self.assertEqual(result["gap_type"], "Strong Match")
        self.assertEqual(result["evidence"], resume)

    def test_plural_visualizations_recognizes_dashboard_evidence(self):
        resume = "Created interactive dashboards using Power BI."
        keyword = {
            "keyword": "Data Visualizations",
            "status": "Missing",
            "importance": "Medium",
        }

        result = build_recommendations([keyword], [], resume)[0]

        self.assertEqual(result["gap_type"], "Wording Gap")
        self.assertEqual(result["evidence"], resume)
class DashboardRequirementTests(unittest.TestCase):
    def test_dashboard_requirement_recognizes_power_bi_evidence(self):
        resume = "Created interactive dashboards using Power BI."
        requirement = {
            "requirement": (
                "Create dashboards and data visualizations "
                "using business intelligence tools."
            ),
            "status": "Found",
            "importance": "High",
            "evidence": resume,
        }

        result = build_recommendations([], [requirement], resume)[0]

        self.assertEqual(result["gap_type"], "Strong Match")
        self.assertEqual(result["evidence"], resume)

    def test_power_bi_does_not_prove_tableau_requirement(self):
        resume = "Created interactive dashboards using Power BI."
        requirement = {
            "requirement": "Create dashboards using Tableau.",
            "status": "Found",
            "importance": "High",
            "evidence": resume,
        }

        result = build_recommendations([], [requirement], resume)[0]

        self.assertEqual(result["gap_type"], "Proof Gap")
if __name__ == "__main__":
    unittest.main()
