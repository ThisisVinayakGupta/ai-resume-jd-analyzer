import os
import streamlit as st
import pypdf

from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List


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

    h2 {
        margin-top: 1.5rem;
    }

    h3 {
        margin-top: 1rem;
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
        margin-top: 4px;
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
    '<p class="subtitle">'
    'AI-powered resume analysis that helps you understand how well your resume matches a job.'
    '</p>',
    unsafe_allow_html=True
)


# ============================================================
# INPUT SECTION
# ============================================================

col1, col2 = st.columns(2)

with col1:

    st.subheader("📄 Your Resume")

    uploaded_file = st.file_uploader(
        "Upload your resume as a PDF",
        type=["pdf"]
    )


with col2:

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
# ANALYSIS
# ============================================================

if analyze_button:

    if uploaded_file is None:
        st.warning("Please upload your resume PDF first.")

    elif not job_description.strip():
        st.warning("Please paste the job description first.")

    else:

        try:

            # ------------------------------------------------
            # READ PDF
            # ------------------------------------------------

            pdf_reader = pypdf.PdfReader(uploaded_file)

            resume_text = ""

            for page in pdf_reader.pages:
                text = page.extract_text()

                if text:
                    resume_text += text + "\n"


            if not resume_text.strip():
                st.error(
                    "I could not extract text from this PDF. "
                    "Please upload a text-based resume PDF."
                )
                st.stop()


            # ------------------------------------------------
            # GEMINI PROMPT
            # ------------------------------------------------

            prompt = f"""
You are an expert ATS resume evaluator and recruiter.

Analyze the resume against the job description.

IMPORTANT:

1. Do NOT invent experience, skills, tools, education, projects,
   certifications, or achievements that are not supported by the resume.

2. Be realistic and conservative.

3. The category scores must represent how well the resume actually
   satisfies the job description.

4. Analyze the specific requirements in the job description.

5. For every important job requirement, classify it as exactly one of:

   Found
   Partial
   Missing

6. "Found" means the resume clearly contains the requirement.

7. "Partial" means the resume contains related evidence but does not
   completely satisfy the requirement.

8. "Missing" means there is no meaningful evidence in the resume.

9. For experience requirements, carefully compare the required years
   with the candidate's actual demonstrated experience.

10. Do not give a high score simply because the candidate has related
    education.

11. Keep the output concise and useful.

RESUME:

{resume_text}

JOB DESCRIPTION:

{job_description}
"""


            # ------------------------------------------------
            # GEMINI REQUEST
            # ------------------------------------------------

            with st.spinner("Analyzing your resume..."):

                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ResumeAnalysis,
                        temperature=0.2
                    )
                )


            result = response.parsed


            if result is None:
                st.error(
                    "The AI response could not be processed. "
                    "Please try again."
                )
                st.stop()


            # ------------------------------------------------
            # WEIGHTED SCORE
            # ------------------------------------------------

            skills_score = result.category_scores.skills_match
            experience_score = result.category_scores.experience_match
            responsibilities_score = result.category_scores.responsibilities_match
            tools_score = result.category_scores.tools_match
            education_score = result.category_scores.education_match
            evidence_score = result.category_scores.evidence_match


            final_score = round(
                skills_score * 0.25
                + experience_score * 0.20
                + responsibilities_score * 0.20
                + tools_score * 0.15
                + education_score * 0.10
                + evidence_score * 0.10
            )


            # ------------------------------------------------
            # ATS REQUIREMENT COVERAGE
            # ------------------------------------------------

            requirements = result.requirements

            total_requirements = len(requirements)

            found_count = sum(
                1 for item in requirements
                if item.status.lower() == "found"
            )

            partial_count = sum(
                1 for item in requirements
                if item.status.lower() == "partial"
            )

            missing_count = sum(
                1 for item in requirements
                if item.status.lower() == "missing"
            )


            if total_requirements > 0:

                # Partial requirements receive half credit.
                ats_score = round(
                    (
                        found_count
                        + partial_count * 0.5
                    )
                    / total_requirements
                    * 100
                )

            else:

                ats_score = 0


            # ------------------------------------------------
            # MATCH STATUS
            # ------------------------------------------------

            if final_score >= 80:
                match_status = "Strong Match"
                status_message = (
                    "The resume has strong alignment with the target role."
                )

            elif final_score >= 60:
                match_status = "Moderate Match"
                status_message = (
                    "The resume has reasonable alignment but has some gaps."
                )

            else:
                match_status = "Low Match"
                status_message = (
                    "The resume has significant gaps for this role."
                )


            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            st.session_state["analysis_result"] = result
            st.session_state["final_score"] = final_score
            st.session_state["ats_score"] = ats_score
            st.session_state["match_status"] = match_status
            st.session_state["status_message"] = status_message

            st.rerun()


        except Exception as e:

            st.error(
                "Something went wrong while analyzing the resume."
            )

            st.caption(
                "Please try again. If the problem continues, "
                "check the Streamlit app logs."
            )


