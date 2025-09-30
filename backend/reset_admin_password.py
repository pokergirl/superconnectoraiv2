import asyncio
from app.core.db import connect_to_mongo, close_mongo_connection, get_database
from app.core.security import get_password_hash

async def reset_admin_password():
    """
    Resets the admin password to "password".
    """
    await connect_to_mongo()
    db = get_database()
    
    hashed_password = get_password_hash("password")
    
    await db.users.update_one(
        {"email": "admin@superconnect.ai"},
        {"$set": {"hashed_password": hashed_password}},
    )
    
    print("Admin password reset to 'password'.")
    
if __name__ == "__main__":
    try:
        asyncio.run(reset_admin_password())
    finally:
        asyncio.run(close_mongo_connection())