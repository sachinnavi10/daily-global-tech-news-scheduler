"""Application settings loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


def _read_integer(name: str, default: int) -> int:
    """Read an integer setting and report a useful error if it is invalid."""
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "tech_news")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

NEWS_SCHEDULE_HOUR = _read_integer("NEWS_SCHEDULE_HOUR", 6)
NEWS_SCHEDULE_MINUTE = _read_integer("NEWS_SCHEDULE_MINUTE", 0)

if not 0 <= NEWS_SCHEDULE_HOUR <= 23:
    raise ValueError("NEWS_SCHEDULE_HOUR must be between 0 and 23.")

if not 0 <= NEWS_SCHEDULE_MINUTE <= 59:
    raise ValueError("NEWS_SCHEDULE_MINUTE must be between 0 and 59.")
