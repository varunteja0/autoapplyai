from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.utils.logging import get_logger

logger = get_logger(__name__)


def _get_sync_session() -> Session:
    """Create a synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@shared_task(
    bind=True,
    name="app.workers.tasks.application_tasks.process_application",
    max_retries=3,
    default_retry_delay=120,
    queue="applications",
)
def process_application(self, application_id: str) -> dict:
    """Main task: process a job application through the automation pipeline."""
    from app.models.application import Application, ApplicationLog, ApplicationStatus
    from app.models.job import Job
    from app.models.resume import Resume, UserProfile
    from app.models.user import User

    db = _get_sync_session()
    try:
        app_uuid = UUID(application_id)
        application = db.execute(
            select(Application).where(Application.id == app_uuid)
        ).scalar_one_or_none()

        if application is None:
            logger.error("Application not found", application_id=application_id)
            return {"status": "error", "message": "Application not found"}

        # Update status
        application.status = ApplicationStatus.IN_PROGRESS
        db.commit()

        _add_log(db, app_uuid, "info", "Application processing started")

        # Load related data
        job = db.execute(select(Job).where(Job.id == application.job_id)).scalar_one()
        user = db.execute(select(User).where(User.id == application.user_id)).scalar_one()
        profile = db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        ).scalar_one_or_none()

        resume = None
        if application.resume_id:
            resume = db.execute(
                select(Resume).where(Resume.id == application.resume_id)
            ).scalar_one_or_none()

        _add_log(db, app_uuid, "info", f"Platform detected: {job.platform.value}")

        # Run AI customization if needed
        from app.workers.tasks.ai_tasks import generate_custom_answers
        custom_answers = generate_custom_answers(
            job_description=job.description or "",
            user_profile=profile,
            resume_data=resume.parsed_data if resume else None,
        )
        application.custom_answers = custom_answers
        db.commit()

        _add_log(db, app_uuid, "info", "AI customization complete")

        # Run the actual automation
        from app.automation.detector import get_platform_bot
        bot_class = get_platform_bot(job.platform)

        bot = bot_class()
        try:
            result = bot.apply(
                url=job.url,
                user=user,
                profile=profile,
                resume=resume,
                custom_answers=custom_answers,
                application_id=str(app_uuid),
            )

            if result.get("captcha_detected"):
                application.status = ApplicationStatus.CAPTCHA_REQUIRED
                _add_log(db, app_uuid, "warning", "CAPTCHA detected - manual intervention required")
                db.commit()
                return {"status": "captcha_required", "application_id": application_id}

            application.status = ApplicationStatus.SUBMITTED
            application.submitted_at = datetime.now(timezone.utc)
            _add_log(db, app_uuid, "info", "Application submitted successfully")
            db.commit()

            logger.info("Application submitted", application_id=application_id)
            return {"status": "submitted", "application_id": application_id}

        except Exception as bot_error:
            error_msg = str(bot_error)
            logger.error(
                "Bot automation failed",
                application_id=application_id,
                error=error_msg,
            )
            _add_log(db, app_uuid, "error", f"Automation failed: {error_msg}")

            if application.retry_count < application.max_retries:
                application.status = ApplicationStatus.RETRYING
                application.retry_count += 1
                db.commit()
                raise self.retry(exc=bot_error)
            else:
                application.status = ApplicationStatus.FAILED
                application.error_message = error_msg
                db.commit()
                return {"status": "failed", "error": error_msg}

    except Exception as exc:
        logger.error("Task failed", application_id=application_id, error=str(exc))
        try:
            if application:
                application.status = ApplicationStatus.FAILED
                application.error_message = str(exc)
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


@shared_task(
    name="app.workers.tasks.application_tasks.cleanup_stale_applications",
    queue="applications",
)
def cleanup_stale_applications() -> dict:
    """Clean up applications stuck in IN_PROGRESS for more than 1 hour."""
    from app.models.application import Application, ApplicationStatus

    db = _get_sync_session()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        result = db.execute(
            update(Application)
            .where(
                Application.status == ApplicationStatus.IN_PROGRESS,
                Application.updated_at < cutoff,
            )
            .values(
                status=ApplicationStatus.FAILED,
                error_message="Timed out - application processing took too long",
            )
        )
        count = result.rowcount
        db.commit()
        logger.info("Cleaned up stale applications", count=count)
        return {"cleaned": count}
    finally:
        db.close()


def _add_log(
    db: Session,
    application_id: UUID,
    level: str,
    message: str,
    details: dict | None = None,
) -> None:
    """Add a log entry for an application."""
    from app.models.application import ApplicationLog

    log = ApplicationLog(
        application_id=application_id,
        level=level,
        message=message,
        details=details or {},
    )
    db.add(log)
    db.commit()
