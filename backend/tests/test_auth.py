from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.config import settings

PREFIX = settings.api_v1_prefix


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post(
        f"{PREFIX}/auth/register",
        json={
            "email": "new@example.com",
            "password": "securepassword123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@example.com",
        "password": "securepassword123",
        "full_name": "User One",
    }
    await client.post(f"{PREFIX}/auth/register", json=payload)
    response = await client.post(f"{PREFIX}/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register first
    await client.post(
        f"{PREFIX}/auth/register",
        json={
            "email": "login@example.com",
            "password": "testpassword123",
            "full_name": "Login User",
        },
    )
    # Login
    response = await client.post(
        f"{PREFIX}/auth/login",
        json={"email": "login@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        f"{PREFIX}/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "correctpassword",
            "full_name": "Test User",
        },
    )
    response = await client.post(
        f"{PREFIX}/auth/login",
        json={"email": "wrongpass@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict):
    response = await client.get(f"{PREFIX}/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.get(f"{PREFIX}/users/me")
    assert response.status_code == 403
