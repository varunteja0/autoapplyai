from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app

# Use a test database — only replace the DB name at the end of the URL
_base_url = settings.database_url
TEST_DB_URL = _base_url.rsplit("/", 1)[0] + "/autoapplyai_test"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Create engine per-test to avoid event loop mismatch
    test_engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session

    # Cleanup: truncate all tables
    async with test_engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE TABLE application_logs, applications, resumes, user_profiles, jobs, users RESTART IDENTITY CASCADE")
        )

    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a test user and return auth headers."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/register",
        json={
            "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
        },
    )
    data = response.json()
    assert "access_token" in data, f"Registration failed: {data}"
    return {"Authorization": f"Bearer {data['access_token']}"}
