"""
Scrape real job URLs from Greenhouse and Lever public APIs,
insert them into the database, and optionally trigger mass apply.

Usage:
    python scrape_real_jobs.py [--apply]
"""
from __future__ import annotations

import asyncio
import sys
import time
from urllib.parse import urlparse

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.job import Job, JobPlatform, JobStatus

engine = create_async_engine(settings.database_url)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Top companies on Greenhouse (public boards)
GREENHOUSE_COMPANIES = [
    "airbnb", "airtable", "brex", "cloudflare", "coinbase",
    "datadog", "discord", "doordash", "figma", "flexport",
    "gusto", "hubspot", "intercom", "loom", "lyft",
    "mongodb", "notion", "openai", "palantir", "plaid",
    "ramp", "retool", "robinhood", "scale", "snyk",
    "sourcegraph", "stripe", "twilio", "twitch", "vanta",
    "watershed", "whatnot", "wiz", "zapier", "zscaler",
    "cockroachlabs", "dbt-labs", "hashicorp", "netlify", "vercel",
    "postman", "gitlabhq", "elastic", "grafanalabs", "sentry",
    "tailscale", "temporal", "1password", "linear", "anduril",
    "benchling", "braze", "chainalysis", "checkout", "chime",
    "deel", "deliveroo", "faire", "fastly", "fivetran",
    "forter", "grammarly", "gusto", "highspot", "hims",
    "justworks", "klarna", "lattice", "lemonade", "marqeta",
    "masterclass", "mux", "nerdwallet", "nextdoor", "noom",
    "opendoor", "outreach", "pagerduty", "patreon", "peloton",
    "privy", "procore", "qualtrics", "readme", "recurly",
    "relativity", "remote", "samsara", "segment", "sendbird",
    "squarespace", "stytch", "supabase", "taskrabbit", "thumbtack",
    "toast", "truebill", "upstart", "vimeo", "webflow",
    "wealthsimple", "weave", "zocdoc", "ironclad", "carta",
]

# Top companies on Lever (public postings)
LEVER_COMPANIES = [
    "netflix", "spotify", "snap", "shopify", "databricks",
    "confluent", "autodesk", "pinterest", "instacart", "reddit",
    "miro", "amplitude", "asana", "atlassian", "box",
    "calendly", "canva", "clearbit", "contentful", "courier",
    "covariant", "cruise", "darktrace", "deepmind", "drata",
    "envoy", "ethyca", "everlaw", "fakespot", "gong",
    "greenhouse", "harness", "ideo", "jumpcloud", "kissmetrics",
    "komodor", "lacework", "launchdarkly", "lightstep", "lucid",
    "mattermost", "mercury", "modern-treasury", "motherduck",
    "mysten-labs", "navan", "olo", "ontra", "osano",
    "pendo", "persona", "pilot", "plaid", "podium",
    "preqin", "prima", "prisma", "productboard", "propel",
    "pulumi", "rainforestqa", "replit", "reverb", "riskified",
    "rivian", "semgrep", "snorkel", "spirion", "standard-ai",
    "starburst", "stigg", "styra", "superhuman", "talkdesk",
    "tessian", "thoughtspot", "transport-for-london", "trueaccord",
    "unqork", "vanta", "verkada", "wepay", "xero",
]


