from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.resume import ResumeCreate, ResumeResponse
from app.services.resume_service import ResumeService

router = APIRouter()


@router.post("/", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    name: str,
    is_default: bool = False,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    """Upload a new resume file."""
    service = ResumeService(db)
    resume = await service.upload_resume(
        user_id=current_user.id,
        name=name,
        file=file,
        is_default=is_default,
    )
    return ResumeResponse.model_validate(resume)


@router.get("/", response_model=list[ResumeResponse])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ResumeResponse]:
    """List all resumes for the current user."""
    service = ResumeService(db)
    resumes = await service.list_resumes(current_user.id)
    return [ResumeResponse.model_validate(r) for r in resumes]


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    """Get a specific resume."""
    service = ResumeService(db)
    resume = await service.get_resume(resume_id, current_user.id)
    return ResumeResponse.model_validate(resume)


@router.patch("/{resume_id}/default", response_model=ResumeResponse)
async def set_default_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    """Set a resume as the default."""
    service = ResumeService(db)
    resume = await service.set_default(resume_id, current_user.id)
    return ResumeResponse.model_validate(resume)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a resume."""
    service = ResumeService(db)
    await service.delete_resume(resume_id, current_user.id)
