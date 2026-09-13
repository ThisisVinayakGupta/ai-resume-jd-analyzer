import os
import html
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

    .requirement-card {
        padding: 14px 16px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #e2e8f0;
        background: white;
    }

    .requirement-title {
        font-weight: 600;
        font-size: 0.98rem;
    }

    .requirement-detail {
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 5px;
    }

    .found {
        color: #047857;
        font-weight: 600;
    }

    .partial {
        color: #b45309;
        font-weight: 600;
    }

    .missing {
        color: #dc2626;
        font-weight: 600;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# PYDANTIC DATA MODELS
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
    """
    Keeps AI-generated scores safely between 0 and 100.
    """
    try:
        value = int(value)
    except Exception:
        value = 0

    return max(0, min(100, value))


def clean_list(items):
    """
    Converts AI list output into clean strings.
    """
    if not items:
        return []

    cleaned = []

    for item in items:

        text = str(item).strip()

        if text:
            cleaned.append(text)

    return cleaned


def calculate_ats_score(requirements):
    """
    Calculates ATS coverage independently from Gemini.

    Found   = 100% credit
    Partial = 50% credit
    Missing = 0% credit
    """

    found = 0
    partial = 0
    missing = 0

    for item in requirements:

        status = str(item.get("status", "")).strip().lower()

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
        ((found + (partial * 0.5)) / total) * 100
    )

    return score, found, partial, missing


def get_match_status(score):
    """
    Converts final score into a simple candidate-fit label.
    """

    if score >= 80:
        return (
            "Strong Match",
            "The resume has strong alignment with the target role."
        )

    if score >= 60:
        return (
            "Moderate Match",
            "The resume has reasonable alignment but has some gaps."
        )

    return (
        "Low Match",
        "The resume has significant gaps for this role."
    )


# ============================================================
# GEMINI API SETUP
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
    <p class="subtitle">
    AI-powered resume analysis that helps you understand
    how well your resume matches a job.
    </p>
    """,
    unsafe_allow_html=True
)


# ============================================================
# INPUT SECTION
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
# RUN ANALYSIS
# ============================================================

if analyze_button:

    # --------------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------------

    if uploaded_file is None:

        st.warning(
            "Please upload your resume PDF first."
        )

        st.stop()


    if not job_description.strip():

        st.warning(
            "Please paste the job description first."
        )

        st.stop()


    try:

        # ----------------------------------------------------
        # EXTRACT RESUME TEXT
        # ----------------------------------------------------

        pdf_reader = pypdf.PdfReader(uploaded_file)

        resume_text = ""

        for page in pdf_reader.pages:

            text = page.extract_text()

            if text:

                resume_text += text + "\n"


        resume_text = resume_text.strip()


        if not resume_text:

            st.error(
                "I could not extract text from this PDF. "
                "Please upload a text-based resume PDF."
            )

            st.stop()


        # ----------------------------------------------------
        # GEMINI PROMPT
        # ----------------------------------------------------

        prompt = f"""
You are an expert ATS resume evaluator and professional recruiter.

Your job is to compare the candidate's resume against the target
job description.

IMPORTANT RULES:

1. Do not invent experience, skills, tools, education, projects,
   certifications, or achievements.

2. Only give credit when the resume provides evidence.

3. Be realistic and conservative.

4. Compare the candidate's actual experience against the experience
   requirement in the job description.

5. Do not treat a degree as equivalent to professional experience.

6. Do not treat a related skill as an exact skill unless the evidence
   supports it.

7. Do not give a high score simply because the candidate appears
   generally suitable.

8. Identify the most important requirements from the job description.

9. For each important requirement classify it as exactly one:

   Found
   Partial
   Missing

10. Found:
    The resume clearly demonstrates the requirement.

11. Partial:
    The resume has related evidence but does not completely satisfy
    the requirement.

12. Missing:
    There is no meaningful evidence in the resume.

13. For years of experience, carefully compare the required years
    against the candidate's demonstrated professional experience.

14. Keep explanations concise and useful.

15. The six category scores must be integers from 0 to 100.

RESUME:

{resume_text}

TARGET JOB DESCRIPTION:

