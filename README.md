# AI Resume & JD Analyzer

An AI-powered web application that analyzes a resume against a job description and provides an intelligent compatibility score, strengths, skill gaps, experience match, and improvement suggestions.

## 🚀 Live Demo

https://resumatchpro.streamlit.app

## 📌 What This Project Does

The application allows users to:

- Upload a resume in PDF format
- Paste a job description
- Analyze the resume using Google Gemini AI
- Generate an AI-based match score
- Identify matching skills
- Identify missing or weak skills
- Analyze experience alignment
- Highlight weak job requirements
- Provide resume improvement suggestions
- Generate interview preparation questions

## 🛠️ Technologies Used

- Python
- Streamlit
- Google Gemini API
- Google GenAI SDK
- PyPDF
- Pydantic

## 🔄 How It Works

1. User uploads a resume PDF.
2. The application extracts the resume text.
3. User enters the target job description.
4. Resume and job description are sent to Gemini AI.
5. Gemini analyzes the candidate's profile against the job requirements.
6. The application displays the results in an easy-to-understand dashboard.

## 📊 Example Analysis

The application provides:

- AI Match Score
- Overall Assessment
- Resume Strengths
- Missing / Weak Skills
- Experience Match
- Weak Requirements
- Improvement Suggestions
- Interview Questions

## 🎯 Project Goal

The goal of this project is to help job seekers understand how well their resume matches a specific job description and identify areas they can improve before applying.

## 🔐 Security

The Gemini API key is stored securely using Streamlit Secrets and is not included in the GitHub repository.

## 👨‍💻 Project Status

Current version: MVP

Future improvements may include:

- ATS keyword analysis
- Resume rewriting
- Multiple resume formats
- Job recommendations
- Downloadable reports
- User accounts
- Premium features
