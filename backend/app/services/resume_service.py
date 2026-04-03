from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.resume import Resume
from app.utils.helpers import sanitize_filename
from app.utils.logging import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}


class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_resume(
        self,
        user_id: UUID,
        name: str,
        file: UploadFile,
        is_default: bool = False,
    ) -> Resume:
        # Validate file
        if file.filename is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided",
            )

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {ext} not allowed. Allowed: {ALLOWED_EXTENSIONS}",
            )

        # Check file size
        content = await file.read()
        max_bytes = settings.max_resume_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {settings.max_resume_size_mb}MB",
            )

        # Save to disk
        safe_name = sanitize_filename(file.filename)
        user_dir = settings.upload_path / str(user_id) / "resumes"
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_dir / safe_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # If setting as default, unset other defaults
        if is_default:
            await self.db.execute(
                update(Resume)
                .where(Resume.user_id == user_id, Resume.is_default == True)
                .values(is_default=False)
            )

        resume = Resume(
            user_id=user_id,
            name=name,
            file_path=str(file_path),
            file_type=ext.lstrip("."),
            is_default=is_default,
        )
        self.db.add(resume)
        await self.db.flush()

        logger.info("Resume uploaded", resume_id=str(resume.id), user_id=str(user_id))
        return resume

    async def list_resumes(self, user_id: UUID) -> list[Resume]:
        result = await self.db.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_resume(self, resume_id: UUID, user_id: UUID) -> Resume:
        result = await self.db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        resume = result.scalar_one_or_none()
        if resume is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )
        return resume

    async def set_default(self, resume_id: UUID, user_id: UUID) -> Resume:
        resume = await self.get_resume(resume_id, user_id)

        # Unset all defaults for this user
        await self.db.execute(
            update(Resume)
            .where(Resume.user_id == user_id, Resume.is_default == True)
            .values(is_default=False)
        )

        resume.is_default = True
        await self.db.flush()
        return resume

    async def delete_resume(self, resume_id: UUID, user_id: UUID) -> None:
        resume = await self.get_resume(resume_id, user_id)

        # Remove file from disk
        file_path = Path(resume.file_path)
        if file_path.exists():
            file_path.unlink()

        await self.db.delete(resume)
        await self.db.flush()
        logger.info("Resume deleted", resume_id=str(resume_id))
