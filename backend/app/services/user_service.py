from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.resume import UserProfile
from app.schemas.user import UserUpdate
from app.schemas.resume import UserProfileCreate
from app.utils.logging import get_logger

logger = get_logger(__name__)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        return user

    async def get_profile(self, user_id: UUID) -> UserProfile | None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_profile(self, user_id: UUID, data: UserProfileCreate) -> UserProfile:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        profile_data = data.model_dump(exclude_unset=True)

        if profile is None:
            profile = UserProfile(user_id=user_id, **profile_data)
            self.db.add(profile)
        else:
            for field, value in profile_data.items():
                setattr(profile, field, value)

        await self.db.flush()
        logger.info("Profile updated", user_id=str(user_id))
        return profile
