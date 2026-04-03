from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.config import settings

PREFIX = settings.api_v1_prefix


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        f"{PREFIX}/jobs/",
        json={
            "url": "https://company.wd5.myworkdayjobs.com/en-US/careers/job/Engineer_12345",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["platform"] == "workday"
    assert data["status"] == "detected"


@pytest.mark.asyncio
async def test_create_job_greenhouse(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        f"{PREFIX}/jobs/",
        json={
            "url": "https://boards.greenhouse.io/company/jobs/12345",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["platform"] == "greenhouse"


@pytest.mark.asyncio
async def test_create_job_unknown_platform(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        f"{PREFIX}/jobs/",
        json={"url": "https://example.com/careers/job/123"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["platform"] == "unknown"
    assert response.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, auth_headers: dict):
    response = await client.get(f"{PREFIX}/jobs/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_bulk_create_jobs(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        f"{PREFIX}/jobs/bulk",
        json={
            "urls": [
                "https://company.wd5.myworkdayjobs.com/job1",
                "https://boards.greenhouse.io/company/jobs/456",
                "https://jobs.lever.co/company/789",
            ]
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
