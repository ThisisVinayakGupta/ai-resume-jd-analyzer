import os
import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
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
# CUSTOM STYLING
# ============================================================

st.markdown("""
<style>

    /* ---------- GLOBAL ---------- */

    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .stApp {
        background: #f8fafc;
    }

    /* ---------- HEADER ---------- */

    .brand {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -1px;
        color: #111827;
        margin-bottom: 0.25rem;
    }

    .tagline {
        font-size: 1rem;
        color: #64748b;
        margin-bottom: 2rem;
    }

    /* ---------- INPUT CARDS ---------- */

    .input-title {
        font-size: 1rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.4rem;
    }

    .input-subtitle {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 0.8rem;
    }

    /* ---------- ANALYZE BUTTON ---------- */

    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3rem;
        font-weight: 700;
        font-size: 1rem;
    }

    /* ---------- SCORE CARD ---------- */

    .score-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 1.8rem;
        text-align: center;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.05);
    }

    .score-label {
        color: #64748b;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .score-number {
        font-size: 4rem;
        line-height: 1;
        font-weight: 800;
        color: #111827;
        margin: 0.6rem 0;
    }

    .score-status {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 700;
        background: #ecfdf5;
        color: #047857;
    }

    /* ---------- SECTION HEADERS ---------- */

    .section-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #111827;
        margin-top: 1.8rem;
        margin-bottom: 0.8rem;
    }

    .section-description {
        color: #64748b;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }

    /* ---------- RESULT CARDS ---------- */

    .result-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 0.8rem;
        color: #334155;
        line-height: 1.6;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
    }

    .strength-card {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
        color: #166534;
    }

    .warning-card {
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
        color: #92400e;
    }

    .info-card {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
        color: #1e40af;
    }

    /* ---------- FOOTER ---------- */

    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e2e8f0;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# AI RESPONSE STRUCTURE
# ============================================================

class ResumeAnalysis(BaseModel):

    match_score: int = Field(
        description="Overall resume to job match score from 0 to 100"
    )

    overall_assessment: str = Field(
        description="Short overall assessment"
    )

    strengths: List[str] = Field(
        description="Important candidate strengths"
    )

    missing_skills: List[str] = Field(
        description="Missing or weak skills"
    )

    experience_match: str = Field(
        description="Experience match explanation"
    )

    weak_requirements: List[str] = Field(
        description="Requirements not clearly demonstrated"
    )

    improvement_suggestions: List[str] = Field(
        description="Resume improvement suggestions"
    )

    interview_questions: List[str] = Field(
        description="Exactly five interview questions"
    )


# ============================================================
# GEMINI CONNECTION
# ============================================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("Gemini API key is not configured.")
    st.stop()

client = genai.Client(api_key=api_key)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="brand">🚀 ResumeMatch Pro</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="tagline">'
    'AI-powered resume analysis that helps you understand how well your resume matches a job.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# INPUT AREA
# ============================================================

input_col1, input_col2 = st.columns([1, 1], gap="large")


with input_col1:

    st.markdown(
        '<div class="input-title">📄 Your Resume</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="input-subtitle">'
        'Upload your resume as a PDF'
        '</div>',
        unsafe_allow_html=True
    )

    resume_file = st.file_uploader(
        "Upload Resume",
        type=["pdf"],
        label_visibility="collapsed"
    )


with input_col2:

    st.markdown(
        '<div class="input-title">💼 Target Job</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="input-subtitle">'
        'Paste the complete job description'
        '</div>',
        unsafe_allow_html=True
    )

    job_description = st.text_area(
        "Job Description",
        height=180,
        placeholder="Paste the job description here...",
        label_visibility="collapsed"
    )


st.write("")


# ============================================================
# ANALYZE BUTTON
# ============================================================

analyze = st.button(
    "✨ Analyze Resume",
    type="primary",
    use_container_width=True
)


# ============================================================
# ANALYSIS
# ============================================================

if analyze:

    if resume_file is None:

        st.error("Please upload your resume PDF.")

    elif len(job_description.strip()) < 50:

        st.error("Please enter a complete job description.")

    else:

        with st.spinner("Analyzing your resume with AI..."):

            reader = PdfReader(resume_file)

            resume_text = ""

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    resume_text += text + "\n"


            prompt = f"""
Analyze this resume against the job description.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Provide a professional recruitment analysis.

Rules:

- Give a realistic match score from 0 to 100.
- Consider skills, experience, responsibilities, education, tools and evidence.
- Do not rely only on keywords.
- Do not invent information.
- Clearly identify missing or weak requirements.
- Provide exactly 5 interview questions.
"""

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeAnalysis
                )
            )

            result = response.parsed

            # Store result so it survives Streamlit reruns
            st.session_state["analysis_result"] = result


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "analysis_result" in st.session_state:

    result = st.session_state["analysis_result"]

    score = result.match_score


    # --------------------------------------------------------
    # MATCH STATUS
    # --------------------------------------------------------

    if score >= 80:
        status = "Strong Match"
        status_color = "#047857"
        status_background = "#ecfdf5"

    elif score >= 60:
        status = "Moderate Match"
        status_color = "#b45309"
        status_background = "#fffbeb"

    else:
        status = "Low Match"
        status_color = "#b91c1c"
        status_background = "#fef2f2"


    st.divider()


   # --------------------------------------------------------
# SCORE
# --------------------------------------------------------

score_col1, score_col2 = st.columns([1, 2], gap="large")


with score_col1:

    st.markdown("### AI Match Score")

    st.metric(
        label="Resume compatibility",
        value=f"{score}%"
    )

    if score >= 80:
        st.success(f"✓ {status}")
    elif score >= 60:
        st.warning(f"⚠ {status}")
    else:
        st.error(f"✕ {status}")


with score_col2:

    st.markdown("### Overall Assessment")

    st.markdown(
        f"""
        <div class="result-card">
            {result.overall_assessment}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.progress(
        min(max(score, 0), 100) / 100,
        text=f"Resume compatibility: {score}%"
    )

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">💼 Experience Match</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="result-card">
            {result.experience_match}
        </div>
        """,
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # STRENGTHS + MISSING SKILLS
    # --------------------------------------------------------

    col_strengths, col_missing = st.columns(2, gap="large")


    with col_strengths:

        st.markdown(
            '<div class="section-title">✓ Resume Strengths</div>',
            unsafe_allow_html=True
        )

        for item in result.strengths:

            st.markdown(
                f"""
                <div class="strength-card">
                    ✓ {item}
                </div>
                """,
                unsafe_allow_html=True
            )


    with col_missing:

        st.markdown(
            '<div class="section-title">⚠ Missing / Weak Skills</div>',
            unsafe_allow_html=True
        )

        for item in result.missing_skills:

            st.markdown(
                f"""
                <div class="warning-card">
                    ⚠ {item}
                </div>
                """,
                unsafe_allow_html=True
            )


    # --------------------------------------------------------
    # WEAK REQUIREMENTS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">🎯 Weak Requirements</div>',
        unsafe_allow_html=True
    )

    for item in result.weak_requirements:

        st.markdown(
            f"""
            <div class="warning-card">
                {item}
            </div>
            """,
            unsafe_allow_html=True
        )


    # --------------------------------------------------------
    # IMPROVEMENT SUGGESTIONS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">💡 Improvement Suggestions</div>',
        unsafe_allow_html=True
    )

    for item in result.improvement_suggestions:

        st.markdown(
            f"""
            <div class="info-card">
                {item}
            </div>
            """,
            unsafe_allow_html=True
        )


    # --------------------------------------------------------
    # INTERVIEW QUESTIONS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">🎤 Interview Preparation</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-description">'
        'Questions you may want to prepare for based on this job.'
        '</div>',
        unsafe_allow_html=True
    )


    for i, question in enumerate(result.interview_questions, 1):

        with st.expander(f"Question {i}"):

            st.write(question)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        ResumeMatch Pro · AI-powered resume & job matching
    </div>
    """,
    unsafe_allow_html=True
)
