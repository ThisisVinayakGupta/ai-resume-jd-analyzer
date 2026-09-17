"""Conservative, source-grounded advice. Does not calculate or change scores.

Keywords are checked against the source again; AI-provided evidence is never
trusted on its own. Requirement quotes must be present in the source. These
rules are deliberately conservative heuristics, not verification of real-world
credentials. A True Gap means absent resume evidence, not absent ability.
"""

import re

from keyword_matcher import SAFE_ALIASES, WEAK_CONTEXT_TERMS


TRUTH_GUARD = (
    "Use only your real experience. Never invent skills, employment, projects, "
    "qualifications, certifications, achievements, responsibilities, or metrics."
)
_ACTIONS = re.compile(
    r"\b(used|built|created|developed|implemented|designed|delivered|analyzed|"
    r"analysed|automated|managed|maintained|deployed|led|tested|optimized|"
    r"optimised|prepared|produced|validated|integrated|migrated)\b", re.I
)
_UNSUPPORTED = re.compile(
    r"\b(no|not|never|without|lack|lacks|lacking|haven't|hasn't|didn't|"
    r"plan|plans|planning|intend|intends|aspire|aspiring|wish|willing|want|"
    r"will|would)\b", re.I
)
_STOP_WORDS = set(
    "a an the and or of in on to for with using experience experienced skills "
    "skill knowledge proficiency proficient ability required requirement strong "
    "demonstrated working professional years year at least have has must".split()
)

