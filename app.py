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
# CUSTOM UI
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1150px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .stApp {
        background-color: #f8fafc;
    }

    .brand {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -1px;
        color: #111827;
        margin-bottom: 0.2rem;
    }

    .tagline {
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    .input-title {
        font-size: 1rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.25rem;
    }

    .input-subtitle {
        color: #64748b;
        font-size: 0.85rem;
        margin-bottom: 0.7rem;
    }

    .stButton > button {
        border-radius: 10px;
        min-height: 3rem;
        font-weight: 700;
        font-size: 1rem;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 0 3px 12px rgba(15, 23, 42, 0.04);
    }

    [data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }

    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e2e8f0;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# AI RESPONSE STRUCTURE
# ============================================================

class CategoryScores(BaseModel):

    skills_match: int = Field(
        description="Skills match score from 0 to 100"
    )

    experience_match: int = Field(
        description="Experience match score from 0 to 100"
    )

    responsibilities_match: int = Field(
        description="Responsibilities match score from 0 to 100"
    )

    tools_match: int = Field(
        description="Tools and technologies match score from 0 to 100"
    )

    education_match: int = Field(
        description="Education match score from 0 to 100"
    )

    evidence_match: int = Field(
        description="Evidence and project match score from 0 to 100"
    )


class ResumeAnalysis(BaseModel):

    category_scores: CategoryScores = Field(
        description="Six category scores used to calculate the final match score"
    )

    overall_assessment: str = Field(
        description="Short professional overall assessment"
    )

    strengths: List[str] = Field(
        description="Important strengths of the candidate for this job"
    )

    missing_skills: List[str] = Field(
        description="Missing or weak skills compared with the job"
    )

    experience_explanation: str = Field(
        description="Explanation of how candidate experience matches the job"
    )

    weak_requirements: List[str] = Field(
        description="Job requirements that are not clearly demonstrated"
    )

    improvement_suggestions: List[str] = Field(
        description="Specific suggestions to improve the resume for this job"
    )

    interview_questions: List[str] = Field(
        description="Exactly five relevant interview questions"
    )


# ============================================================
# GEMINI API
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
# INPUT SECTION
# ============================================================

resume_col, jd_col = st.columns(2, gap="large")


with resume_col:

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
        "Resume PDF",
        type=["pdf"],
        label_visibility="collapsed"
    )


with jd_col:

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

analyze_button = st.button(
    "✨ Analyze Resume",
    type="primary",
    use_container_width=True
)


# ============================================================
# AI ANALYSIS
# ============================================================

