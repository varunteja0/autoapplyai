from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
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


@shared_task(
    name="app.workers.tasks.application_tasks.auto_apply_all_pending",
    queue="applications",
)
def auto_apply_all_pending() -> dict:
    """Automatically create and process applications for all ready jobs.

    This is the core scheduler that drives 10K+ daily applications.
    It finds all READY jobs that don't have active applications for each user
    and queues them for processing.
    """
    from app.models.application import Application, ApplicationStatus
    from app.models.job import Job, JobStatus
    from app.models.user import User
    from app.models.resume import Resume

    db = _get_sync_session()
    try:
        # Get all active users
        users = db.execute(
            select(User).where(User.is_active == True)
        ).scalars().all()

        total_queued = 0

        for user in users:
            # Check daily limit
            now = datetime.now(timezone.utc)
            if user.last_application_reset.date() < now.date():
                user.daily_application_count = 0
                user.last_application_reset = now
                db.commit()

            remaining = settings.max_applications_per_day - user.daily_application_count
            if remaining <= 0:
                continue

            # Get user's default resume
            default_resume = db.execute(
                select(Resume).where(
                    Resume.user_id == user.id,
                    Resume.is_default == True,
                )
            ).scalar_one_or_none()

            # Get ready jobs without active applications for this user
            active_app_job_ids = db.execute(
                select(Application.job_id).where(
                    Application.user_id == user.id,
                    Application.status.notin_([
                        ApplicationStatus.FAILED,
                        ApplicationStatus.CANCELLED,
                    ]),
                )
            ).scalars().all()

            jobs_query = select(Job).where(
                Job.status.in_([JobStatus.READY, JobStatus.DETECTED]),
            )
            if active_app_job_ids:
                jobs_query = jobs_query.where(Job.id.notin_(active_app_job_ids))
            jobs_query = jobs_query.limit(remaining)

            jobs = db.execute(jobs_query).scalars().all()

            for job in jobs:
                application = Application(
                    user_id=user.id,
                    job_id=job.id,
                    resume_id=default_resume.id if default_resume else None,
                    status=ApplicationStatus.QUEUED,
                )
                db.add(application)
                db.flush()

                user.daily_application_count += 1

                # Queue for processing
                task = process_application.delay(str(application.id))
                application.celery_task_id = task.id
                total_queued += 1

            db.commit()

        logger.info("Auto-apply completed", total_queued=total_queued)
        return {"status": "success", "queued": total_queued}

    except Exception as exc:
        logger.error("Auto-apply failed", error=str(exc))
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()


@shared_task(
    name="app.workers.tasks.application_tasks.reset_daily_counters",
    queue="applications",
)
def reset_daily_counters() -> dict:
    """Reset daily application counters for all users at midnight."""
    from app.models.user import User

    db = _get_sync_session()
    try:
        result = db.execute(
            update(User).values(
                daily_application_count=0,
                last_application_reset=datetime.now(timezone.utc),
            )
        )
        count = result.rowcount
        db.commit()
        logger.info("Daily counters reset", users_reset=count)
        return {"reset": count}
    finally:
        db.close()


@shared_task(
    name="app.workers.tasks.application_tasks.bulk_apply",
    queue="applications",
)
def bulk_apply(user_id: str, job_ids: list[str], resume_id: str | None = None) -> dict:
    """Bulk-create applications for a list of jobs and queue them all."""
    from app.models.application import Application, ApplicationStatus
    from app.models.job import Job
    from app.models.user import User

    db = _get_sync_session()
    try:
        user_uuid = UUID(user_id)
        user = db.execute(select(User).where(User.id == user_uuid)).scalar_one()

        now = datetime.now(timezone.utc)
        if user.last_application_reset.date() < now.date():
            user.daily_application_count = 0
            user.last_application_reset = now

        queued = 0
        skipped = 0
        resume_uuid = UUID(resume_id) if resume_id else None

        for jid in job_ids:
            if user.daily_application_count >= settings.max_applications_per_day:
                skipped += len(job_ids) - queued - skipped
                break

            job_uuid = UUID(jid)

            # Check for existing active application
            existing = db.execute(
                select(Application).where(
                    Application.user_id == user_uuid,
                    Application.job_id == job_uuid,
                    Application.status.notin_([
                        ApplicationStatus.FAILED,
                        ApplicationStatus.CANCELLED,
                    ]),
                )
            ).scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            application = Application(
                user_id=user_uuid,
                job_id=job_uuid,
                resume_id=resume_uuid,
                status=ApplicationStatus.QUEUED,
            )
            db.add(application)
            db.flush()

            user.daily_application_count += 1
            task = process_application.delay(str(application.id))
            application.celery_task_id = task.id
            queued += 1

        db.commit()
        logger.info("Bulk apply completed", queued=queued, skipped=skipped)
        return {"status": "success", "queued": queued, "skipped": skipped}

    except Exception as exc:
        logger.error("Bulk apply failed", error=str(exc))
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()
