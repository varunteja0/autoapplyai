from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.application import ApplicationStatus


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_id: uuid.UUID | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    error_message: str | None = None


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID | None
    status: ApplicationStatus
    retry_count: int
    max_retries: int
    error_message: str | None
    submitted_at: datetime | None
    celery_task_id: str | None
    custom_answers: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationLogResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    level: str
    message: str
    details: dict | None
    screenshot_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationStats(BaseModel):
    total: int
    queued: int
    in_progress: int
    submitted: int
    failed: int
    captcha_required: int
