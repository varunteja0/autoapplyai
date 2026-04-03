from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl

from app.models.job import JobPlatform, JobStatus


class JobCreate(BaseModel):
    url: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    platform: JobPlatform | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    platform: JobPlatform | None = None
    status: JobStatus | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    url: str
    title: str | None
    company: str | None
    location: str | None
    description: str | None
    platform: JobPlatform
    status: JobStatus
    platform_job_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobBulkCreate(BaseModel):
    urls: list[str]
