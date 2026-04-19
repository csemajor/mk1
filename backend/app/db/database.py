from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import ConfigurationError

from ..core.config import settings

_mongo_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _mongo_client, _database

    mongo_uri = settings.MONGO_URI
    if not mongo_uri:
        raise RuntimeError("MONGO_URI environment variable is not set.")

    _mongo_client = AsyncIOMotorClient(mongo_uri)

    try:
        _database = _mongo_client.get_default_database()
    except ConfigurationError:
        _database = _mongo_client[settings.MONGO_DB_NAME]

    # Mobile is the primary credential for customer auth.
    await _database.get_collection("users").create_index(
        [("mobile", 1)],
        unique=True,
        sparse=True,
        name="uniq_users_mobile",
    )


async def close_mongo_connection() -> None:
    global _mongo_client, _database

    if _mongo_client is not None:
        _mongo_client.close()

    _mongo_client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError("Database is not initialized. Call connect_to_mongo() first.")
    return _database


def get_service_collection() -> AsyncIOMotorCollection:
    return get_database().get_collection("services")


def get_booking_collection() -> AsyncIOMotorCollection:
    return get_database().get_collection("bookings")


def get_review_collection() -> AsyncIOMotorCollection:
    return get_database().get_collection("reviews")


def get_user_collection() -> AsyncIOMotorCollection:
    return get_database().get_collection("users")