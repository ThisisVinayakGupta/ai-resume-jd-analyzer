"""Real Streamlit reruns and PDF parsing; Gemini is mocked (no credentials/cost)."""
import copy
import io
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from streamlit.testing.v1 import AppTest


RESUME_LINES = [
    "SAMPLE CANDIDATE - fictional test resume",
    "Used SQL to extract and validate operational datasets.",
    "Created interactive dashboards using Power BI.",
    "Completed a Machine Learning course covering regression and classification.",
    "Skills: Python, SQL, Power BI",
]


def resume_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(("BT /F1 10 Tf 40 790 Td 18 TL " + " ".join(f"({line}) Tj T*" for line in RESUME_LINES) + " ET").encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output


def response_data():
    return dict(
        category_scores=dict(skills_match=70, experience_match=60, responsibilities_match=80,
                             tools_match=75, education_match=50, evidence_match=65),
        requirements=[dict(requirement="SQL experience", status="Found", explanation="SQL is applied.",
                           evidence=RESUME_LINES[1], importance="High"),
                      dict(requirement="Build dashboards using business intelligence tools.",
                           status="Found", explanation="Applied dashboard evidence.",
                           evidence=RESUME_LINES[2], importance="High")],
        keywords=[dict(keyword=k, importance="High", category="Skill")
                  for k in ["SQL", "Python", "Machine Learning", "Data visualization", "Business Intelligence Tools", "Tableau"]],
        overall_assessment="Some requirements are supported.", strengths=["SQL application"],
        missing_skills=["Tableau"], experience_explanation="Some applied evidence exists.",
        weak_requirements=["Machine Learning application"], improvement_suggestions=[],
        interview_questions=["Explain your SQL work."],
    )


class StreamlitFlowTests(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.client.models.generate_content.return_value = SimpleNamespace(
            parsed=SimpleNamespace(model_dump=lambda: copy.deepcopy(response_data())))
        self.env = patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-test-key-not-a-secret"})
        self.client_patch = patch("google.genai.Client", return_value=self.client)
        self.env.start()
        self.client_patch.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.client_patch.stop)
        self.app_path = Path(__file__).resolve().parents[1] / "app.py"

    def test_pdf_analysis_and_rerun_persist_without_second_api_call(self):
        with patch("streamlit.file_uploader", return_value=resume_pdf()):
            app = AppTest.from_file(str(self.app_path), default_timeout=30).run()
            app.text_area[0].set_value("Data analyst: SQL, Python, Machine Learning, data visualization, Tableau.")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertFalse(any("Something went wrong" in error.value for error in app.error))
            recs = app.session_state["recommendations"]
            kinds = {r["subject"]: r["gap_type"] for r in recs}
            self.assertEqual(kinds["SQL"], "Strong Match")
            self.assertEqual(kinds["Python"], "Proof Gap")
            self.assertEqual(kinds["Machine Learning"], "Proof Gap")
            self.assertEqual(kinds["Data visualization"], "Wording Gap")
            self.assertEqual(kinds["Business Intelligence Tools"], "Wording Gap")
            self.assertEqual(kinds["Build dashboards using business intelligence tools."], "Strong Match")
            self.assertEqual(kinds["Tableau"], "True Gap")
            self.assertTrue(any("Keyword wording was not found" in c.value for c in app.caption))
            self.assertTrue(any("Keyword wording absent" in w.value for w in app.warning))
            self.assertEqual(app.session_state["final_score"], 68)
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["recommendations"], recs)
            self.assertEqual(self.client.models.generate_content.call_count, 1)

    def test_missing_upload_never_calls_api(self):
        with patch("streamlit.file_uploader", return_value=None):
            app = AppTest.from_file(str(self.app_path), default_timeout=30).run()
            app.button[0].click().run()
            self.assertTrue(any("upload" in w.value.lower() for w in app.warning))
            self.client.models.generate_content.assert_not_called()


if __name__ == "__main__":
    unittest.main()
