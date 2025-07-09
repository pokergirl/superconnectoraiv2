from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None

db = Database()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    try:
        db.client = AsyncIOMotorClient(
            settings.DATABASE_URL,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        # The ismaster command is cheap and does not require auth.
        await db.client.admin.command('ismaster')
        logger.info("Successfully connected to MongoDB.")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")


async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
    logger.info("MongoDB connection closed.")

def get_database():
    if db.client is None:
        raise Exception("Database client not initialized. Call connect_to_mongo first.")
    # Use the specific database name from settings
    return db.client[settings.DATABASE_NAME]