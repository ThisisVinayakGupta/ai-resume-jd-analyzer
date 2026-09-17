"""Wording variants and protections for the consolidated Phase 2B fix."""
import unittest

from recommendation_engine import build_recommendations


DASHBOARD = "Created interactive dashboards using Power BI."


class ConsolidatedWordingTests(unittest.TestCase):
    def keyword(self, subject, resume=DASHBOARD):
        return build_recommendations(
            [{"keyword": subject, "importance": "High", "status": "Missing"}], [], resume
        )[0]

    def requirement(self, subject, quote=DASHBOARD, resume=None, status="Found"):
        return build_recommendations([], [{
            "requirement": subject, "status": status, "importance": "High", "evidence": quote,
        }], quote if resume is None else resume)[0]

    def test_bi_keyword_variants(self):
        for subject in ("Business Intelligence", "Business Intelligence Tool",
                        "Business Intelligence Tools", "BI", "BI tool", "BI tools"):
            with self.subTest(subject=subject):
                result = self.keyword(subject)
                self.assertEqual(result["gap_type"], "Wording Gap")
                self.assertEqual(result["evidence"], DASHBOARD)

    def test_visualization_keyword_variants(self):
        for subject in ("Data Visualization", "Data Visualizations", "Data Visualisation",
                        "Data Visualisations", "Data-Visualization", "data visualisation tools"):
            with self.subTest(subject=subject):
                self.assertEqual(self.keyword(subject)["gap_type"], "Wording Gap")

    def test_requirement_variations_without_exact_sentence_shortcuts(self):
        for subject in (
            "Build dashboards using business intelligence tools.",
            "Create a dashboard using a BI tool.",
            "Experience creating dashboards using Power BI.",
            "Create dashboards and data visualizations using business intelligence tools.",
            "Develop dashboards and data visualisations using BI tools.",
            "Business intelligence tools experience",
        ):
            with self.subTest(subject=subject):
                self.assertEqual(self.requirement(subject)["gap_type"], "Strong Match")

    def test_extra_requirement_constraints_remain_gaps(self):
        for subject in (
            "Create dashboards using Tableau.",
            "Create dashboards using Power BI and Tableau.",
            "Build dashboards using BI tools and Python.",
            "Create dashboards using BI tools with real-time streaming.",
            "Create dashboards using BI tools with a certification.",
            "Five years of BI tools experience.",
            "Create three dashboards using BI tools.",
        ):
            with self.subTest(subject=subject):
                self.assertNotEqual(self.requirement(subject)["gap_type"], "Strong Match")

    def test_partial_status_is_not_overridden(self):
        self.assertEqual(self.requirement("Build dashboards using BI tools.", status="Partial")["gap_type"], "Proof Gap")

    def test_training_cannot_prove_bi_application(self):
        resume = "Completed a Power BI course and created a dashboard during training."
        self.assertNotEqual(self.keyword("BI tools", resume)["gap_type"], "Strong Match")
        self.assertNotEqual(self.requirement("Create dashboards using BI tools.", quote=resume)["gap_type"], "Strong Match")

    def test_skill_list_does_not_prove_bi_application(self):
        self.assertEqual(self.keyword("BI tools", "Skills: Power BI, SQL")["gap_type"], "True Gap")
        self.assertEqual(self.keyword("BI tools", "Skills: Business Intelligence Tools")["gap_type"], "Proof Gap")

    def test_unrelated_action_does_not_support_skill_list(self):
        result = self.keyword("Python", "Skills: Python; Built SQL queries for reporting.")
        self.assertEqual(result["gap_type"], "Proof Gap")

    def test_requirement_cannot_borrow_application_from_another_line(self):
        for text in ("Built SQL reports\nSkills: Python", "Built SQL reports; Skills: Python"):
            with self.subTest(text=text):
                result = self.requirement("Python experience", quote="Python", resume=text)
                self.assertEqual(result["gap_type"], "Proof Gap")

    def test_requirement_cannot_merge_applied_tool_with_bare_tool(self):
        text = "Built dashboards using Power BI; Skills: Tableau"
        result = self.requirement("Build dashboards using Power BI and Tableau.", quote=text)
        self.assertEqual(result["gap_type"], "Proof Gap")

    def test_compound_technology_name_must_match_as_a_phrase(self):
        text = "Created reports about renewable power using BI tools."
        self.assertNotEqual(self.requirement("Power BI experience", quote=text)["gap_type"], "Strong Match")

    def test_c_and_cpp_remain_distinct(self):
        text = "Built services using C++."
        self.assertNotEqual(self.requirement("C experience", quote=text)["gap_type"], "Strong Match")

    def test_cropped_training_quote_keeps_training_context(self):
        result = self.requirement("SQL experience", quote="Built SQL reports.",
                                  resume="Coursework: Built SQL reports.")
        self.assertEqual(result["gap_type"], "Proof Gap")

    def test_wrapped_negation_cannot_be_removed_from_quote(self):
        result = self.requirement("Python experience", quote="used Python.",
                                  resume="I have never\nused Python.")
        self.assertEqual(result["gap_type"], "Proof Gap")
        self.assertEqual(result["evidence"], "")

    def test_quote_from_training_does_not_hide_later_genuine_work(self):
        resume = "Coursework: Built SQL reports.\nBuilt SQL reports."
        result = self.requirement("SQL experience", quote="Built SQL reports.", resume=resume)
        self.assertEqual(result["gap_type"], "Strong Match")
        self.assertEqual(result["evidence"], "Built SQL reports.")

    def test_applied_evidence_preserves_pdf_line_wrap(self):
        resume = "Created interactive dashboards\nusing Power BI."
        result = self.requirement("Build dashboards using BI tools.",
                                  quote="Created interactive dashboards using Power BI.", resume=resume)
        self.assertEqual(result["gap_type"], "Strong Match")
        self.assertEqual(result["evidence"], resume)

    def test_simple_verb_variations(self):
        for action, text in (("Use", "Used SQL to validate sales records."),
                             ("Build", "Built SQL reports."),
                             ("Create", "Created SQL reports.")):
            with self.subTest(action=action):
                self.assertEqual(self.requirement(f"{action} SQL reports." if action != "Use" else "Use SQL to validate sales records.", quote=text)["gap_type"], "Strong Match")


if __name__ == "__main__":
    unittest.main()
