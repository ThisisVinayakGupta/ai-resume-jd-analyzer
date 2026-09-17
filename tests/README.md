# Phase 2B verification

From the repository folder, install the existing requirements and run:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m py_compile app.py keyword_matcher.py recommendation_engine.py
```

The tests use a fictional PDF and a mocked Gemini response. No real API key is
needed, and tests do not send resumes to an AI provider. They cover recommendations,
source evidence verification, score weights, PDF extraction, missing uploads, and
Streamlit session persistence without a second model call on a rerun.

The consolidated fix passes 51 tests on 17 September 2026. Regression tests first
reproduced the wording and evidence-context failures, then passed after the fixes.
They include BI tool(s), US/UK visualization spelling, simple verb variants, named
tool boundaries, extra requirement constraints, cropped training/negation quotes,
repeated quotes, and unrelated actions beside skill lists. Application must cover
the requirement within one source statement; adjacent bare skills cannot complete
an otherwise partial application claim.

## Recommendation rules

- True Gap: no supporting resume evidence found. This is not proof of absent ability.
- Proof Gap: a bare skill, training, incomplete requirement, or unverified AI quote.
- Wording Gap: a narrow supported relationship, currently dashboard work using a BI
  tool supporting the broader terms data visualization or business intelligence,
  including explicit tool(s), plural, BI, and US/UK spelling variants.
- Strong Match: demonstrated application. Keep the existing evidence.

The recommendation module does not alter scores. Named tools are not substituted
for one another. Requirement quotes must exist in the resume and be relevant.
Duration and numeric requirements require review. Source verification confirms what
the resume says, not whether the underlying experience is true. Conservative text
heuristics can miss paraphrases, section context, complex negation, or PDF line wraps;
users must confirm advice before editing. No resume rewrite is generated in Phase 2B.

## Deployment check

After deployment, check the Phase 2B caption, then upload a fictional text PDF with:
SQL applied to reports, Power BI dashboards, a Machine Learning course, and a bare
Python skill. Compare against a JD asking for those skills plus Tableau and data
visualization. Confirm actual evidence text and guarded recommendations. The model
may choose different extracted keywords; exact scores are not a fixed expectation.

Phase 2C remains gated on successful live analysis verification.
The consolidated replacement files have been verified locally with mocked Gemini;
perform a fresh live analysis after uploading them. A new Gemini response can
change extracted keywords and category scores even when formulas remain unchanged.
