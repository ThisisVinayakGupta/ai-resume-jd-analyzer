import os

import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List


# -----------------------------
# AI RESPONSE STRUCTURE
# -----------------------------

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


# -----------------------------
# GEMINI CONNECTION
# -----------------------------

api_key = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


# -----------------------------
# PAGE
# -----------------------------

st.set_page_config(
    page_title="AI Resume & JD Analyzer",
    page_icon="📄",
    layout="wide"
)

st.title("📄 AI Resume & JD Analyzer")

st.write(
    "Upload your resume, paste a job description, "
    "and get an AI-powered compatibility analysis."
)


# -----------------------------
# INPUTS
# -----------------------------

resume_file = st.file_uploader(
    "Upload Resume PDF",
    type=["pdf"]
)

job_description = st.text_area(
    "Paste Job Description",
    height=250,
    placeholder="Paste the complete job description here..."
)


# -----------------------------
# ANALYZE
# -----------------------------

if st.button("Analyze Resume", type="primary"):

    if resume_file is None:
        st.error("Please upload a resume PDF.")

    elif len(job_description.strip()) < 50:
        st.error("Please enter a complete job description.")

    else:

        with st.spinner("Analyzing resume with AI..."):

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
- Consider skills, experience, responsibilities,
  education, tools and evidence.
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


        # -----------------------------
        # SCORE
        # -----------------------------

        score = result.match_score

        if score >= 80:
            status = "Strong Match"
        elif score >= 60:
            status = "Moderate Match"
        else:
            status = "Low Match"


        # -----------------------------
        # RESULT
        # -----------------------------

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "AI Match Score",
                f"{score}%"
            )

        with col2:
            st.metric(
                "Assessment",
                status
            )


        st.divider()

        st.subheader("Overall Assessment")

        st.write(result.overall_assessment)


        st.subheader("Resume Strengths")

        for item in result.strengths:
            st.success(item)


        st.subheader("Missing / Weak Skills")

        for item in result.missing_skills:
            st.warning(item)


        st.subheader("Experience Match")

        st.write(result.experience_match)


        st.subheader("Weak Requirements")

        for item in result.weak_requirements:
            st.warning(item)


        st.subheader("Improvement Suggestions")

        for item in result.improvement_suggestions:
            st.info(item)


        st.subheader("Interview Questions")

        for i, question in enumerate(
            result.interview_questions,
            1
        ):
            st.write(f"**{i}.** {question}")