# Only these broader concepts can be supported by applied BI dashboard work.
# Keep phrases explicit rather than stripping arbitrary words like "tools".
_BI_TERMS = (
    "business intelligence", "business intelligence tool", "business intelligence tools",
    "bi", "bi tool", "bi tools",
)
_VISUALIZATION_TERMS = tuple(
    f"{term}{suffix}"
    for term in (
        "data visualization", "data visualizations", "data visualisation", "data visualisations",
    )
    for suffix in ("", " tool", " tools")
)
_CONCEPTS = {
    "business intelligence": _BI_TERMS,
    "data visualization": _VISUALIZATION_TERMS,
}
_VERB_FORMS = (
    ("use", "used", "using"),
    ("build", "built", "building", "create", "created", "creating", "develop", "developed", "developing"),
    ("design", "designed", "designing"),
    ("validate", "validated", "validating"),
    ("extract", "extracted", "extracting"),
    ("analyze", "analyzed", "analyzing", "analyse", "analysed", "analysing"),
    ("automate", "automated", "automating"),
    ("implement", "implemented", "implementing"),
    ("deploy", "deployed", "deploying"),
    ("test", "tested", "testing"),
)
_NOUN_FORMS = (("dashboard", "dashboards"), ("report", "reports"))


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def _normalize(value):
    value = _text(value).casefold().replace("&", " and ")
    value = re.sub(r"[\u2010-\u2015/|\-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _contains(term, text):
    term = _normalize(term)
    return bool(term and re.search(r"(?<![\w+#])" + re.escape(term) + r"(?![\w+#])", _normalize(text)))


def _aliases(keyword):
    key = _normalize(keyword)
    for variants in _CONCEPTS.values():
        if key in variants:
            return list(variants)
    for canonical, aliases in SAFE_ALIASES.items():
        group = [canonical, *aliases]
        if key in [_normalize(item) for item in group]:
            return group
    return [keyword]


def _matches(keyword, text):
    if _normalize(keyword) in _BI_TERMS:
        # "BI" inside the product name Power BI is related evidence, not a
        # literal mention of the broader concept. Route it through wording rules.
        text = _normalize(text)
        for name in _aliases("Power BI"):
            text = re.sub(r"(?<![\w+#])" + re.escape(_normalize(name)) + r"(?![\w+#])", " ", text)
    return any(_contains(term, text) for term in _aliases(keyword))


def _segments(resume):
    # Keep skill lists separate from unrelated actions after a semicolon.
    # Rejoin only clearly signalled continuation lines from PDF extraction.
    lines = []
    for line in resume.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if (lines and lines[-1].strip() and not re.search(r"[.!?]$", lines[-1].strip())
                and re.match(r"^\s*(using|with|to|for|and|covering|including)\b", line, re.I)):
            lines[-1] += "\n" + line
        else:
            lines.append(line)
    return [part.strip() for line in lines
            for part in re.split(r";|(?<=[.!?])\s+", line) if part.strip()]


def _training(evidence):
    return any(_contains(term, evidence) for term in WEAK_CONTEXT_TERMS)


def _application(evidence):
    return (
        bool(_ACTIONS.search(evidence))
        and not re.match(r"^\s*(skills?|technologies|tools)\s*:", evidence, re.I)
        and not _training(evidence)
        and not _UNSUPPORTED.search(evidence)
    )


def _wording_evidence(keyword, segments):
    # A dashboard can support broader visualization terminology.
    # It does not establish experience with a different named tool.
    if _normalize(keyword) not in {*_BI_TERMS, *_VISUALIZATION_TERMS}:
        return ""

    for segment in segments:
        if (
            _application(segment)
            and re.search(r"\bdashboards?\b", segment, re.I)
            and any(
                _matches(tool, segment)
                for tool in ("Power BI", "Tableau", "Looker")
            )
        ):
            return segment

    return ""


def _quote_in_source(quote, resume):
    quote = re.sub(r"^Evidence:\s*", "", _text(quote), flags=re.I)
    if not quote:
        return ""
    # Permit PDF whitespace wrapping, but preserve the exact original source text.
    pattern = r"\s+".join(re.escape(word) for word in quote.split())
    # Sentence/paragraph boundaries preserve context across soft PDF line wraps.
    # A cropped quote cannot remove "Coursework:" or a preceding "never".
    boundaries = [(m.start(), m.end()) for m in re.finditer(r"(?<=[.!?])\s+|\n\s*\n", resume)]
    candidates = []
    for match in re.finditer(r"(?<!\w)" + pattern + r"(?!\w)", resume):
        start = max((end for _, end in boundaries if end <= match.start()), default=0)
        end = min((begin for begin, _ in boundaries if begin >= match.end()), default=len(resume))
        source = resume[start:end].strip()
        if not _UNSUPPORTED.search(source):
            candidates.append(source)
    # A training occurrence must not hide a later genuine work occurrence.
    return next((source for source in candidates if _application(source)), candidates[0] if candidates else "")


def _requirement_terms(subject):
    # Replace whole known phrases with atomic tokens before inspecting words.
    # This prevents unrelated occurrences of "power" and "BI" proving Power BI.
    groups = {canonical: [canonical, *aliases] for canonical, aliases in SAFE_ALIASES.items()}
    groups.update(_CONCEPTS)
    replacements = []
    markers = {}
    for index, (canonical, variants) in enumerate(groups.items()):
        marker = f"knownphrase_{index}"
        markers[marker] = canonical
        replacements.extend((_normalize(variant), marker) for variant in variants)
    normalized = _normalize(subject)
    for variant, marker in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        normalized = re.sub(
            r"(?<![\w+#])" + re.escape(variant) + r"(?![\w+#])", marker, normalized
        )
    terms = [term.rstrip(".") for term in re.findall(r"[\w+#.]+", normalized)]
    return [markers.get(term, term) for term in terms if term and term not in _STOP_WORDS]


def _term_supported(term, quote):
    if _matches(term, quote):
        return True
    if term in _CONCEPTS:
        return bool(_wording_evidence(term, [quote]))
    for forms in (*_VERB_FORMS, *_NOUN_FORMS):
        if term in forms:
            return any(_contains(form, quote) for form in forms)
    return False


def _relevant_quote(subject, quote):
    return any(_term_supported(term, quote) for term in _requirement_terms(subject))


def _covers_requirement(subject, quote):
    # Numeric and duration requirements still need manual review.
    if re.search(
        r"\b(\d+|years?|months?|minimum|least)\b",
        subject,
        re.I,
    ):
        return False

    # Check EVERY remaining term. Supporting a broader concept never erases
    # an extra named tool, certification, metric, or responsibility from the JD.
    # Require the terms in one applied statement; a neighbouring skill list
    # must not borrow application from unrelated work in the same paragraph.
    terms = _requirement_terms(subject)
    return bool(terms) and any(
        _application(segment) and all(_term_supported(term, segment) for term in terms)
        for segment in _segments(quote)
    )


def _advice(subject, source, importance, gap, evidence, explanation):
    actions = {
        "True Gap": f'Add "{subject}" only if you genuinely have this experience or qualification. Otherwise leave it out and consider it a learning or eligibility gap.',
        "Proof Gap": "If you have a genuine example, explain what you did and where you applied it. Keep training labelled as training; add results or metrics only when you can verify them.",
        "Wording Gap": f'Consider the term "{subject}" only if it accurately describes the quoted work. Keep the original tools and facts; confirm the meaning before changing the wording.',
        "Strong Match": "Keep this evidence. No additional claim or unnecessary rewrite is recommended.",
    }
    return dict(subject=subject, source=source, priority="Maintain" if gap == "Strong Match" else importance,
                gap_type=gap, evidence=evidence, explanation=explanation,
                action=actions[gap], truth_guard=TRUTH_GUARD)


def build_recommendations(keywords, requirements, resume_text):
    """Return sorted advice from keyword rows, requirement rows, and the resume.

    Requirement evidence is a dedicated verbatim quote, never an explanation.
    Found without a verified quote is a Proof Gap, not evidence of a missing
    qualification. Partial requirements remain Proof Gaps even with good quotes.
    All input records and all existing scores are left untouched.
    """
    resume = _text(resume_text)
    segments = _segments(resume)
    results = []
    seen = set()
    for source, rows, field in (("Keyword", keywords, "keyword"), ("Requirement", requirements, "requirement")):
        for item in rows if isinstance(rows, list) else []:
            if not isinstance(item, dict):
                continue
            subject = _text(item.get(field))
            key = (source, _normalize(subject))
            if not subject or key in seen:
                continue
            seen.add(key)
            importance = _text(item.get("importance")).title()
            if importance not in {"High", "Medium", "Low"}:
                importance = "Medium"
            status = _text(item.get("status")).casefold()
            evidence = ""
            gap = "True Gap"
            explanation = "No supporting evidence was verified in this resume. This does not establish that you lack the skill."
            if source == "Keyword":
                matches = [s for s in segments if _matches(subject, s) and not _UNSUPPORTED.search(s)]
                strong = next((s for s in matches if _application(s)), "")
                if strong:
                    evidence, gap = strong, "Strong Match"
                    explanation = "The resume describes an application of this keyword."
                elif matches:
                    evidence, gap = matches[0], "Proof Gap"
                    explanation = ("The resume mentions this in training; it does not establish professional application."
                                   if _training(evidence) else "The keyword is present, but practical application is not clearly demonstrated.")
                else:
                    evidence = _wording_evidence(subject, segments)
                    if evidence:
                        gap = "Wording Gap"
                        explanation = "The quoted BI dashboard work supports this broader terminology. Confirm it accurately describes your work before editing."
            else:
                evidence = _quote_in_source(item.get("evidence"), resume)
                if evidence and not _relevant_quote(subject, evidence):
                    evidence = ""
                if evidence:
                    if status == "found" and _application(evidence) and _covers_requirement(subject, evidence):
                        gap = "Strong Match"
                        explanation = "The AI marked this requirement Found and its relevant application quote was verified in the resume. Check the full requirement, including years and qualifications."
                    else:
                        gap = "Proof Gap"
                        explanation = "Some resume evidence is verified, but it does not establish the complete requirement."
                elif status in {"found", "partial"}:
                    gap = "Proof Gap"
                    explanation = "The analysis reports a match, but a relevant source quote could not be verified. Review the requirement and provide a genuine supporting example."
            results.append(_advice(subject, source, importance, gap, evidence, explanation))
    order = {"High": 0, "Medium": 1, "Low": 2, "Maintain": 3}
    return sorted(results, key=lambda row: order[row["priority"]])