{job_description}
"""


        # ----------------------------------------------------
        # CALL GEMINI
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # GET STRUCTURED RESULT
        # ----------------------------------------------------

        result = response.parsed


        if result is None:

            st.error(
                "The AI response could not be processed. "
                "Please try again."
            )

            st.stop()


        # ----------------------------------------------------
        # CONVERT RESULT TO PLAIN DICTIONARY
        # ----------------------------------------------------

        if hasattr(result, "model_dump"):

            result_data = result.model_dump()

        elif hasattr(result, "dict"):

            result_data = result.dict()

        else:

            result_data = result


        # ----------------------------------------------------
        # CLEAN CATEGORY SCORES
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # WEIGHTED FINAL SCORE
        # ----------------------------------------------------

        final_score = round(

            skills_score * 0.25

            + experience_score * 0.20

            + responsibilities_score * 0.20

            + tools_score * 0.15

            + education_score * 0.10

            + evidence_score * 0.10

        )


        final_score = clamp_score(final_score)


        # ----------------------------------------------------
        # REQUIREMENTS
        # ----------------------------------------------------

        requirements = result_data.get(
            "requirements",
            []
        )


        if not isinstance(requirements, list):

            requirements = []


        clean_requirements = []


        for item in requirements:

            if not isinstance(item, dict):

                continue


            requirement = str(
                item.get(
                    "requirement",
                    ""
                )
            ).strip()


            status = str(
                item.get(
                    "status",
                    "Missing"
                )
            ).strip()


            explanation = str(
                item.get(
                    "explanation",
                    ""
                )
            ).strip()


            if not requirement:

                continue


            status_lower = status.lower()


            if status_lower == "found":

                normalized_status = "Found"


            elif status_lower == "partial":

                normalized_status = "Partial"


            else:

                normalized_status = "Missing"


            clean_requirements.append(
                {
                    "requirement": requirement,
                    "status": normalized_status,
                    "explanation": explanation
                }
            )


        # ----------------------------------------------------
        # ATS SCORE
        # ----------------------------------------------------

        (
            ats_score,
            found_count,
            partial_count,
            missing_count
        ) = calculate_ats_score(
            clean_requirements
        )


        # ----------------------------------------------------
        # MATCH STATUS
        # ----------------------------------------------------

        match_status, status_message = get_match_status(
            final_score
        )


        # ----------------------------------------------------
        # CLEAN OTHER FIELDS
        # ----------------------------------------------------

        result_data["requirements"] = clean_requirements

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


        # ----------------------------------------------------
        # SAVE EVERYTHING NEEDED FOR FUTURE RERUNS
        # ----------------------------------------------------

        st.session_state["analysis_result"] = result_data

        st.session_state["final_score"] = final_score

        st.session_state["ats_score"] = ats_score

        st.session_state["found_count"] = found_count

        st.session_state["partial_count"] = partial_count

        st.session_state["missing_count"] = missing_count

        st.session_state["match_status"] = match_status

        st.session_state["status_message"] = status_message


        # ----------------------------------------------------
        # FORCE CLEAN RERUN
        # ----------------------------------------------------

        st.rerun()


    except Exception:

        st.error(
            "Something went wrong while analyzing the resume."
        )

        st.info(
            "Please try the analysis again. "
            "If the problem continues, open Manage app → Logs "
            "in Streamlit Cloud."
        )


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "analysis_result" in st.session_state:

    result = st.session_state["analysis_result"]


    # --------------------------------------------------------
    # RECOVER ALL VALUES FROM SESSION STATE
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
    # RECOVER CATEGORY SCORES
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
    # RESULTS HEADER
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

        st.success(status_message)

    elif final_score >= 60:

        st.warning(status_message)

    else:

        st.error(status_message)


    # ========================================================
    # MATCH BREAKDOWN
    # ========================================================

    st.subheader("📈 Match Breakdown")


    scores = [
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
        scores[:3]
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
        scores[3:]
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
    # ATS REQUIREMENT COVERAGE
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


    ats_col1, ats_col2, ats_col3 = st.columns(3)


    with ats_col1:

        st.metric(
            "ATS Coverage",
            f"{ats_score}%"
        )


    with ats_col2:

        st.metric(
            "Requirements Found",
            found_count
        )


    with ats_col3:

        st.metric(
            "Requirements Missing",
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

for item in requirements:

    requirement = str(
        item.get("requirement", "")
    ).strip()

    status = str(
        item.get("status", "Missing")
    ).strip().lower()

    explanation = str(
        item.get("explanation", "")
    ).strip()


    if not requirement:
        continue


    # ----------------------------------------------------
    # FOUND
    # ----------------------------------------------------

    if status == "found":

        with st.container(border=True):

            st.markdown(
                f"### ✅ {requirement}"
            )

            st.success(
                "Found"
            )

            if explanation:

                st.write(
                    explanation
                )


    # ----------------------------------------------------
    # PARTIAL
    # ----------------------------------------------------

    elif status == "partial":

        with st.container(border=True):

            st.markdown(
                f"### ⚠️ {requirement}"
            )

            st.warning(
                "Partial"
            )

            if explanation:

                st.write(
                    explanation
                )


    # ----------------------------------------------------
    # MISSING
    # ----------------------------------------------------

    else:

        with st.container(border=True):

            st.markdown(
                f"### ❌ {requirement}"
            )

            st.error(
                "Missing"
            )

            if explanation:

                st.write(
                    explanation
                )
