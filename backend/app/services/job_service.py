from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.detector import detect_platform
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreate
from app.utils.logging import get_logger

logger = get_logger(__name__)


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(self, data: JobCreate) -> Job:
        platform = data.platform or detect_platform(data.url)
        job = Job(
            url=data.url,
            title=data.title,
            company=data.company,
            location=data.location,
            description=data.description,
            platform=platform,
            status=JobStatus.DETECTED if platform.value != "unknown" else JobStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        logger.info("Job created", job_id=str(job.id), platform=platform.value, url=data.url)
        return job

    async def create_jobs_bulk(self, urls: list[str]) -> list[Job]:
        jobs = []
        for url in urls:
            platform = detect_platform(url)
            job = Job(
                url=url,
                platform=platform,
                status=JobStatus.DETECTED if platform.value != "unknown" else JobStatus.PENDING,
            )
            self.db.add(job)
            jobs.append(job)

        await self.db.flush()
        for job in jobs:
            await self.db.refresh(job)
        logger.info("Bulk jobs created", count=len(jobs))
        return jobs

    async def list_jobs(self, skip: int = 0, limit: int = 50) -> list[Job]:
        result = await self.db.execute(
            select(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_job(self, job_id: UUID) -> Job:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return job

    async def delete_job(self, job_id: UUID) -> None:
        job = await self.get_job(job_id)
        await self.db.delete(job)
        await self.db.flush()
        logger.info("Job deleted", job_id=str(job_id))
