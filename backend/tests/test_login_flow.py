import pytest
from httpx import AsyncClient
from fastapi import status
from app.core.db import get_database
from app.core.security import get_password_hash

@pytest.mark.asyncio
async def test_login_with_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "invalid@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Incorrect username or password"}

@pytest.mark.asyncio
async def test_login_with_valid_credentials(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user["email"], "password": "testpassword"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_with_must_change_password(client: AsyncClient, test_user_must_change_password):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user_must_change_password["email"], "password": "testpassword"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "reset_token" in response.json()

@pytest.mark.asyncio
async def test_logout(client: AsyncClient, authorized_client):
    response = await authorized_client.post("/api/v1/auth/logout")
    assert response.status_code == status.HTTP_204_NO_CONTENT