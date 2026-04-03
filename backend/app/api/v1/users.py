from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.resume import UserProfileCreate, UserProfileUpdate, UserProfileResponse
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update current user information."""
    service = UserService(db)
    user = await service.update_user(current_user.id, user_data)
    return UserResponse.model_validate(user)


@router.get("/me/profile", response_model=UserProfileResponse | None)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse | None:
    """Get user profile with autofill data."""
    service = UserService(db)
    profile = await service.get_profile(current_user.id)
    if profile is None:
        return None
    return UserProfileResponse.model_validate(profile)


@router.put("/me/profile", response_model=UserProfileResponse)
async def upsert_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Create or update user profile."""
    service = UserService(db)
    profile = await service.upsert_profile(current_user.id, profile_data)
    return UserProfileResponse.model_validate(profile)
