import asyncio
import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient
from asgi_lifespan import LifespanManager
from app.main import app
from app.core.db import get_database
from app.core.security import get_password_hash
from app.models.user import UserInDB, UserStatus

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_app():
    return app

@pytest_asyncio.fixture(scope="function")
async def db():
    database = get_database()
    yield database
    await database.users.delete_many({})

@pytest_asyncio.fixture(scope="function")
async def client(test_app):
    async with LifespanManager(test_app):
        transport = httpx.ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

@pytest_asyncio.fixture(scope="function")
async def test_user(db):
    user_data = {
        "email": "test@example.com",
        "hashed_password": get_password_hash("testpassword"),
        "status": UserStatus.active,
    }
    user = UserInDB(**user_data)
    user_dict = user.model_dump()
    user_dict["id"] = str(user_dict["id"])
    await db.users.insert_one(user_dict)
    return user_dict

@pytest_asyncio.fixture(scope="function")
async def test_user_must_change_password(db):
    user_data = {
        "email": "changepass@example.com",
        "hashed_password": get_password_hash("testpassword"),
        "status": UserStatus.active,
        "must_change_password": True,
    }
    user = UserInDB(**user_data)
    user_dict = user.model_dump()
    user_dict["id"] = str(user_dict["id"])
    await db.users.insert_one(user_dict)
    return user_dict

@pytest_asyncio.fixture(scope="function")
async def authorized_client(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user["email"], "password": "testpassword"},
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client