"""MongoDB connection and collection setup."""

from datetime import date, datetime, timedelta, timezone
import re
from typing import Any, Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

import config

client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
database: Database = client[config.MONGODB_DATABASE]
news_collection: Collection = database["news"]
briefings_collection: Collection = database["daily_briefings"]
settings_collection: Collection = database["app_settings"]


def connect_to_mongodb() -> None:
    """Check the MongoDB connection and create required unique indexes."""
    try:
        client.admin.command("ping")
    except PyMongoError as error:
        raise ConnectionError(
            "Could not connect to MongoDB. Check that MongoDB is running and "
            "MONGODB_URI is correct."
        ) from error

    try:
        news_collection.create_index("url", unique=True)
        briefings_collection.create_index("briefing_date", unique=True)
    except PyMongoError as error:
        raise RuntimeError(
            "MongoDB is reachable, but the required unique indexes could not be created."
        ) from error


def save_news_articles(news_documents: list[dict[str, Any]]) -> tuple[int, int]:
    """Insert articles and return the inserted and duplicate counts."""
    inserted_count = 0
    duplicate_count = 0

    for article in news_documents:
        try:
            news_collection.insert_one(article.copy())
            inserted_count += 1
        except DuplicateKeyError:
            duplicate_count += 1
        except PyMongoError as error:
            raise RuntimeError("Could not save a news article to MongoDB.") from error

    return inserted_count, duplicate_count


def save_daily_briefing(briefing: dict[str, Any]) -> None:
    """Insert or update the briefing for its date."""
    briefing_date = briefing.get("briefing_date")
    if not isinstance(briefing_date, str):
        raise ValueError("briefing_date must be a YYYY-MM-DD string.")

    try:
        date.fromisoformat(briefing_date)
    except ValueError as error:
        raise ValueError("briefing_date must be a valid YYYY-MM-DD date.") from error

    briefing_fields = briefing.copy()
    created_at = briefing_fields.pop("created_at", datetime.now(timezone.utc))

    try:
        briefings_collection.update_one(
            {"briefing_date": briefing_date},
            {
                "$set": briefing_fields,
                "$setOnInsert": {"created_at": created_at},
            },
            upsert=True,
        )
    except PyMongoError as error:
        raise RuntimeError("Could not save the daily briefing to MongoDB.") from error


def get_recent_news(days: int = 7) -> list[dict[str, Any]]:
    """Return articles published within the requested number of days."""
    if days <= 0:
        raise ValueError("days must be greater than zero.")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        cursor = news_collection.find(
            {"published_at": {"$gte": cutoff}},
            {"_id": 0},
        ).sort("published_at", -1)
        return list(cursor)
    except PyMongoError as error:
        raise RuntimeError("Could not read recent news from MongoDB.") from error


def get_latest_news(limit: int = 50) -> list[dict[str, Any]]:
    """Return the newest stored articles."""
    try:
        cursor = news_collection.find().sort("published_at", -1).limit(limit)
        return list(cursor)
    except PyMongoError as error:
        raise RuntimeError("Could not read news from MongoDB.") from error


def get_news_by_id(article_id: ObjectId) -> Optional[dict[str, Any]]:
    """Find one news document by its MongoDB ObjectId."""
    try:
        return news_collection.find_one({"_id": article_id})
    except PyMongoError as error:
        raise RuntimeError("Could not read news from MongoDB.") from error


def get_news_by_category(category: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return articles in one category, newest first."""
    try:
        cursor = (
            news_collection.find({"category": category})
            .sort("published_at", -1)
            .limit(limit)
        )
        return list(cursor)
    except PyMongoError as error:
        raise RuntimeError("Could not filter news in MongoDB.") from error


def search_news(keyword: str, limit: int = 50) -> list[dict[str, Any]]:
    """Search article titles, descriptions, and categories."""
    safe_keyword = re.escape(keyword)
    search_filter = {
        "$or": [
            {"title": {"$regex": safe_keyword, "$options": "i"}},
            {"description": {"$regex": safe_keyword, "$options": "i"}},
            {"category": {"$regex": safe_keyword, "$options": "i"}},
        ]
    }

    try:
        cursor = (
            news_collection.find(search_filter)
            .sort("published_at", -1)
            .limit(limit)
        )
        return list(cursor)
    except PyMongoError as error:
        raise RuntimeError("Could not search news in MongoDB.") from error


def get_daily_briefings(limit: int = 30) -> list[dict[str, Any]]:
    """Return stored briefings, newest first."""
    try:
        cursor = (
            briefings_collection.find()
            .sort("briefing_date", -1)
            .limit(limit)
        )
        return list(cursor)
    except PyMongoError as error:
        raise RuntimeError("Could not read briefings from MongoDB.") from error


def get_briefing_by_date(briefing_date: str) -> Optional[dict[str, Any]]:
    """Find one briefing by its YYYY-MM-DD date."""
    try:
        return briefings_collection.find_one({"briefing_date": briefing_date})
    except PyMongoError as error:
        raise RuntimeError("Could not read the briefing from MongoDB.") from error


def get_saved_refresh_schedule() -> Optional[str]:
    """Read the selected scheduler setting, if one has been saved."""
    try:
        setting = settings_collection.find_one({"_id": "news_refresh_schedule"})
    except PyMongoError as error:
        raise RuntimeError("Could not read the saved refresh schedule.") from error

    if setting is None:
        return None

    schedule = setting.get("value")
    if not isinstance(schedule, str):
        raise RuntimeError("The saved refresh schedule is invalid.")
    return schedule


def save_refresh_schedule(schedule: str) -> None:
    """Persist the selected refresh schedule for the next application start."""
    try:
        settings_collection.update_one(
            {"_id": "news_refresh_schedule"},
            {
                "$set": {
                    "value": schedule,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
    except PyMongoError as error:
        raise RuntimeError("Could not save the refresh schedule.") from error
