from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.application import Application, ApplicationLog, ApplicationStatus
from app.models.job import Job
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationStats
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_rate_limit(self, user_id: UUID) -> None:
        """Check if user has exceeded daily application limit."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()

        now = datetime.now(timezone.utc)
        if user.last_application_reset.date() < now.date():
            user.daily_application_count = 0
            user.last_application_reset = now

        if user.daily_application_count >= settings.max_applications_per_day:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily application limit ({settings.max_applications_per_day}) exceeded",
            )

    async def create_application(
        self, user_id: UUID, data: ApplicationCreate
    ) -> Application:
        await self._check_rate_limit(user_id)

        # Verify job exists
        result = await self.db.execute(select(Job).where(Job.id == data.job_id))
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )

        # Check for duplicate application
        result = await self.db.execute(
            select(Application).where(
                Application.user_id == user_id,
                Application.job_id == data.job_id,
                Application.status.notin_([
                    ApplicationStatus.FAILED,
                    ApplicationStatus.CANCELLED,
                ]),
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active application already exists for this job",
            )

        application = Application(
            user_id=user_id,
            job_id=data.job_id,
            resume_id=data.resume_id,
            status=ApplicationStatus.QUEUED,
        )
        self.db.add(application)
        await self.db.flush()

        # Increment daily count
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.daily_application_count += 1

        # Dispatch to Celery
        from app.workers.tasks.application_tasks import process_application
        task = process_application.delay(str(application.id))
        application.celery_task_id = task.id
        await self.db.flush()

        logger.info(
            "Application queued",
            application_id=str(application.id),
            job_id=str(data.job_id),
            task_id=task.id,
        )
        return application

    async def list_user_applications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        status_filter: str | None = None,
    ) -> list[Application]:
        query = select(Application).where(Application.user_id == user_id)
        if status_filter:
            query = query.where(Application.status == status_filter)
        query = query.order_by(Application.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_application(self, application_id: UUID, user_id: UUID) -> Application:
        result = await self.db.execute(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id,
            )
        )
        application = result.scalar_one_or_none()
        if application is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )
        return application

    async def get_application_logs(
        self, application_id: UUID, user_id: UUID
    ) -> list[ApplicationLog]:
        # Verify ownership
        await self.get_application(application_id, user_id)
        result = await self.db.execute(
            select(ApplicationLog)
            .where(ApplicationLog.application_id == application_id)
            .order_by(ApplicationLog.created_at.asc())
        )
        return list(result.scalars().all())

    async def retry_application(self, application_id: UUID, user_id: UUID) -> Application:
        application = await self.get_application(application_id, user_id)
        if application.status not in (ApplicationStatus.FAILED, ApplicationStatus.CAPTCHA_REQUIRED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only retry failed or captcha-blocked applications",
            )
        if application.retry_count >= application.max_retries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum retries exceeded",
            )

        application.status = ApplicationStatus.RETRYING
        application.retry_count += 1
        application.error_message = None
        await self.db.flush()

        from app.workers.tasks.application_tasks import process_application
        task = process_application.delay(str(application.id))
        application.celery_task_id = task.id
        await self.db.flush()

        logger.info("Application retry queued", application_id=str(application_id))
        return application

    async def cancel_application(self, application_id: UUID, user_id: UUID) -> Application:
        application = await self.get_application(application_id, user_id)
        if application.status in (ApplicationStatus.SUBMITTED, ApplicationStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel application in {application.status} status",
            )

        application.status = ApplicationStatus.CANCELLED
        await self.db.flush()
        logger.info("Application cancelled", application_id=str(application_id))
        return application

    async def get_stats(self, user_id: UUID) -> ApplicationStats:
        result = await self.db.execute(
            select(Application.status, func.count(Application.id))
            .where(Application.user_id == user_id)
            .group_by(Application.status)
        )
        counts: dict[str, int] = {}
        total = 0
        for row_status, count in result.all():
            counts[row_status] = count
            total += count

        return ApplicationStats(
            total=total,
            queued=counts.get(ApplicationStatus.QUEUED, 0),
            in_progress=counts.get(ApplicationStatus.IN_PROGRESS, 0),
            submitted=counts.get(ApplicationStatus.SUBMITTED, 0),
            failed=counts.get(ApplicationStatus.FAILED, 0),
            captcha_required=counts.get(ApplicationStatus.CAPTCHA_REQUIRED, 0),
        )
