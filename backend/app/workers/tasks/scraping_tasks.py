from __future__ import annotations

from celery import shared_task

from app.utils.logging import get_logger

logger = get_logger(__name__)


@shared_task(
    name="app.workers.tasks.scraping_tasks.scrape_job_details",
    queue="scraping",
    max_retries=2,
    default_retry_delay=60,
)
def scrape_job_details(job_id: str) -> dict:
    """Scrape job details from the career portal page."""
    from uuid import UUID
    from sqlalchemy import select
    from app.models.job import Job, JobStatus
    from app.workers.tasks.application_tasks import _get_sync_session
    from app.automation.detector import get_platform_bot

    db = _get_sync_session()
    try:
        job = db.execute(
            select(Job).where(Job.id == UUID(job_id))
        ).scalar_one_or_none()

        if job is None:
            return {"status": "error", "message": "Job not found"}

        bot_class = get_platform_bot(job.platform)
        bot = bot_class()

        details = bot.scrape_job_details(job.url)

        job.title = details.get("title", job.title)
        job.company = details.get("company", job.company)
        job.location = details.get("location", job.location)
        job.description = details.get("description", job.description)
        job.status = JobStatus.READY

        db.commit()
        logger.info("Job details scraped", job_id=job_id)
        return {"status": "success", "job_id": job_id}

    except Exception as exc:
        logger.error("Scraping failed", job_id=job_id, error=str(exc))
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()
