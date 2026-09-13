import os
import json
import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List


# ============================================================
# PAGE CONFIGURATION
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

    /* Main page */
    .block-container {
        max-width: 1150px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .stApp {
        background-color: #f8fafc;
    }

    /* Brand */
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

    /* Section labels */
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

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        min-height: 3rem;
        font-weight: 700;
        font-size: 1rem;
    }

    /* Metric */
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 3px 12px rgba(15, 23, 42, 0.04);
    }

    /* Expanders */
    [data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }

    /* Footer */
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

class ResumeAnalysis(BaseModel):

    match_score: int = Field(
        description="Overall resume to job match score from 0 to 100"
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

    experience_match: str = Field(
        description="Explanation of how the candidate experience matches the job"
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
# RUN AI ANALYSIS
# ============================================================

if analyze_button:

    # Check resume
    if resume_file is None:

        st.error("Please upload your resume PDF.")

        st.stop()


    # Check job description
    if len(job_description.strip()) < 50:

        st.error(
            "Please paste a complete job description "
            "(at least 50 characters)."
        )

        st.stop()


    try:

        with st.spinner("Analyzing your resume with AI..."):

            # --------------------------------------------
            # Extract resume text
            # --------------------------------------------

            reader = PdfReader(resume_file)

            resume_text = ""

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:
                    resume_text += page_text + "\n"


            if not resume_text.strip():

                st.error(
                    "I could not extract readable text from this PDF. "
                    "Please try another PDF."
                )

                st.stop()


            # --------------------------------------------
            # AI Prompt
            # --------------------------------------------

            prompt = f"""
You are an experienced technical recruiter and resume analyst.

Analyze the candidate's resume against the target job description.

========================
CANDIDATE RESUME
========================

{resume_text}

========================
TARGET JOB DESCRIPTION
========================

{job_description}

========================
ANALYSIS REQUIREMENTS
========================

Provide a realistic and evidence-based analysis.

1. Give an overall match score from 0 to 100.

2. Consider:
   - Technical skills
   - Tools and technologies
   - Work experience
   - Responsibilities
   - Education
   - Projects
   - Evidence of required skills

3. Do not give a high score only because keywords appear.

4. Do not invent experience, skills, projects or qualifications.

5. Clearly identify missing or weak requirements.

6. Explain the experience match realistically.

7. Give practical resume improvement suggestions.

8. Generate exactly 5 interview questions based on the job and the candidate.

Keep the analysis professional, concise and useful for a job seeker.
"""


            # --------------------------------------------
            # Gemini structured response
            # --------------------------------------------

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeAnalysis
                )
            )


            # --------------------------------------------
            # Parse AI result
            # --------------------------------------------

            parsed_result = response.parsed

            if parsed_result is None:

                if not response.text:

                    st.error(
                        "The AI returned an empty response. "
                        "Please try again."
                    )

                    st.stop()

                data = json.loads(response.text)

                result = ResumeAnalysis.model_validate(data)

            else:

                if isinstance(parsed_result, ResumeAnalysis):

                    result = parsed_result

                else:

                    result = ResumeAnalysis.model_validate(
                        parsed_result
                    )


            # --------------------------------------------
            # Store result
            # --------------------------------------------

            st.session_state["analysis_result"] = result


    except json.JSONDecodeError:

        st.error(
            "The AI response could not be processed. "
            "Please try the analysis again."
        )

        st.stop()


    except Exception as e:

        st.error(
            "Something went wrong while analyzing the resume."
        )

        st.caption(
            "Please check your API configuration or try again."
        )

        st.stop()


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "analysis_result" in st.session_state:

    result = st.session_state["analysis_result"]


    # --------------------------------------------------------
    # SAFE SCORE
    # --------------------------------------------------------

    try:

        score = int(result.match_score)

    except Exception:

        score = 0


    score = max(0, min(score, 100))


    # --------------------------------------------------------
    # MATCH STATUS
    # --------------------------------------------------------

    if score >= 80:

        status = "Strong Match"

    elif score >= 60:

        status = "Moderate Match"

    else:

        status = "Low Match"


    st.divider()


    # ========================================================
    # SCORE + ASSESSMENT
    # ========================================================

    score_col, assessment_col = st.columns(
        [1, 2],
        gap="large"
    )


    with score_col:

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


    with assessment_col:

        st.markdown("### Overall Assessment")

        st.info(result.overall_assessment)

        st.progress(
            score / 100,
            text=f"Resume compatibility: {score}%"
        )


    # ========================================================
    # EXPERIENCE MATCH
    # ========================================================

    st.markdown("### 💼 Experience Match")

    st.write(result.experience_match)


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

            st.write("No specific strengths were identified.")


    with missing_col:

        st.markdown("### ⚠ Missing / Weak Skills")

        if result.missing_skills:

            for item in result.missing_skills:

                st.warning(item)

        else:

            st.success("No major skill gaps identified.")


    # ========================================================
    # WEAK REQUIREMENTS
    # ========================================================

    st.markdown("### 🎯 Weak Requirements")

    if result.weak_requirements:

        for item in result.weak_requirements:

            st.warning(item)

    else:

        st.success(
            "The resume demonstrates the major requirements of the job."
        )


    # ========================================================
    # IMPROVEMENT SUGGESTIONS
    # ========================================================

    st.markdown("### 💡 Improvement Suggestions")

    if result.improvement_suggestions:

        for i, item in enumerate(
            result.improvement_suggestions,
            start=1
        ):

            st.info(f"**{i}.** {item}")

    else:

        st.write("No additional suggestions were generated.")


    # ========================================================
    # INTERVIEW PREPARATION
    # ========================================================

    st.markdown("### 🎤 Interview Preparation")

    st.caption(
        "Questions you may want to prepare for based on this job."
    )


    questions = result.interview_questions[:5]


    if questions:

        for i, question in enumerate(
            questions,
            start=1
        ):

            with st.expander(
                f"Question {i}"
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
