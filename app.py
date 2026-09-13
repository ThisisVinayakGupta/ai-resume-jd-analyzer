import os
import json
from typing import List

import streamlit as st
import pypdf

from google import genai
from google.genai import types
from pydantic import BaseModel


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ResumeMatch Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #f8fafc;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1 {
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    h2, h3 {
        font-weight: 650;
    }

    .subtitle {
        color: #64748b;
        margin-top: -10px;
        margin-bottom: 25px;
    }

    .section-description {
        color: #64748b;
        font-size: 0.9rem;
        margin-top: -10px;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
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


class ResumeAnalysis(BaseModel):

    category_scores: CategoryScores

    requirements: List[Requirement]

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

def clamp_score(value):
    """Keep a score between 0 and 100."""

    try:
        value = int(value)
    except Exception:
        value = 0

    return max(0, min(100, value))


def clean_text(value):
    """Safely convert a value to clean text."""

    if value is None:
        return ""

    return str(value).strip()


def clean_list(items):
    """Safely clean AI-generated lists."""

    if not isinstance(items, list):
        return []

    result = []

    for item in items:

        text = clean_text(item)

        if text:
            result.append(text)

    return result


def calculate_ats_score(requirements):
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

        status = clean_text(
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

        return 0, 0, 0, 0

    score = round(
        (
            found + (partial * 0.5)
        )
        / total
        * 100
    )

    return score, found, partial, missing


def get_match_status(score):

    if score >= 80:

        return (
            "Strong Match",
            "The resume has strong alignment with the target role."
        )

    elif score >= 60:

        return (
            "Moderate Match",
            "The resume has reasonable alignment but has some gaps."
        )

    else:

        return (
            "Low Match",
            "The resume has significant gaps for this role."
        )


def normalize_requirements(requirements):
    """
    Clean and normalize Gemini requirement output.
    """

    if not isinstance(requirements, list):
        return []

    cleaned = []

    for item in requirements:

        if not isinstance(item, dict):
            continue

        requirement = clean_text(
            item.get("requirement")
        )

        status = clean_text(
            item.get("status")
        ).lower()

        explanation = clean_text(
            item.get("explanation")
        )

        if not requirement:
            continue

        if status == "found":

            normalized_status = "Found"

        elif status == "partial":

            normalized_status = "Partial"

        else:

            normalized_status = "Missing"

        cleaned.append(
            {
                "requirement": requirement,
                "status": normalized_status,
                "explanation": explanation
            }
        )

    return cleaned


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


client = genai.Client(
    api_key=api_key
)


# ============================================================
# HEADER
# ============================================================

st.title("🚀 ResumeMatch Pro")

st.markdown(
    """
    <p class="subtitle">
    AI-powered resume analysis that helps you understand
    how well your resume matches a job.
    </p>
    """,
    unsafe_allow_html=True
)


# ============================================================
# INPUT AREA
# ============================================================

resume_col, job_col = st.columns(2)


with resume_col:

    st.subheader("📄 Your Resume")

    uploaded_file = st.file_uploader(
        "Upload your resume as a PDF",
        type=["pdf"]
    )


with job_col:

    st.subheader("💼 Target Job")

    job_description = st.text_area(
        "Paste the complete job description",
        height=180,
        placeholder="Paste the job description here..."
    )


# ============================================================
# ANALYZE BUTTON
# ============================================================

analyze_button = st.button(
    "✨ Analyze Resume",
    type="primary",
    use_container_width=True
)


# ============================================================
# ANALYZE RESUME
# ============================================================

if analyze_button:

    # --------------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------------

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

            pdf_reader = pypdf.PdfReader(
                uploaded_file
            )

            resume_text = ""

            for page in pdf_reader.pages:

                page_text = page.extract_text()

                if page_text:

                    resume_text += page_text + "\n"


            resume_text = resume_text.strip()


            if not resume_text:

                st.error(
                    "I could not extract text from this PDF. "
                    "Please upload a text-based PDF resume."
                )

            else:

                # --------------------------------------------
                # GEMINI PROMPT
                # --------------------------------------------

                prompt = f"""
You are an expert ATS resume evaluator,
professional recruiter, and hiring analyst.

Compare the candidate's resume against the target
job description.

IMPORTANT RULES:

1. Do not invent information.

2. Only give credit when the resume contains evidence.

3. Be realistic and conservative.

4. Compare actual professional experience against
   required professional experience.

5. Do not treat education as professional experience.

6. Do not treat a related technology as an exact
   technology unless the resume provides evidence.

7. Identify the important requirements from the
   job description.

8. For every important requirement use exactly one
   of these statuses:

   Found
   Partial
   Missing

9. Found means the resume clearly demonstrates
   the requirement.

10. Partial means related evidence exists but the
    requirement is not completely satisfied.

11. Missing means there is no meaningful evidence
    for the requirement.

12. For years of experience, compare the actual
    demonstrated professional experience against
    the requested years.

13. Keep the explanations concise and useful.

14. All six category scores must be integers
    between 0 and 100.

15. Generate between 4 and 10 important job
    requirements when possible.

16. Do not inflate scores simply because the candidate
    has a related degree or is studying the subject.

RESUME:

{resume_text}

TARGET JOB DESCRIPTION:

{job_description}
"""


                # --------------------------------------------
                # CALL GEMINI
                # --------------------------------------------

                with st.spinner(
                    "Analyzing your resume against the job..."
                ):

                    response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ResumeAnalysis,
                            temperature=0.2
                        )
                    )


                # --------------------------------------------
                # GET STRUCTURED RESULT
                # --------------------------------------------

                result = response.parsed


                # --------------------------------------------
                # FALLBACK JSON PARSING
                # --------------------------------------------

                if result is None:

                    response_text = getattr(
                        response,
                        "text",
                        None
                    )

                    if response_text:

                        try:

                            result = ResumeAnalysis.model_validate(
                                json.loads(response_text)
                            )

                        except Exception:

                            result = None


                if result is None:

                    st.error(
                        "The AI response could not be processed. "
                        "Please try again."
                    )

                else:

                    # ----------------------------------------
                    # CONVERT TO DICTIONARY
                    # ----------------------------------------

                    result_data = result.model_dump()


                    # ----------------------------------------
                    # CATEGORY SCORES
                    # ----------------------------------------

                    category_scores = result_data.get(
                        "category_scores",
                        {}
                    )


                    skills_score = clamp_score(
                        category_scores.get(
                            "skills_match",
                            0
                        )
                    )


                    experience_score = clamp_score(
                        category_scores.get(
                            "experience_match",
                            0
                        )
                    )


                    responsibilities_score = clamp_score(
                        category_scores.get(
                            "responsibilities_match",
                            0
                        )
                    )


                    tools_score = clamp_score(
                        category_scores.get(
                            "tools_match",
                            0
                        )
                    )


                    education_score = clamp_score(
                        category_scores.get(
                            "education_match",
                            0
                        )
                    )


                    evidence_score = clamp_score(
                        category_scores.get(
                            "evidence_match",
                            0
                        )
                    )


                    # ----------------------------------------
                    # WEIGHTED SCORE
                    # ----------------------------------------

                    final_score = round(

                        skills_score * 0.25

                        + experience_score * 0.20

                        + responsibilities_score * 0.20

                        + tools_score * 0.15

                        + education_score * 0.10

                        + evidence_score * 0.10

                    )


                    final_score = clamp_score(
                        final_score
                    )


                    # ----------------------------------------
                    # ATS REQUIREMENTS
                    # ----------------------------------------

                    requirements = normalize_requirements(
                        result_data.get(
                            "requirements",
                            []
                        )
                    )


                    # ----------------------------------------
                    # ATS SCORE
                    # ----------------------------------------

                    (
                        ats_score,
                        found_count,
                        partial_count,
                        missing_count
                    ) = calculate_ats_score(
                        requirements
                    )


                    # ----------------------------------------
                    # MATCH STATUS
                    # ----------------------------------------

                    (
                        match_status,
                        status_message
                    ) = get_match_status(
                        final_score
                    )


                    # ----------------------------------------
                    # CLEAN TEXT FIELDS
                    # ----------------------------------------

                    result_data["overall_assessment"] = clean_text(
                        result_data.get(
                            "overall_assessment"
                        )
                    )


                    result_data["experience_explanation"] = clean_text(
                        result_data.get(
                            "experience_explanation"
                        )
                    )


                    result_data["strengths"] = clean_list(
                        result_data.get(
                            "strengths",
                            []
                        )
                    )


                    result_data["missing_skills"] = clean_list(
                        result_data.get(
                            "missing_skills",
                            []
                        )
                    )


                    result_data["weak_requirements"] = clean_list(
                        result_data.get(
                            "weak_requirements",
                            []
                        )
                    )


                    result_data["improvement_suggestions"] = clean_list(
                        result_data.get(
                            "improvement_suggestions",
                            []
                        )
                    )


                    result_data["interview_questions"] = clean_list(
                        result_data.get(
                            "interview_questions",
                            []
                        )
                    )


                    result_data["requirements"] = requirements


                    # ----------------------------------------
                    # SAVE RESULT
                    # ----------------------------------------

                    st.session_state["analysis_result"] = result_data

                    st.session_state["final_score"] = final_score

                    st.session_state["ats_score"] = ats_score

                    st.session_state["found_count"] = found_count

                    st.session_state["partial_count"] = partial_count

                    st.session_state["missing_count"] = missing_count

                    st.session_state["match_status"] = match_status

                    st.session_state["status_message"] = status_message


                    st.success(
                        "Resume analysis completed successfully."
                    )


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "analysis_result" in st.session_state:

    result = st.session_state["analysis_result"]


    # --------------------------------------------------------
    # GET SAVED VALUES
    # --------------------------------------------------------

    final_score = st.session_state.get(
        "final_score",
        0
    )


    ats_score = st.session_state.get(
        "ats_score",
        0
    )


    found_count = st.session_state.get(
        "found_count",
        0
    )


    partial_count = st.session_state.get(
        "partial_count",
        0
    )


    missing_count = st.session_state.get(
        "missing_count",
        0
    )


    match_status = st.session_state.get(
        "match_status",
        "Unknown"
    )


    status_message = st.session_state.get(
        "status_message",
        ""
    )


    # --------------------------------------------------------
    # CATEGORY SCORES
    # --------------------------------------------------------

    category_scores = result.get(
        "category_scores",
        {}
    )


    skills_score = clamp_score(
        category_scores.get(
            "skills_match",
            0
        )
    )


    experience_score = clamp_score(
        category_scores.get(
            "experience_match",
            0
        )
    )


    responsibilities_score = clamp_score(
        category_scores.get(
            "responsibilities_match",
            0
        )
    )


    tools_score = clamp_score(
        category_scores.get(
            "tools_match",
            0
        )
    )


    education_score = clamp_score(
        category_scores.get(
            "education_match",
            0
        )
    )


    evidence_score = clamp_score(
        category_scores.get(
            "evidence_match",
            0
        )
    )


    # --------------------------------------------------------
    # REQUIREMENTS
    # --------------------------------------------------------

    requirements = result.get(
        "requirements",
        []
    )


    # ========================================================
    # RESULTS
    # ========================================================

    st.divider()

    st.header("📊 Resume Match Analysis")

    st.markdown(
        """
        <p class="section-description">
        AI evaluation across resume-to-job compatibility dimensions.
        </p>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # TOP SCORE
    # ========================================================

    score_col, fit_col = st.columns(2)


    with score_col:

        st.metric(
            "Overall Match Score",
            f"{final_score}%"
        )


    with fit_col:

        st.metric(
            "Candidate Fit",
            match_status
        )


    st.progress(
        final_score / 100,
        text=f"Overall compatibility: {final_score}%"
    )


    if final_score >= 80:

        st.success(
            status_message
        )

    elif final_score >= 60:

        st.warning(
            status_message
        )

    else:

        st.error(
            status_message
        )


    # ========================================================
    # MATCH BREAKDOWN
    # ========================================================

    st.subheader("📈 Match Breakdown")


    score_items = [
        ("Skills", skills_score),
        ("Experience", experience_score),
        ("Responsibilities", responsibilities_score),
        ("Tools & Technology", tools_score),
        ("Education", education_score),
        ("Evidence / Projects", evidence_score)
    ]


    first_row = st.columns(3)


    for column, (label, value) in zip(
        first_row,
        score_items[:3]
    ):

        with column:

            st.metric(
                label,
                f"{value}%"
            )

            st.progress(
                value / 100
            )


    second_row = st.columns(3)


    for column, (label, value) in zip(
        second_row,
        score_items[3:]
    ):

        with column:

            st.metric(
                label,
                f"{value}%"
            )

            st.progress(
                value / 100
            )


    # ========================================================
    # ATS COVERAGE
    # ========================================================

    st.divider()

    st.subheader("🎯 ATS Requirement Coverage")

    st.markdown(
        """
        <p class="section-description">
        How well your resume covers the important requirements
        in the target job description.
        </p>
        """,
        unsafe_allow_html=True
    )


    ats_col1, ats_col2, ats_col3, ats_col4 = st.columns(4)


    with ats_col1:

        st.metric(
            "ATS Coverage",
            f"{ats_score}%"
        )


    with ats_col2:

        st.metric(
            "Found",
            found_count
        )


    with ats_col3:

        st.metric(
            "Partial",
            partial_count
        )


    with ats_col4:

        st.metric(
            "Missing",
            missing_count
        )


    st.progress(
        ats_score / 100,
        text=f"ATS requirement coverage: {ats_score}%"
    )


    # ========================================================
    # REQUIREMENT DETAILS
    # ========================================================

    st.subheader("📋 Requirement Details")


    if not requirements:

        st.info(
            "No specific requirements were identified from this job description."
        )


    else:

        for index, item in enumerate(
            requirements
        ):

            requirement = clean_text(
                item.get(
                    "requirement",
                    ""
                )
            )


            status = clean_text(
                item.get(
                    "status",
                    "Missing"
                )
            ).lower()


            explanation = clean_text(
                item.get(
                    "explanation",
                    ""
                )
            )


            if not requirement:
                continue


            # ----------------------------------------------
            # FOUND
            # ----------------------------------------------

            if status == "found":

                with st.container(
                    border=True
                ):

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

                with st.container(
                    border=True
                ):

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

                with st.container(
                    border=True
                ):

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


    overall_assessment = result.get(
        "overall_assessment",
        ""
    )


    if overall_assessment:

        st.info(
            overall_assessment
        )


    # ========================================================
    # EXPERIENCE
    # ========================================================

    st.subheader("💼 Experience Match")


    experience_explanation = result.get(
        "experience_explanation",
        ""
    )


    if experience_explanation:

        st.write(
            experience_explanation
        )


    # ========================================================
    # STRENGTHS / MISSING SKILLS
    # ========================================================

    strength_col, missing_col = st.columns(2)


    with strength_col:

        st.subheader("✓ Resume Strengths")


        strengths = result.get(
            "strengths",
            []
        )


        if strengths:

            for item in strengths:

                st.success(
                    item
                )

        else:

            st.write(
                "No specific strengths were identified."
            )


    with missing_col:

        st.subheader("⚠ Missing / Weak Skills")


        missing_skills = result.get(
            "missing_skills",
            []
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


    weak_requirements = result.get(
        "weak_requirements",
        []
    )


    if weak_requirements:

        for item in weak_requirements:

            st.warning(
                item
            )

    else:

        st.success(
            "No major weak requirements were identified."
        )


    # ========================================================
    # IMPROVEMENT SUGGESTIONS
    # ========================================================

    st.subheader("🚀 Improvement Suggestions")


    suggestions = result.get(
        "improvement_suggestions",
        []
    )


    if suggestions:

        for item in suggestions:

            st.info(
                item
            )

    else:

        st.write(
            "No additional improvement suggestions were identified."
        )


    # ========================================================
    # INTERVIEW PREPARATION
    # ========================================================

    st.subheader("🎤 Interview Preparation")


    interview_questions = result.get(
        "interview_questions",
        []
    )


    if interview_questions:

        for number, question in enumerate(
            interview_questions,
            start=1
        ):

            st.write(
                f"**{number}. {question}**"
            )

    else:

        st.write(
            "No interview questions were generated."
        )
