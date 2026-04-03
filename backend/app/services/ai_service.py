from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AIService:
    """Service for AI-powered resume customization and answer generation."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.model = settings.openai_model

    def generate_answers(
        self,
        job_description: str,
        user_profile: Any | None = None,
        resume_data: dict | None = None,
    ) -> dict:
        """Generate custom answers to common application questions."""
        if not self.client or not job_description:
            return {}

        profile_context = ""
        if user_profile:
            profile_context = f"""
User Profile:
- Name: {getattr(user_profile, 'current_title', 'N/A')}
- Experience: {getattr(user_profile, 'years_of_experience', 'N/A')} years
- Skills: {', '.join(getattr(user_profile, 'skills', []) or [])}
- Work Authorization: {getattr(user_profile, 'work_authorization', 'N/A')}
"""

        resume_context = ""
        if resume_data:
            resume_context = f"\nResume Summary: {json.dumps(resume_data, default=str)[:2000]}"

        prompt = f"""You are an expert career coach. Based on the following job description and candidate profile,
generate professional answers for common application questions.

Job Description:
{job_description[:3000]}

{profile_context}
{resume_context}

Generate a JSON object with answers for these common questions:
1. "why_interested" - Why are you interested in this role? (2-3 sentences)
2. "cover_letter_summary" - A brief cover letter summary (3-4 sentences)
3. "salary_expectations" - Professional salary expectation response
4. "start_date" - Professional availability response
5. "work_authorization" - Work authorization status
6. "relevant_experience" - Most relevant experience for this role (2-3 sentences)

Return ONLY valid JSON, no markdown formatting."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000,
            )
            content = response.choices[0].message.content or "{}"
            # Strip markdown code fences if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return json.loads(content)
        except Exception as exc:
            logger.error("AI answer generation failed", error=str(exc))
            return {}

    def tailor_resume_bullets(
        self,
        resume_text: str,
        job_description: str,
    ) -> list[str]:
        """Generate tailored resume bullet points for a specific job."""
        if not self.client:
            return []

        prompt = f"""You are an expert resume writer. Based on the candidate's resume and the target job description,
generate 5-8 tailored resume bullet points that highlight the most relevant experience and skills.

Each bullet should:
- Start with a strong action verb
- Include quantifiable results where possible
- Be directly relevant to the job requirements
- Be concise (1-2 lines each)

Resume:
{resume_text[:3000]}

Job Description:
{job_description[:3000]}

Return ONLY a JSON array of strings, each string being one bullet point. No markdown."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=800,
            )
            content = response.choices[0].message.content or "[]"
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return json.loads(content)
        except Exception as exc:
            logger.error("AI resume tailoring failed", error=str(exc))
            return []
