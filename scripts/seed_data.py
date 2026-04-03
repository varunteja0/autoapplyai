"""Seed script to create test data for development."""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security import hash_password
from app.database import Base
from app.models.user import User
from app.models.job import Job, JobPlatform, JobStatus
from app.models.resume import UserProfile

engine = create_async_engine(settings.database_url)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    async with session_factory() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.email == "admin@autoapplyai.com"))
        if result.scalar_one_or_none():
            print("Seed data already exists. Skipping.")
            return

        # Create admin user
        admin = User(
            email="admin@autoapplyai.com",
            hashed_password=hash_password("admin123456"),
            full_name="Admin User",
            is_superuser=True,
            is_verified=True,
        )
        db.add(admin)
        await db.flush()

        # Create admin profile
        profile = UserProfile(
            user_id=admin.id,
            phone="+1-555-0100",
            address_line1="123 Tech Street",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            country="United States",
            linkedin_url="https://linkedin.com/in/admin",
            github_url="https://github.com/admin",
            years_of_experience=10,
            current_title="Senior Software Engineer",
            current_company="TechCorp",
            work_authorization="US Citizen",
            requires_sponsorship=False,
            skills=["Python", "JavaScript", "React", "AWS", "PostgreSQL"],
            salary_expectation="$180,000 - $220,000",
            stored_answers={
                "Why are you interested in this role?": "I am passionate about building scalable systems and this role aligns perfectly with my expertise.",
                "How did you hear about us?": "LinkedIn",
            },
        )
        db.add(profile)

        # Create sample jobs
        sample_jobs = [
            Job(
                url="https://company.wd5.myworkdayjobs.com/en-US/careers/job/Senior-Engineer_12345",
                title="Senior Software Engineer",
                company="TechCorp Inc",
                location="San Francisco, CA",
                platform=JobPlatform.WORKDAY,
                status=JobStatus.READY,
            ),
            Job(
                url="https://boards.greenhouse.io/startup/jobs/67890",
                title="Full Stack Developer",
                company="StartupXYZ",
                location="New York, NY (Remote)",
                platform=JobPlatform.GREENHOUSE,
                status=JobStatus.READY,
            ),
            Job(
                url="https://jobs.lever.co/techfirm/abcdef",
                title="Backend Engineer",
                company="TechFirm",
                location="Austin, TX",
                platform=JobPlatform.LEVER,
                status=JobStatus.DETECTED,
            ),
        ]
        for job in sample_jobs:
            db.add(job)

        await db.commit()
        print(f"Seed data created. Admin user: admin@autoapplyai.com / admin123456")


if __name__ == "__main__":
    asyncio.run(seed())
