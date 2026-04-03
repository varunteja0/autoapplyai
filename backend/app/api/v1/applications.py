from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationLogResponse,
    ApplicationStats,
    BulkApplicationCreate,
)
from app.services.application_service import ApplicationService

router = APIRouter()


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    app_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Queue a new job application for automated processing."""
    service = ApplicationService(db)
    application = await service.create_application(current_user.id, app_data)
    return ApplicationResponse.model_validate(application)


@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED)
async def bulk_apply(
    bulk_data: BulkApplicationCreate,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Queue multiple job applications at once for automated processing.
    Returns immediately — applications are processed asynchronously.
    """
    from app.workers.tasks.application_tasks import bulk_apply as bulk_apply_task
    task = bulk_apply_task.delay(
        str(current_user.id),
        [str(jid) for jid in bulk_data.job_ids],
        str(bulk_data.resume_id) if bulk_data.resume_id else None,
    )
    return {"task_id": task.id, "job_count": len(bulk_data.job_ids), "status": "queued"}


@router.post("/apply-all", status_code=status.HTTP_202_ACCEPTED)
async def apply_to_all_jobs(
    resume_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Apply to all available jobs that don't have active applications.
    Returns immediately — applications are processed asynchronously.
    """
    from sqlalchemy import select
    from app.models.job import Job, JobStatus
    from app.models.application import Application, ApplicationStatus

    # Get job IDs without active applications for this user
    active_app_job_ids_q = select(Application.job_id).where(
        Application.user_id == current_user.id,
        Application.status.notin_([
            ApplicationStatus.FAILED,
            ApplicationStatus.CANCELLED,
        ]),
    )
    active_job_ids = (await db.execute(active_app_job_ids_q)).scalars().all()

    jobs_query = select(Job.id).where(
        Job.status.in_([JobStatus.READY, JobStatus.DETECTED]),
    )
    if active_job_ids:
        jobs_query = jobs_query.where(Job.id.notin_(active_job_ids))

    job_ids = (await db.execute(jobs_query)).scalars().all()

    if not job_ids:
        return {"task_id": None, "job_count": 0, "status": "no_jobs_available"}

    from app.workers.tasks.application_tasks import bulk_apply as bulk_apply_task
    task = bulk_apply_task.delay(
        str(current_user.id),
        [str(jid) for jid in job_ids],
        str(resume_id) if resume_id else None,
    )
    return {"task_id": task.id, "job_count": len(job_ids), "status": "queued"}


@router.get("/", response_model=list[ApplicationResponse])
async def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationResponse]:
    """List user's applications with optional status filter."""
    service = ApplicationService(db)
    apps = await service.list_user_applications(
        current_user.id, skip=skip, limit=limit, status_filter=status_filter
    )
    return [ApplicationResponse.model_validate(a) for a in apps]


@router.get("/stats", response_model=ApplicationStats)
async def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationStats:
    """Get application statistics for the current user."""
    service = ApplicationService(db)
    return await service.get_stats(current_user.id)


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Get a specific application."""
    service = ApplicationService(db)
    application = await service.get_application(application_id, current_user.id)
    return ApplicationResponse.model_validate(application)


@router.get("/{application_id}/logs", response_model=list[ApplicationLogResponse])
async def get_application_logs(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationLogResponse]:
    """Get logs for a specific application."""
    service = ApplicationService(db)
    logs = await service.get_application_logs(application_id, current_user.id)
    return [ApplicationLogResponse.model_validate(log) for log in logs]


@router.post("/{application_id}/retry", response_model=ApplicationResponse)
async def retry_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Retry a failed application."""
    service = ApplicationService(db)
    application = await service.retry_application(application_id, current_user.id)
    return ApplicationResponse.model_validate(application)


@router.post("/{application_id}/cancel", response_model=ApplicationResponse)
async def cancel_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Cancel a queued or in-progress application."""
    service = ApplicationService(db)
    application = await service.cancel_application(application_id, current_user.id)
    return ApplicationResponse.model_validate(application)