if analyze_button:

    if resume_file is None:

        st.error("Please upload your resume PDF.")
        st.stop()


    if len(job_description.strip()) < 50:

        st.error(
            "Please paste a complete job description "
            "(at least 50 characters)."
        )
        st.stop()


    try:

        with st.spinner("Analyzing your resume with AI..."):

            # ------------------------------------------------
            # Extract PDF text
            # ------------------------------------------------

            reader = PdfReader(resume_file)

            resume_text = ""

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:

                    resume_text += page_text + "\n"


            if not resume_text.strip():

                st.error(
                    "Could not extract readable text from this PDF."
                )
                st.stop()


            # ------------------------------------------------
            # AI PROMPT
            # ------------------------------------------------

            prompt = f"""
You are an experienced technical recruiter and resume analyst.

Your task is to evaluate the candidate's resume against the target
job description using evidence from the resume.

========================
CANDIDATE RESUME
========================

{resume_text}

========================
TARGET JOB DESCRIPTION
========================

{job_description}

========================
SCORING FRAMEWORK
========================

Evaluate these six categories independently.

1. SKILLS MATCH
Weight: 25%

Compare required skills with skills clearly demonstrated in the resume.

2. EXPERIENCE MATCH
Weight: 20%

Compare years, seniority, industry and type of experience.

3. RESPONSIBILITIES MATCH
Weight: 20%

Compare the candidate's actual responsibilities with the job responsibilities.

4. TOOLS & TECHNOLOGIES
Weight: 15%

Compare software, platforms, programming languages, databases,
cloud technologies and other tools.

5. EDUCATION
Weight: 10%

Compare degree, academic background and relevant education.

6. EVIDENCE / PROJECTS
Weight: 10%

Look for projects, measurable achievements and concrete evidence
supporting the candidate's claims.

========================
SCORING RULES
========================

Give every category a score from 0 to 100.

Use evidence from the resume.

Do NOT give a high score just because a keyword appears.

Do NOT invent skills, experience, projects or qualifications.

If a requirement is only weakly implied, score it conservatively.

If the resume does not provide evidence, do not assume the candidate
has the skill.

The final score will be calculated automatically using the weights.

Also provide:

- Overall assessment
- Resume strengths
- Missing or weak skills
- Experience explanation
- Weak requirements
- Specific improvement suggestions
- Exactly five interview questions

Keep everything professional, realistic and useful to a job seeker.
"""


            # ------------------------------------------------
            # GEMINI REQUEST
            # ------------------------------------------------

            response = client.models.generate_content(

                model="gemini-3.6-flash",

                contents=prompt,

                config=types.GenerateContentConfig(

                    response_mime_type="application/json",

                    response_schema=ResumeAnalysis,

                    temperature=0.2
                )
            )


            # ------------------------------------------------
            # PARSED RESULT
            # ------------------------------------------------

            result = response.parsed

            if result is None:

                st.error(
                    "The AI returned an unexpected response. "
                    "Please try again."
                )

                st.stop()


            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            st.session_state["analysis_result"] = result


    except Exception as e:

        st.error(
            "Something went wrong while analyzing the resume."
        )

        st.caption(
            "Please try again. If the problem continues, check the "
            "Streamlit app logs."
        )

        st.stop()


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "analysis_result" in st.session_state:

    result = st.session_state["analysis_result"]

    scores = result.category_scores


    # ========================================================
    # SAFE CATEGORY SCORES
    # ========================================================

    skills_score = max(0, min(int(scores.skills_match), 100))

    experience_score = max(
        0,
        min(int(scores.experience_match), 100)
    )

    responsibilities_score = max(
        0,
        min(int(scores.responsibilities_match), 100)
    )

    tools_score = max(
        0,
        min(int(scores.tools_match), 100)
    )

    education_score = max(
        0,
        min(int(scores.education_match), 100)
    )

    evidence_score = max(
        0,
        min(int(scores.evidence_match), 100)
    )


    # ========================================================
    # WEIGHTED FINAL SCORE
    # ========================================================

    final_score = round(
        (
            skills_score * 0.25
            + experience_score * 0.20
            + responsibilities_score * 0.20
            + tools_score * 0.15
            + education_score * 0.10
            + evidence_score * 0.10
        )
    )


    # ========================================================
    # MATCH STATUS
    # ========================================================

    if final_score >= 80:

        status = "Strong Match"

    elif final_score >= 60:

        status = "Moderate Match"

    else:

        status = "Low Match"


    # ========================================================
    # RESULTS HEADER
    # ========================================================

    st.divider()

    st.markdown("## 📊 Resume Match Analysis")

    st.caption(
        "AI evaluation across six resume-to-job compatibility dimensions."
    )


    # ========================================================
    # MAIN SCORE
    # ========================================================

    score_col, status_col = st.columns(2, gap="large")


    with score_col:

        st.metric(
            "Overall Match Score",
            f"{final_score}%"
        )

        st.progress(
            final_score / 100,
            text=f"Overall compatibility: {final_score}%"
        )


    with status_col:

        st.metric(
            "Candidate Fit",
            status
        )

        if final_score >= 80:

            st.success(
                "The resume shows strong alignment with this job."
            )

        elif final_score >= 60:

            st.warning(
                "The resume has reasonable alignment but has some gaps."
            )

        else:

            st.error(
                "The resume has significant gaps for this position."
            )


    # ========================================================
    # CATEGORY BREAKDOWN
    # ========================================================

    st.markdown("### 📈 Match Breakdown")

    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "Skills",
            f"{skills_score}%"
        )

        st.progress(skills_score / 100)


    with col2:

        st.metric(
            "Experience",
            f"{experience_score}%"
        )

        st.progress(experience_score / 100)


    with col3:

        st.metric(
            "Responsibilities",
            f"{responsibilities_score}%"
        )

        st.progress(responsibilities_score / 100)


    col4, col5, col6 = st.columns(3)


    with col4:

        st.metric(
            "Tools & Technology",
            f"{tools_score}%"
        )

        st.progress(tools_score / 100)


    with col5:

        st.metric(
            "Education",
            f"{education_score}%"
        )

        st.progress(education_score / 100)


    with col6:

        st.metric(
            "Evidence / Projects",
            f"{evidence_score}%"
        )

        st.progress(evidence_score / 100)


    # ========================================================
    # OVERALL ASSESSMENT
    # ========================================================

    st.markdown("### 🧠 Overall Assessment")

    st.info(result.overall_assessment)


    # ========================================================
    # EXPERIENCE
    # ========================================================

    st.markdown("### 💼 Experience Match")

    st.write(result.experience_explanation)


    # ========================================================
    # STRENGTHS + MISSING SKILLS
    # ========================================================

    strengths_col, missing_col = st.columns(
        2,
        gap="large"
    )


    with strengths_col:

        st.markdown("### ✓ Resume Strengths")

        if result.strengths:

            for item in result.strengths:

                st.success(item)

        else:

            st.write(
                "No specific strengths were identified."
            )


    with missing_col:

        st.markdown("### ⚠ Missing / Weak Skills")

        if result.missing_skills:

            for item in result.missing_skills:

                st.warning(item)

        else:

            st.success(
                "No major skill gaps identified."
            )


    # ========================================================
    # WEAK REQUIREMENTS
    # ========================================================

    st.markdown("### 🎯 Weak Requirements")

    if result.weak_requirements:

        for item in result.weak_requirements:

            st.warning(item)

    else:

        st.success(
            "The resume demonstrates the major requirements."
        )


    # ========================================================
    # IMPROVEMENT SUGGESTIONS
    # ========================================================

    st.markdown("### 💡 Improvement Suggestions")

    if result.improvement_suggestions:

        for number, item in enumerate(
            result.improvement_suggestions,
            start=1
        ):

            st.info(
                f"**{number}.** {item}"
            )

    else:

        st.write(
            "No additional suggestions were generated."
        )


    # ========================================================
    # INTERVIEW QUESTIONS
    # ========================================================

    st.markdown("### 🎤 Interview Preparation")

    st.caption(
        "Questions generated specifically from the job requirements "
        "and candidate profile."
    )


    questions = result.interview_questions[:5]


    if questions:

        for number, question in enumerate(
            questions,
            start=1
        ):

            with st.expander(
                f"Question {number}"
            ):

                st.write(question)

    else:

        st.write(
            "No interview questions were generated."
        )


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
