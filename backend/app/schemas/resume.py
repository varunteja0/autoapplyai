from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ResumeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_default: bool = False


class ResumeResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    file_path: str
    file_type: str
    is_default: bool
    parsed_data: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileCreate(BaseModel):
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = "United States"
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    years_of_experience: int | None = None
    current_title: str | None = None
    current_company: str | None = None
    work_authorization: str | None = None
    requires_sponsorship: bool | None = None
    stored_answers: dict | None = None
    skills: list[str] | None = None
    preferred_locations: list[str] | None = None
    salary_expectation: str | None = None


class UserProfileUpdate(UserProfileCreate):
    pass


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    phone: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    country: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    years_of_experience: int | None
    current_title: str | None
    current_company: str | None
    work_authorization: str | None
    requires_sponsorship: bool | None
    stored_answers: dict | None
    skills: list | None
    preferred_locations: list | None
    salary_expectation: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
