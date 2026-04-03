from __future__ import annotations

from typing import Any

from celery import shared_task

from app.utils.logging import get_logger

logger = get_logger(__name__)


def generate_custom_answers(
    job_description: str,
    user_profile: Any | None = None,
    resume_data: dict | None = None,
) -> dict:
    """Generate AI-customized answers for application questions.

    This is called synchronously within the application task.
    For heavy AI workloads, use the async Celery task version.
    """
    from app.services.ai_service import AIService

    service = AIService()
    return service.generate_answers(
        job_description=job_description,
        user_profile=user_profile,
        resume_data=resume_data,
    )


@shared_task(
    name="app.workers.tasks.ai_tasks.tailor_resume",
    queue="ai",
    max_retries=2,
    default_retry_delay=30,
)
def tailor_resume(
    resume_text: str,
    job_description: str,
    user_id: str,
) -> dict:
    """Generate tailored resume bullet points for a specific job."""
    from app.services.ai_service import AIService

    service = AIService()
    try:
        tailored = service.tailor_resume_bullets(
            resume_text=resume_text,
            job_description=job_description,
        )
        logger.info("Resume tailored", user_id=user_id)
        return {"status": "success", "tailored_bullets": tailored}
    except Exception as exc:
        logger.error("Resume tailoring failed", user_id=user_id, error=str(exc))
        return {"status": "error", "message": str(exc)}
