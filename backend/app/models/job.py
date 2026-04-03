from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobPlatform(str, enum.Enum):
    WORKDAY = "workday"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    TALEO = "taleo"
    UNKNOWN = "unknown"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    DETECTED = "detected"
    READY = "ready"
    EXPIRED = "expired"
    ERROR = "error"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    platform: Mapped[JobPlatform] = mapped_column(
        Enum(JobPlatform, values_callable=lambda x: [e.value for e in x]),
        default=JobPlatform.UNKNOWN,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        default=JobStatus.PENDING,
    )

    # Platform-specific metadata
    platform_job_id: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    applications: Mapped[list["Application"]] = relationship(  # noqa: F821
        back_populates="job", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Job {self.title} @ {self.company}>"
