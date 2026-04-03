from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse, JobBulkCreate, JobUpdate
from app.services.job_service import JobService

router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Add a job URL for processing. Platform will be auto-detected."""
    service = JobService(db)
    job = await service.create_job(job_data)
    return JobResponse.model_validate(job)


@router.post("/bulk", response_model=list[JobResponse], status_code=status.HTTP_201_CREATED)
async def create_jobs_bulk(
    bulk_data: JobBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    """Add multiple job URLs at once."""
    service = JobService(db)
    jobs = await service.create_jobs_bulk(bulk_data.urls)
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    """List all ingested jobs."""
    service = JobService(db)
    jobs = await service.list_jobs(skip=skip, limit=limit)
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Get a specific job by ID."""
    service = JobService(db)
    job = await service.get_job(job_id)
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a job."""
    service = JobService(db)
    await service.delete_job(job_id)
