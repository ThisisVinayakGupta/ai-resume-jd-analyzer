import re
from typing import Dict, List, Tuple


# Conservative aliases: common abbreviations/format variants only.
# We intentionally avoid broad semantic synonyms to reduce false positives.
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

IMPORTANCE_WEIGHTS = {
    "high": 3,
    "medium": 2,
    "low": 1,
}

WEAK_CONTEXT_TERMS = (
    "course", "coursework", "training", "certification", "certificate",
    "learned", "studied", "workshop", "bootcamp", "academic module",
)


def _normalize(text: str) -> str:
    """Normalize text for conservative keyword matching."""
    text = str(text or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\u2010-\u2015\-/|]+", " ", text)
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


def _evidence_segments(resume_text: str) -> List[str]:
    """Split resume text into useful evidence-sized segments while preserving wording."""
    text = str(resume_text or "").replace("\r\n", "\n").replace("\r", "\n")
    segments = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # PDF extraction often puts bullets/experience statements on separate lines.
        # If a line contains multiple sentences, inspect each sentence separately.
        parts = re.split(r"(?<=[.!?])\s+", line)
        segments.extend(part.strip() for part in parts if part.strip())

    return segments or [text.strip()]


def _segment_contains_keyword(keyword: str, segment: str) -> bool:
    """Return True when a segment contains the keyword or one of its safe aliases."""
    normalized_segment = _normalize(segment)
    return any(
        _contains_term(term, normalized_segment)
        for term in _candidate_terms(keyword)
    )


def _is_weak_segment(segment: str) -> bool:
    """Return True when the matching segment is explicitly learning/training focused."""
    normalized = _normalize(segment)
    return any(term in normalized for term in WEAK_CONTEXT_TERMS)


def _find_keyword_evidence(keyword: str, resume_text: str) -> Tuple[str, bool, bool]:
    """Return best evidence plus whether strong and weak evidence were found."""
    strong_evidence = []
    weak_evidence = []

    for segment in _evidence_segments(resume_text):
        if not _segment_contains_keyword(keyword, segment):
            continue
        if _is_weak_segment(segment):
            weak_evidence.append(segment)
        else:
            strong_evidence.append(segment)

    if strong_evidence:
        return strong_evidence[0], True, bool(weak_evidence)
    if weak_evidence:
        return weak_evidence[0], False, True
    return "", False, False


def match_keyword(keyword: str, resume_text: str) -> Dict[str, str]:
    """Classify one JD keyword against resume text as Found, Partial, or Missing."""
    keyword = str(keyword or "").strip()
    text = str(resume_text or "")

    if not keyword or not text.strip():
        return {
            "keyword": keyword,
            "status": "Missing",
            "evidence": "No matching evidence found in the resume.",
        }

    evidence, has_strong_evidence, has_weak_evidence = _find_keyword_evidence(
        keyword, text
    )

    if has_strong_evidence:
        return {
            "keyword": keyword,
            "status": "Found",
            "evidence": f"Evidence: {evidence}",
        }

    if has_weak_evidence:
        return {
            "keyword": keyword,
            "status": "Partial",
            "evidence": f"Evidence: {evidence}",
        }

    return {
        "keyword": keyword,
        "status": "Missing",
        "evidence": f'No evidence for "{keyword}" was found in the resume.',
    }


def calculate_keyword_coverage(
    keywords: List[Dict], statuses: List[str]
) -> Tuple[int, int, int, int]:
    """Calculate importance-weighted keyword coverage.

    High = 3 points, Medium = 2 points, Low = 1 point.
    Found earns 100% of its points, Partial earns 50%, Missing earns 0%.
    """
    found = 0
    partial = 0
    missing = 0
    earned_points = 0.0
    total_points = 0.0

    # Pair each status with its keyword importance. If a caller supplies no
    # keyword records, preserve the old equal-weight behavior as a fallback.
    for index, status in enumerate(statuses):
        keyword = keywords[index] if index < len(keywords) else {}
        importance = str(keyword.get("importance", "Medium") or "Medium").strip().lower()
        weight = IMPORTANCE_WEIGHTS.get(importance, IMPORTANCE_WEIGHTS["medium"])
        total_points += weight

        normalized_status = str(status or "").strip().lower()
        if normalized_status == "found":
            found += 1
            earned_points += weight
        elif normalized_status == "partial":
            partial += 1
            earned_points += weight * 0.5
        else:
            missing += 1

    if total_points == 0:
        return 0, found, partial, missing

    score = round((earned_points / total_points) * 100)
    return score, found, partial, missing
