import asyncio
from app.core.db import get_database, connect_to_mongo, close_mongo_connection
from app.models.user import UserInDB, UserRole, UserStatus
from app.core.security import get_password_hash
from datetime import datetime

async def create_test_user():
    """Create a test user for diagnosis"""
    await connect_to_mongo()
    db = get_database()
    
    # Check if test user already exists
    test_email = "test@example.com"
    existing_user = await db.users.find_one({"email": test_email})
    if existing_user:
        print(f"Test user with email {test_email} already exists.")
        await close_mongo_connection()
        return

    hashed_password = get_password_hash("testpassword")
    
    test_user = UserInDB(
        email=test_email,
        hashed_password=hashed_password,
        role=UserRole.user,
        status=UserStatus.active,
        is_premium=False,
        must_change_password=False,
        created_at=datetime.utcnow()
    )
    
    user_dict = test_user.model_dump()
    user_dict["id"] = str(user_dict["id"])
    
    await db.users.insert_one(user_dict)
    print(f"Test user {test_email} created successfully.")
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(create_test_user())