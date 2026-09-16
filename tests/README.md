# Phase 2B tests

Run from the repository folder:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m py_compile app.py keyword_matcher.py recommendation_engine.py
```

Tests use a fictional PDF and mocked Gemini responses. No real API key or AI calls are needed. Coverage includes truthful recommendations, source quotes, score weights, PDF parsing, missing uploads, and Streamlit reruns.

True Gap means absent resume evidence, not absent ability. Proof Gap covers bare skills, training, incomplete requirements, and unverified quotes. Wording Gap currently supports only narrow dashboard-to-visualization terminology. Strong Match requires application evidence. Scores are unchanged. Named tools are not interchangeable. Numeric and duration requirements need review.

These conservative rules can miss paraphrases, complex negation, and PDF line-wrap context. Confirm all advice before editing. Phase 2C follows successful live analysis verification.