# ============================================================
# RESULTS
# ============================================================

if "analysis_result" in st.session_state:

    result = st.session_state["analysis_result"]

    final_score = st.session_state["final_score"]
    ats_score = st.session_state["ats_score"]

    match_status = st.session_state["match_status"]
    status_message = st.session_state["status_message"]


    st.divider()

    st.header("📊 Resume Match Analysis")

    st.markdown(
        '<p class="section-description">'
        'AI evaluation across resume-to-job compatibility dimensions.'
        '</p>',
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


    row1 = st.columns(3)

    for column, (label, value) in zip(row1, scores[:3]):

        with column:

            st.metric(
                label,
                f"{value}%"
            )

            st.progress(value / 100)


    row2 = st.columns(3)

    for column, (label, value) in zip(row2, scores[3:]):

        with column:

            st.metric(
                label,
                f"{value}%"
            )

            st.progress(value / 100)


    # ========================================================
    # ATS REQUIREMENT COVERAGE
    # ========================================================

    st.divider()

    st.subheader("🎯 ATS Requirement Coverage")

    st.markdown(
        '<p class="section-description">'
        'How well your resume covers the important requirements in the job description.'
        '</p>',
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
    # REQUIREMENT LIST
    # ========================================================

    for item in requirements:

        status = item.status.lower().strip()


        if status == "found":

            icon = "✅"
            status_class = "found"
            status_text = "Found"

        elif status == "partial":

            icon = "⚠️"
            status_class = "partial"
            status_text = "Partial"

        else:

            icon = "❌"
            status_class = "missing"
            status_text = "Missing"


        st.markdown(
            f"""
            <div class="requirement-card">

                <div class="requirement-title">
                    {icon} {item.requirement}
                    <span class="{status_class}">
                        — {status_text}
                    </span>
                </div>

                <div class="requirement-detail">
                    {item.explanation}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    # ========================================================
    # OVERALL ASSESSMENT
    # ========================================================

    st.subheader("🧠 Overall Assessment")

    st.info(result.overall_assessment)


    # ========================================================
    # EXPERIENCE
    # ========================================================

    st.subheader("💼 Experience Match")

    st.write(result.experience_explanation)


    # ========================================================
    # STRENGTHS + MISSING SKILLS
    # ========================================================

    strength_col, missing_col = st.columns(2)


    with strength_col:

        st.subheader("✓ Resume Strengths")

        for item in result.strengths:

            st.success(item)


    with missing_col:

        st.subheader("⚠ Missing / Weak Skills")

        for item in result.missing_skills:

            st.warning(item)


    # ========================================================
    # WEAK REQUIREMENTS
    # ========================================================

    st.subheader("⚠ Weak Requirements")

    if result.weak_requirements:

        for item in result.weak_requirements:

            st.warning(item)

    else:

        st.success(
            "No major weak requirements were identified."
        )


    # ========================================================
    # IMPROVEMENT SUGGESTIONS
    # ========================================================

    st.subheader("🚀 Improvement Suggestions")

    for item in result.improvement_suggestions:

        st.info(item)


    # ========================================================
    # INTERVIEW PREPARATION
    # ========================================================

    st.subheader("🎤 Interview Preparation")

    for index, question in enumerate(
        result.interview_questions,
        start=1
    ):

        st.write(
            f"**{index}. {question}**"
        )
