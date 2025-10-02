from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings
import logging
from typing import Optional
from bson.codec_options import CodecOptions
from uuid import UUID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None

db = Database()

async def connect_to_mongo():
    """
    Establishes a connection to MongoDB with standard UUID representation.
    """
    logger.info("Connecting to MongoDB with standard UUID representation...")
    try:
        # Pass uuidRepresentation directly as a keyword argument
        db.client = AsyncIOMotorClient(
            settings.DATABASE_URL,
            tls=True,
            tlsAllowInvalidCertificates=True,
            uuidRepresentation='standard'  # Use 'standard' for cross-language compatibility
        )
        
        # The ismaster command is cheap and does not require auth.
        await db.client.admin.command('ismaster')
        
        # Log the configured UUID representation
        db_instance = get_database()
        logger.info(f"Successfully connected to MongoDB. UUID representation: {db_instance.codec_options.uuid_representation}")
        
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}", exc_info=True)
        raise

async def close_mongo_connection():
    """
    Closes the MongoDB connection.
    """
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
    logger.info("MongoDB connection closed.")

def get_database():
    """
    Returns the database instance, ensuring the client is initialized.
    """
    if db.client is None:
        raise Exception("Database client not initialized. Call connect_to_mongo first.")
    
    # Return the database with the correct codec options
    return db.client.get_database(settings.DATABASE_NAME)