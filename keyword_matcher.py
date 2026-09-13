import re
from typing import Dict, List, Tuple


# Conservative aliases: these are common abbreviations/format variants rather than
# broad semantic synonyms. The goal is to avoid falsely marking a skill as present.
SAFE_ALIASES = {
    "machine learning": ["ml"],
    "artificial intelligence": ["ai"],
    "natural language processing": ["nlp"],
    "structured query language": ["sql"],
    "object oriented programming": ["oop"],
    "microsoft excel": ["excel"],
    "power bi": ["powerbi"],
    "amazon web services": ["aws"],
    "google cloud platform": ["gcp"],
    "microsoft azure": ["azure"],
}


def _normalize(text: str) -> str:
    """Normalize text for conservative keyword matching."""
    text = str(text or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\u2010-\u2015\-_/|]+", " ", text)
    text = re.sub(r"[^a-z0-9+#. ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _contains_term(term: str, text: str) -> bool:
    """Match a term as a whole word/phrase, avoiding substring false positives."""
    term = _normalize(term)
    if not term:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _candidate_terms(keyword: str) -> List[str]:
    """Return the keyword plus conservative, known aliases."""
    normalized = _normalize(keyword)
    terms = [normalized]
    terms.extend(_normalize(alias) for alias in SAFE_ALIASES.get(normalized, []))
    return [term for term in terms if term]


def _is_weak_context(keyword: str, resume_text: str) -> bool:
    """Identify evidence that mentions a keyword only in a learning/training context."""
    text = _normalize(resume_text)
    keyword_terms = _candidate_terms(keyword)

    weak_context_terms = (
        "course", "coursework", "training", "certification", "certificate",
        "learned", "studied", "workshop", "bootcamp", "academic module",
    )

    # A keyword is Found if at least one occurrence has substantive context.
    # It is only Partial when every detected occurrence appears tied to training/learning.
    weak_occurrence_found = False
    strong_occurrence_found = False

    for term in keyword_terms:
        pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
        for match in re.finditer(pattern, text):
            window = text[max(0, match.start() - 100): min(len(text), match.end() + 100)]
            if any(weak in window for weak in weak_context_terms):
                weak_occurrence_found = True
            else:
                strong_occurrence_found = True

    return weak_occurrence_found and not strong_occurrence_found


def match_keyword(keyword: str, resume_text: str) -> Dict[str, str]:
    """Classify one JD keyword against resume text as Found, Partial, or Missing."""
    keyword = str(keyword or "").strip()
    text = _normalize(resume_text)

    if not keyword or not text:
        return {
            "keyword": keyword,
            "status": "Missing",
            "evidence": "No matching evidence found in the resume.",
        }

    for term in _candidate_terms(keyword):
        if _contains_term(term, text):
            if _is_weak_context(keyword, text):
                return {
                    "keyword": keyword,
                    "status": "Partial",
                    "evidence": "The keyword appears, but the available context suggests limited or training-focused evidence.",
                }
            return {
                "keyword": keyword,
                "status": "Found",
                "evidence": f'Found evidence for "{keyword}" in the resume.',
            }

    return {
        "keyword": keyword,
        "status": "Missing",
        "evidence": f'No evidence for "{keyword}" was found in the resume.',
    }


def calculate_keyword_coverage(
    keywords: List[Dict], statuses: List[str]
) -> Tuple[int, int, int, int]:
    """Calculate transparent keyword coverage: Found=100%, Partial=50%, Missing=0%."""
    found = 0
    partial = 0
    missing = 0

    for status in statuses:
        status = str(status or "").strip().lower()
        if status == "found":
            found += 1
        elif status == "partial":
            partial += 1
        else:
            missing += 1

    total = found + partial + missing
    if total == 0:
        return 0, found, partial, missing

    score = round(((found + partial * 0.5) / total) * 100)
    return score, found, partial, missing
