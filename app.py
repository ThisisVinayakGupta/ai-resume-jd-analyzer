import os
from typing import List

import streamlit as st
import pypdf

from google import genai
from google.genai import types
from pydantic import BaseModel

from keyword_matcher import match_keyword, calculate_keyword_coverage


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ResumeMatch Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# PAGE STYLE
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1100px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .subtitle {
            color: #64748b;
            margin-top: -10px;
            margin-bottom: 25px;
        }

        .small-text {
            color: #64748b;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA MODELS
# ============================================================

class CategoryScores(BaseModel):
    skills_match: int
    experience_match: int
    responsibilities_match: int
    tools_match: int
    education_match: int
    evidence_match: int


class Requirement(BaseModel):
    requirement: str
    status: str
    explanation: str


class JDKeyword(BaseModel):
    keyword: str
    importance: str
    category: str


class ResumeAnalysis(BaseModel):
    category_scores: CategoryScores
    requirements: List[Requirement]
    keywords: List[JDKeyword]
    overall_assessment: str
    strengths: List[str]
    missing_skills: List[str]
    experience_explanation: str
    weak_requirements: List[str]
    improvement_suggestions: List[str]
    interview_questions: List[str]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_score(value):
    """Convert a value into a safe 0-100 score."""
    try:
        value = int(value)
    except Exception:
        value = 0

    return max(0, min(100, value))


def safe_text(value):
    """Convert a value into clean text."""
    if value is None:
        return ""
    return str(value).strip()


def safe_list(value):
    """Return a clean list of strings."""
    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


def calculate_final_score(scores):
    """Calculate weighted resume-to-JD score."""

    return round(
        scores["skills"] * 0.25
        + scores["experience"] * 0.20
        + scores["responsibilities"] * 0.20
        + scores["tools"] * 0.15
        + scores["education"] * 0.10
        + scores["evidence"] * 0.10
    )


def calculate_ats(requirements):
    """
    ATS scoring:

    Found   = 100%
    Partial = 50%
    Missing = 0%
    """

    found = 0
    partial = 0
    missing = 0

    for item in requirements:

        status = safe_text(
            item.get("status", "")
        ).lower()

        if status == "found":
            found += 1

        elif status == "partial":
            partial += 1

        else:
            missing += 1

    total = found + partial + missing

    if total == 0:
        return 0, found, partial, missing

    score = round(
        ((found + partial * 0.5) / total) * 100
    )

    return score, found, partial, missing


def match_status(score):

    if score >= 80:
        return (
            "Strong Match",
            "The resume has strong alignment with the target role.",
        )

    if score >= 60:
        return (
            "Moderate Match",
            "The resume has reasonable alignment but has some gaps.",
        )

    return (
        "Low Match",
        "The resume has significant gaps for this role.",
    )


def normalize_requirements(items):

    if not isinstance(items, list):
        return []

    requirements = []

    for item in items:

        if not isinstance(item, dict):
            continue

        requirement = safe_text(
            item.get("requirement")
        )

        explanation = safe_text(
            item.get("explanation")
        )

        status = safe_text(
            item.get("status")
        ).lower()

        if not requirement:
            continue

        if status == "found":
            status = "Found"

        elif status == "partial":
            status = "Partial"

        else:
            status = "Missing"

        requirements.append(
            {
                "requirement": requirement,
                "status": status,
                "explanation": explanation,
            }
        )

    return requirements


def normalize_keywords(items):
    """Return clean JD keyword records for deterministic matching."""
    if not isinstance(items, list):
        return []

    keywords = []
    seen = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        keyword = safe_text(item.get("keyword"))
        importance = safe_text(item.get("importance")).title()
        category = safe_text(item.get("category"))

        if not keyword:
            continue

        key = keyword.lower()
        if key in seen:
            continue
        seen.add(key)

        if importance not in {"High", "Medium", "Low"}:
            importance = "Medium"

        if not category:
            category = "General"

        keywords.append({
            "keyword": keyword,
            "importance": importance,
            "category": category,
        })

    return keywords


def analyze_keywords(keywords, resume_text):
    """Match JD keywords against the actual resume text deterministically."""
    results = []
    statuses = []

    for item in keywords:
        keyword = safe_text(item.get("keyword"))
        match = match_keyword(keyword, resume_text)
        result = {
            "keyword": keyword,
            "importance": safe_text(item.get("importance")) or "Medium",
            "category": safe_text(item.get("category")) or "General",
            "status": match["status"],
            "evidence": match["evidence"],
        }
        results.append(result)
        statuses.append(match["status"])

    score, found, partial, missing = calculate_keyword_coverage(
        keywords, statuses
    )

    return results, score, found, partial, missing


# ============================================================
# GEMINI SETUP
# ============================================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:

    st.error(
        "Gemini API key is not configured. "
        "Please add GEMINI_API_KEY in Streamlit Secrets."
    )

    st.stop()


client = genai.Client(api_key=api_key)


# ============================================================
# HEADER
# ============================================================

st.title("🚀 ResumeMatch Pro")

st.markdown(
    """
    <div class="subtitle">
        AI-powered resume analysis that helps you understand
        how well your resume matches a job.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# INPUT SECTION
# ============================================================

resume_col, job_col = st.columns(2)

with resume_col:

    st.subheader("📄 Your Resume")

    uploaded_file = st.file_uploader(
        "Upload your resume as a PDF",
        type=["pdf"],
    )


with job_col:

    st.subheader("💼 Target Job")

    job_description = st.text_area(
        "Paste the complete job description",
        height=180,
        placeholder="Paste the job description here...",
    )


# ============================================================
# ANALYZE BUTTON
# ============================================================

analyze = st.button(
    "✨ Analyze Resume",
    type="primary",
    use_container_width=True,
)


# ============================================================
# ANALYSIS
# ============================================================

if analyze:

    if uploaded_file is None:

        st.warning(
            "Please upload your resume PDF first."
        )

    elif not job_description.strip():

        st.warning(
            "Please paste the job description first."
        )

    else:

        try:

            # ------------------------------------------------
            # READ PDF
            # ------------------------------------------------

            pdf = pypdf.PdfReader(
                uploaded_file
            )

            resume_text = ""

            for page in pdf.pages:

                text = page.extract_text()

                if text:
                    resume_text += text + "\n"

            resume_text = resume_text.strip()


            if not resume_text:

                st.error(
                    "Could not extract text from the PDF. "
                    "Please upload a text-based resume PDF."
                )

            else:

                # --------------------------------------------
                # PROMPT
                # --------------------------------------------

                prompt = f"""
You are an expert ATS resume evaluator,
professional recruiter, and hiring analyst.

Compare the resume against the job description.

IMPORTANT RULES:

1. Never invent information.

2. Only give credit when the resume provides evidence.

3. Be realistic and conservative.

4. Compare actual professional experience against
   the experience required by the job.

5. Do not count education as professional work experience.

6. Do not treat a related technology as an exact technology
   unless the resume provides evidence.

7. Identify the important requirements from the job description.

8. Classify every important requirement as exactly:

   Found
   Partial
   Missing

9. Found means the resume clearly demonstrates the requirement.

10. Partial means related evidence exists but the requirement
    is not completely satisfied.

11. Missing means there is no meaningful evidence.

12. Compare required years of experience carefully.

13. Generate 4-10 important requirements when possible.

14. Extract 8-20 important ATS keywords or short phrases from the job description when possible.

15. Keywords should be specific skills, technologies, tools, certifications, methods,
    domain terms, or other terms that an ATS/recruiter would reasonably search for.

16. Do not generate generic words such as "team", "work", "company", or "experience".

17. For each keyword, provide importance as exactly High, Medium, or Low.

18. Provide a simple category such as Skill, Tool, Technology, Methodology, Domain,
    Certification, or Other.

19. Category scores must be integers from 0 to 100.

15. Do not inflate scores because the candidate has a related degree.

RESUME:

{resume_text}

JOB DESCRIPTION:

{job_description}
"""


                # --------------------------------------------
                # GEMINI
                # --------------------------------------------

                with st.spinner(
                    "Analyzing your resume..."
                ):

                    response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ResumeAnalysis,
                            temperature=0.2,
                        ),
                    )


                # --------------------------------------------
                # STRUCTURED RESULT
                # --------------------------------------------

                result = response.parsed


                if result is None:

                    st.error(
                        "The AI response could not be processed. "
                        "Please try again."
                    )

                else:

                    # ----------------------------------------
                    # CONVERT TO DICTIONARY
                    # ----------------------------------------

                    data = result.model_dump()


                    # ----------------------------------------
                    # SCORES
                    # ----------------------------------------

                    raw_scores = data.get(
                        "category_scores",
                        {},
                    )


                    scores = {
                        "skills": safe_score(
                            raw_scores.get(
                                "skills_match",
                                0,
                            )
                        ),
                        "experience": safe_score(
                            raw_scores.get(
                                "experience_match",
                                0,
                            )
                        ),
                        "responsibilities": safe_score(
                            raw_scores.get(
                                "responsibilities_match",
                                0,
                            )
                        ),
                        "tools": safe_score(
                            raw_scores.get(
                                "tools_match",
                                0,
                            )
                        ),
                        "education": safe_score(
                            raw_scores.get(
                                "education_match",
                                0,
                            )
                        ),
                        "evidence": safe_score(
                            raw_scores.get(
                                "evidence_match",
                                0,
                            )
                        ),
                    }


                    final_score = calculate_final_score(
                        scores
                    )

                    final_score = safe_score(
                        final_score
                    )


                    # ----------------------------------------
                    # REQUIREMENTS
                    # ----------------------------------------

                    requirements = normalize_requirements(
                        data.get(
                            "requirements",
                            [],
                        )
                    )


                    # ----------------------------------------
                    # ATS
                    # ----------------------------------------

                    (
                        ats_score,
                        found_count,
                        partial_count,
                        missing_count,
                    ) = calculate_ats(
                        requirements
                    )


                    # ----------------------------------------
                    # STATUS
                    # ----------------------------------------

                    (
                        match_label,
                        match_message,
                    ) = match_status(
                        final_score
                    )


                    # ----------------------------------------
                    # CLEAN TEXT
                    # ----------------------------------------

                    data["overall_assessment"] = safe_text(
                        data.get(
                            "overall_assessment"
                        )
                    )

                    data["experience_explanation"] = safe_text(
                        data.get(
                            "experience_explanation"
                        )
                    )

                    data["strengths"] = safe_list(
                        data.get(
                            "strengths",
                            [],
                        )
                    )

                    data["missing_skills"] = safe_list(
                        data.get(
                            "missing_skills",
                            [],
                        )
                    )

                    data["weak_requirements"] = safe_list(
                        data.get(
                            "weak_requirements",
                            [],
                        )
                    )

                    data["improvement_suggestions"] = safe_list(
                        data.get(
                            "improvement_suggestions",
                            [],
                        )
                    )

                    data["interview_questions"] = safe_list(
                        data.get(
                            "interview_questions",
                            [],
                        )
                    )

                    data["requirements"] = requirements


                    # ----------------------------------------
                    # SAVE TO SESSION STATE
                    # ----------------------------------------

                    st.session_state["analysis"] = data

                    st.session_state["scores"] = scores

                    st.session_state["final_score"] = final_score

                    st.session_state["ats_score"] = ats_score

                    st.session_state["found_count"] = found_count

                    st.session_state["partial_count"] = partial_count

                    st.session_state["missing_count"] = missing_count

                    # ----------------------------------------
                    # ATS KEYWORDS
                    # ----------------------------------------

                    keywords = normalize_keywords(
                        data.get("keywords", [])
                    )

                    (
                        keyword_results,
                        keyword_score,
                        keyword_found_count,
                        keyword_partial_count,
                        keyword_missing_count,
                    ) = analyze_keywords(
                        keywords, resume_text
                    )

                    st.session_state["keywords"] = keyword_results
                    st.session_state["keyword_score"] = keyword_score
                    st.session_state["keyword_found_count"] = keyword_found_count
                    st.session_state["keyword_partial_count"] = keyword_partial_count
                    st.session_state["keyword_missing_count"] = keyword_missing_count

                    st.session_state["match_label"] = match_label

                    st.session_state["match_message"] = match_message


                    st.success(
                        "Analysis completed successfully."
                    )


        except Exception as error:

            st.error(
                "Something went wrong while analyzing the resume."
            )

            st.caption(
                f"Technical details: {error}"
            )


# ============================================================
# RESULTS
# ============================================================

if "analysis" in st.session_state:

    data = st.session_state["analysis"]

    scores = st.session_state["scores"]

    final_score = st.session_state["final_score"]

    ats_score = st.session_state["ats_score"]

    found_count = st.session_state["found_count"]

    partial_count = st.session_state["partial_count"]

    missing_count = st.session_state["missing_count"]

    keywords = st.session_state.get("keywords", [])
    keyword_score = st.session_state.get("keyword_score", 0)
    keyword_found_count = st.session_state.get("keyword_found_count", 0)
    keyword_partial_count = st.session_state.get("keyword_partial_count", 0)
    keyword_missing_count = st.session_state.get("keyword_missing_count", 0)

    match_label = st.session_state["match_label"]

    match_message = st.session_state["match_message"]

    requirements = data.get(
        "requirements",
        [],
    )


    # ========================================================
    # ANALYSIS HEADER
    # ========================================================

    st.divider()

    st.header("📊 Resume Match Analysis")

    st.markdown(
        """
        <div class="small-text">
            AI evaluation across resume-to-job compatibility dimensions.
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # TOP SCORE
    # ========================================================

    score_col, fit_col = st.columns(2)

    with score_col:

        st.metric(
            "Overall Match Score",
            f"{final_score}%",
        )


    with fit_col:

        st.metric(
            "Candidate Fit",
            match_label,
        )


    st.progress(
        final_score / 100,
        text=f"Overall compatibility: {final_score}%",
    )


    if final_score >= 80:

        st.success(match_message)

    elif final_score >= 60:

        st.warning(match_message)

    else:

        st.error(match_message)


    # ========================================================
    # MATCH BREAKDOWN
    # ========================================================

    st.subheader("📈 Match Breakdown")


    breakdown = [
        ("Skills", scores["skills"]),
        ("Experience", scores["experience"]),
        ("Responsibilities", scores["responsibilities"]),
        ("Tools & Technology", scores["tools"]),
        ("Education", scores["education"]),
        ("Evidence / Projects", scores["evidence"]),
    ]


    row_one = st.columns(3)


    for column, item in zip(
        row_one,
        breakdown[:3],
    ):

        label, value = item

        with column:

            st.metric(
                label,
                f"{value}%",
            )

            st.progress(
                value / 100,
            )


    row_two = st.columns(3)


    for column, item in zip(
        row_two,
        breakdown[3:],
    ):

        label, value = item

        with column:

            st.metric(
                label,
                f"{value}%",
            )

            st.progress(
                value / 100,
            )


    # ========================================================
    # ATS COVERAGE
    # ========================================================

    st.divider()

    st.subheader("🎯 ATS Requirement Coverage")

    st.markdown(
        """
        <div class="small-text">
            Coverage of important requirements identified from the job description.
        </div>
        """,
        unsafe_allow_html=True,
    )


    ats_col1, ats_col2, ats_col3, ats_col4 = st.columns(4)


    with ats_col1:

        st.metric(
            "ATS Coverage",
            f"{ats_score}%",
        )


    with ats_col2:

        st.metric(
            "Found",
            found_count,
        )


    with ats_col3:

        st.metric(
            "Partial",
            partial_count,
        )


    with ats_col4:

        st.metric(
            "Missing",
            missing_count,
        )


    st.progress(
        ats_score / 100,
        text=f"ATS requirement coverage: {ats_score}%",
    )


    # ========================================================
    # ATS KEYWORD ANALYSIS
    # ========================================================

    st.divider()

    st.subheader("🔑 ATS Keyword Analysis")

    st.markdown(
        """
        <div class="small-text">
            Important keywords are extracted from the job description, then matched
            against the actual resume text using deterministic Python rules.
        </div>
        """,
        unsafe_allow_html=True,
    )

    keyword_col1, keyword_col2, keyword_col3, keyword_col4 = st.columns(4)

    with keyword_col1:
        st.metric("Keyword Coverage", f"{keyword_score}%")

    with keyword_col2:
        st.metric("Found", keyword_found_count)

    with keyword_col3:
        st.metric("Partial", keyword_partial_count)

    with keyword_col4:
        st.metric("Missing", keyword_missing_count)

    st.progress(
        keyword_score / 100,
        text=f"Keyword coverage: {keyword_score}%",
    )

    if not keywords:
        st.info("No ATS keywords were extracted from the job description.")
    else:
        for item in keywords:
            keyword = safe_text(item.get("keyword"))
            importance = safe_text(item.get("importance")) or "Medium"
            category = safe_text(item.get("category")) or "General"
            status = safe_text(item.get("status"))
            evidence = safe_text(item.get("evidence"))

            if status == "Found":
                icon = "✅"
            elif status == "Partial":
                icon = "⚠️"
            else:
                icon = "❌"

            with st.container(border=True):
                st.markdown(
                    f"**{icon} {keyword}** &nbsp; · &nbsp; {importance} importance &nbsp; · &nbsp; {category}"
                )

                if status == "Found":
                    st.success("Found")
                elif status == "Partial":
                    st.warning("Partial")
                else:
                    st.error("Missing")

                if evidence:
                    st.caption(evidence)

        missing_keywords = [
            item for item in keywords
            if safe_text(item.get("status")) == "Missing"
        ]

        if missing_keywords:
            st.markdown("**Priority keyword gaps**")
            for item in sorted(
                missing_keywords,
                key=lambda value: {"High": 0, "Medium": 1, "Low": 2}.get(
                    safe_text(value.get("importance")), 1
                ),
            )[:8]:
                st.warning(
                    f"{item.get('keyword')} ({item.get('importance')}): "
                    "No evidence was found in the resume. Add it only if you genuinely have this skill or experience."
                )


    # ========================================================
    # REQUIREMENT DETAILS
    # ========================================================

    st.subheader("📋 Requirement Details")


    if not requirements:

        st.info(
            "No specific requirements were identified."
        )

    else:

        for item in requirements:

            requirement = safe_text(
                item.get(
                    "requirement",
                    "",
                )
            )

            status = safe_text(
                item.get(
                    "status",
                    "Missing",
                )
            ).lower()

            explanation = safe_text(
                item.get(
                    "explanation",
                    "",
                )
            )


            if not requirement:
                continue


            # ----------------------------------------------
            # FOUND
            # ----------------------------------------------

            if status == "found":

                with st.container(border=True):

                    st.markdown(
                        f"**✅ {requirement}**"
                    )

                    st.success(
                        "Found"
                    )

                    if explanation:

                        st.write(
                            explanation
                        )


            # ----------------------------------------------
            # PARTIAL
            # ----------------------------------------------

            elif status == "partial":

                with st.container(border=True):

                    st.markdown(
                        f"**⚠️ {requirement}**"
                    )

                    st.warning(
                        "Partial"
                    )

                    if explanation:

                        st.write(
                            explanation
                        )


            # ----------------------------------------------
            # MISSING
            # ----------------------------------------------

            else:

                with st.container(border=True):

                    st.markdown(
                        f"**❌ {requirement}**"
                    )

                    st.error(
                        "Missing"
                    )

                    if explanation:

                        st.write(
                            explanation
                        )


    # ========================================================
    # OVERALL ASSESSMENT
    # ========================================================

    st.subheader("🧠 Overall Assessment")

    assessment = data.get(
        "overall_assessment",
        "",
    )

    if assessment:

        st.info(
            assessment
        )


    # ========================================================
    # EXPERIENCE
    # ========================================================

    st.subheader("💼 Experience Match")

    experience = data.get(
        "experience_explanation",
        "",
    )

    if experience:

        st.write(
            experience
        )


    # ========================================================
    # STRENGTHS / MISSING SKILLS
    # ========================================================

    left, right = st.columns(2)


    with left:

        st.subheader("✓ Resume Strengths")

        strengths = data.get(
            "strengths",
            [],
        )

        if strengths:

            for item in strengths:

                st.success(
                    item
                )

        else:

            st.write(
                "No specific strengths identified."
            )


    with right:

        st.subheader("⚠ Missing / Weak Skills")

        missing_skills = data.get(
            "missing_skills",
            [],
        )

        if missing_skills:

            for item in missing_skills:

                st.warning(
                    item
                )

        else:

            st.success(
                "No major missing skills identified."
            )


    # ========================================================
    # WEAK REQUIREMENTS
    # ========================================================

    st.subheader("⚠ Weak Requirements")

    weak_requirements = data.get(
        "weak_requirements",
        [],
    )


    if weak_requirements:

        for item in weak_requirements:

            st.warning(
                item
            )

    else:

        st.success(
            "No major weak requirements identified."
        )


    # ========================================================
    # IMPROVEMENT SUGGESTIONS
    # ========================================================

    st.subheader("🚀 Improvement Suggestions")

    suggestions = data.get(
        "improvement_suggestions",
        [],
    )


    if suggestions:

        for item in suggestions:

            st.info(
                item
            )

    else:

        st.write(
            "No additional suggestions identified."
        )


    # ========================================================
    # INTERVIEW QUESTIONS
    # ========================================================

    st.subheader("🎤 Interview Preparation")

    questions = data.get(
        "interview_questions",
        [],
    )


    if questions:

        for number, question in enumerate(
            questions,
            start=1,
        ):

            st.write(
                f"**{number}. {question}**"
            )

    else:

        st.write(
            "No interview questions generated."
        )