async def scrape_greenhouse(client: httpx.AsyncClient, company: str) -> list[dict]:
    """Fetch jobs from a Greenhouse public board API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = data.get("jobs", [])
        results = []
        for j in jobs:
            abs_url = j.get("absolute_url", "")
            if not abs_url:
                continue
            results.append({
                "url": abs_url,
                "title": j.get("title", ""),
                "company": company.replace("-", " ").title(),
                "location": j.get("location", {}).get("name", ""),
                "platform": JobPlatform.GREENHOUSE,
            })
        return results
    except Exception:
        return []


async def scrape_lever(client: httpx.AsyncClient, company: str) -> list[dict]:
    """Fetch jobs from a Lever public postings API."""
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = []
        for j in data:
            posting_url = j.get("hostedUrl", "")
            if not posting_url:
                continue
            loc = j.get("categories", {}).get("location", "")
            results.append({
                "url": posting_url[:2000],
                "title": j.get("text", "")[:490],
                "company": company.replace("-", " ").title()[:250],
                "location": (loc or "")[:490],
                "platform": JobPlatform.LEVER,
            })
        return results
    except Exception:
        return []


async def scrape_all_jobs(target: int = 10000) -> list[dict]:
    """Scrape jobs from all platforms until we reach target count."""
    all_jobs = []
    seen_urls = set()

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; AutoApplyAI/1.0)"},
        follow_redirects=True,
    ) as client:
        # Scrape Greenhouse in batches
        print(f"Scraping Greenhouse ({len(GREENHOUSE_COMPANIES)} companies)...")
        for i in range(0, len(GREENHOUSE_COMPANIES), 10):
            batch = GREENHOUSE_COMPANIES[i : i + 10]
            tasks = [scrape_greenhouse(client, c) for c in batch]
            results = await asyncio.gather(*tasks)
            for company_jobs in results:
                for j in company_jobs:
                    if j["url"] not in seen_urls:
                        seen_urls.add(j["url"])
                        all_jobs.append(j)
            count = len(all_jobs)
            print(f"  Batch {i // 10 + 1}: {count} total jobs so far")
            if count >= target:
                break
            await asyncio.sleep(0.5)

        if len(all_jobs) < target:
            # Scrape Lever
            print(f"\nScraping Lever ({len(LEVER_COMPANIES)} companies)...")
            for i in range(0, len(LEVER_COMPANIES), 10):
                batch = LEVER_COMPANIES[i : i + 10]
                tasks = [scrape_lever(client, c) for c in batch]
                results = await asyncio.gather(*tasks)
                for company_jobs in results:
                    for j in company_jobs:
                        if j["url"] not in seen_urls:
                            seen_urls.add(j["url"])
                            all_jobs.append(j)
                count = len(all_jobs)
                print(f"  Batch {i // 10 + 1}: {count} total jobs so far")
                if count >= target:
                    break
                await asyncio.sleep(0.5)

    # Trim to target
    all_jobs = all_jobs[:target]
    print(f"\nTotal unique jobs scraped: {len(all_jobs)}")

    # Stats
    platforms = {}
    for j in all_jobs:
        p = j["platform"].value
        platforms[p] = platforms.get(p, 0) + 1
    for p, c in sorted(platforms.items()):
        print(f"  {p}: {c}")

    return all_jobs


async def insert_jobs(jobs: list[dict]) -> int:
    """Insert scraped jobs into the database, skipping duplicates."""
    async with session_factory() as db:
        # Get existing URLs to avoid duplicates
        result = await db.execute(select(Job.url))
        existing_urls = {row[0] for row in result.all()}

        new_jobs = [j for j in jobs if j["url"] not in existing_urls]
        print(f"\nInserting {len(new_jobs)} new jobs ({len(jobs) - len(new_jobs)} duplicates skipped)...")

        batch_size = 500
        inserted = 0
        for i in range(0, len(new_jobs), batch_size):
            batch = new_jobs[i : i + batch_size]
            for j in batch:
                db.add(Job(
                    url=j["url"],
                    title=j["title"],
                    company=j["company"],
                    location=j["location"],
                    platform=j["platform"],
                    status=JobStatus.READY,
                ))
            await db.flush()
            inserted += len(batch)
            print(f"  Inserted batch {i // batch_size + 1}: {inserted} / {len(new_jobs)}")

        await db.commit()

        total = (await db.execute(select(func.count()).select_from(Job))).scalar()
        print(f"\nTotal jobs in database: {total}")
        return len(new_jobs)


async def main():
    do_apply = "--apply" in sys.argv
    target = 10000

    # Parse target from args
    for arg in sys.argv[1:]:
        if arg.isdigit():
            target = int(arg)

    print(f"=== AutoApplyAI Job Scraper ===")
    print(f"Target: {target} jobs")
    print()

    # Scrape
    start = time.time()
    jobs = await scrape_all_jobs(target)
    elapsed = time.time() - start
    print(f"Scraping completed in {elapsed:.1f}s")

    # Insert
    new_count = await insert_jobs(jobs)

    if do_apply and new_count > 0:
        print(f"\n=== Triggering mass apply for all ready jobs ===")
        # We could call the API, but since we're inside the container,
        # let's use the Celery task directly
        from app.workers.tasks.application_tasks import bulk_apply
        async with session_factory() as db:
            # Get admin user
            from app.models.user import User
            result = await db.execute(select(User).where(User.email == "admin@autoapplyai.com"))
            user = result.scalar_one()

            # Get all READY job IDs that don't have active applications
            from app.models.application import Application, ApplicationStatus
            from sqlalchemy import and_, not_, exists

            subq = select(Application.job_id).where(
                and_(
                    Application.user_id == user.id,
                    Application.status.notin_([
                        ApplicationStatus.FAILED,
                        ApplicationStatus.CANCELLED,
                    ]),
                )
            )
            result = await db.execute(
                select(Job.id).where(
                    Job.status == JobStatus.READY,
                    ~Job.id.in_(subq),
                )
            )
            job_ids = [str(r[0]) for r in result.all()]
            print(f"Found {len(job_ids)} jobs ready to apply")

            # Dispatch in batches of 500 via Celery
            batch_size = 500
            for i in range(0, len(job_ids), batch_size):
                batch = job_ids[i : i + batch_size]
                bulk_apply.delay(str(user.id), batch, None)
                print(f"  Dispatched batch {i // batch_size + 1}: {len(batch)} jobs")

        print(f"\nAll jobs queued for application!")
    elif do_apply:
        print("\nNo new jobs to apply to.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
