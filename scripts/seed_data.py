"""Seed script to create test data for development."""
from __future__ import annotations

import asyncio
import random
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security import hash_password
from app.database import Base
from app.models.user import User
from app.models.job import Job, JobPlatform, JobStatus
from app.models.resume import UserProfile

engine = create_async_engine(settings.database_url)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Templates for generating realistic job data
COMPANIES = [
    "Google", "Meta", "Amazon", "Apple", "Microsoft", "Netflix", "Stripe",
    "Airbnb", "Uber", "Lyft", "Spotify", "Slack", "Shopify", "Square",
    "Coinbase", "Dropbox", "Twilio", "Datadog", "Snowflake", "Palantir",
    "Figma", "Notion", "Vercel", "Supabase", "Linear", "Retool", "Airtable",
    "MongoDB", "Elastic", "Cloudflare", "Fastly", "HashiCorp", "GitLab",
]

TITLES = [
    "Software Engineer", "Senior Software Engineer", "Staff Engineer",
    "Backend Engineer", "Frontend Engineer", "Full Stack Developer",
    "DevOps Engineer", "SRE", "Data Engineer", "ML Engineer",
    "Platform Engineer", "Infrastructure Engineer", "Security Engineer",
    "Mobile Engineer", "QA Engineer", "Engineering Manager",
]

LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
    "Remote", "Boston, MA", "Chicago, IL", "Denver, CO", "Portland, OR",
    "Los Angeles, CA", "Miami, FL", "Atlanta, GA",
]

PLATFORM_URLS = {
    JobPlatform.GREENHOUSE: "https://boards.greenhouse.io/{company}/jobs/{jid}",
    JobPlatform.LEVER: "https://jobs.lever.co/{company}/{jid}",
    JobPlatform.WORKDAY: "https://{company}.wd5.myworkdayjobs.com/en-US/careers/job/{jid}",
    JobPlatform.TALEO: "https://{company}.taleo.net/careersection/2/jobdetail.ftl?job={jid}",
}


def _generate_job(index: int) -> Job:
    company = random.choice(COMPANIES)
    title = random.choice(TITLES)
    location = random.choice(LOCATIONS)
    platform = random.choice(list(PLATFORM_URLS.keys()))
    jid = f"{100000 + index}"
    url = PLATFORM_URLS[platform].format(
        company=company.lower().replace(" ", ""), jid=jid
    )
    return Job(
        url=url,
        title=title,
        company=company,
        location=location,
        description=f"{title} at {company}. Work on cutting-edge technology in {location}.",
        platform=platform,
        status=JobStatus.READY,
    )


async def seed(num_jobs: int = 100):
    async with session_factory() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.email == "admin@autoapplyai.com"))
        admin = result.scalar_one_or_none()

        if admin is None:
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
                    "Why are you interested in this role?": "I am passionate about building scalable systems.",
                    "How did you hear about us?": "LinkedIn",
                },
            )
            db.add(profile)
            print("Admin user created: admin@autoapplyai.com / admin123456")
        else:
            print("Admin user already exists.")

        # Count existing jobs
        count_result = await db.execute(select(func.count()).select_from(Job))
        existing_count = count_result.scalar()

        jobs_to_create = max(0, num_jobs - existing_count)
        if jobs_to_create == 0:
            print(f"Already have {existing_count} jobs. Skipping job creation.")
        else:
            print(f"Creating {jobs_to_create} jobs (existing: {existing_count})...")
            batch_size = 500
            for i in range(0, jobs_to_create, batch_size):
                batch = [_generate_job(existing_count + i + j) for j in range(min(batch_size, jobs_to_create - i))]
                db.add_all(batch)
                await db.flush()
                print(f"  Batch {i // batch_size + 1}: {len(batch)} jobs added")

        await db.commit()
        final_count = (await db.execute(select(func.count()).select_from(Job))).scalar()
        print(f"Seed complete. Total jobs in database: {final_count}")


if __name__ == "__main__":
    import sys
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(seed(num))
