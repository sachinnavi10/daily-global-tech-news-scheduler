"""Flask REST API for news, briefings, and scheduler settings."""

from datetime import date, datetime
from typing import Any

from bson import ObjectId
from flask import Flask, jsonify, request
from pymongo.errors import PyMongoError

import config
from database import (
    client,
    get_briefing_by_date,
    get_daily_briefings,
    get_latest_news,
    get_news_by_category,
    get_news_by_id,
    search_news,
)
from models import CATEGORY_KEYWORDS
from scheduler import (
    SCHEDULE_OPTIONS,
    get_refresh_schedule,
    set_refresh_schedule,
    start_scheduler,
    stop_scheduler,
)

app = Flask(__name__)
VALID_CATEGORIES = {
    category.casefold(): category
    for category in (*CATEGORY_KEYWORDS, "Other Technology")
}
MAX_PAGE_SIZE = 100


@app.get("/")
def home():
    return app.send_static_file("index.html")


def _serialize(value: Any) -> Any:
    """Convert MongoDB and date values to standard JSON-compatible values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def _read_limit() -> int:
    raw_limit = request.args.get("limit", "50")
    try:
        limit = int(raw_limit)
    except ValueError as error:
        raise ValueError("limit must be a whole number.") from error

    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}.")
    return limit


def _database_unavailable():
    return jsonify({"error": "Database is unavailable."}), 503


@app.get("/news")
def list_news():
    try:
        limit = _read_limit()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    try:
        news = get_latest_news(limit)
    except RuntimeError:
        return _database_unavailable()
    return jsonify({"count": len(news), "news": _serialize(news)})


@app.get("/news/search")
def search_news_route():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "keyword is required."}), 400
    if len(keyword) > 100:
        return jsonify({"error": "keyword must be 100 characters or fewer."}), 400

    try:
        limit = _read_limit()
        news = search_news(keyword, limit)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError:
        return _database_unavailable()
    return jsonify(
        {"keyword": keyword, "count": len(news), "news": _serialize(news)}
    )


@app.get("/news/category/<category>")
def list_news_by_category(category: str):
    canonical_category = VALID_CATEGORIES.get(category.casefold())
    if canonical_category is None:
        return jsonify({"error": "Invalid news category."}), 400

    try:
        limit = _read_limit()
        news = get_news_by_category(canonical_category, limit)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError:
        return _database_unavailable()
    return jsonify(
        {
            "category": canonical_category,
            "count": len(news),
            "news": _serialize(news),
        }
    )


@app.get("/news/<article_id>")
def get_news(article_id: str):
    if not ObjectId.is_valid(article_id):
        return jsonify({"error": "Article ID is invalid."}), 400

    try:
        article = get_news_by_id(ObjectId(article_id))
    except RuntimeError:
        return _database_unavailable()
    if article is None:
        return jsonify({"error": "Article not found."}), 404
    return jsonify(_serialize(article))


@app.get("/briefings")
def list_briefings():
    try:
        limit = _read_limit()
        briefings = get_daily_briefings(limit)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError:
        return _database_unavailable()
    return jsonify(
        {"count": len(briefings), "briefings": _serialize(briefings)}
    )


@app.get("/briefings/<briefing_date>")
def get_briefing(briefing_date: str):
    try:
        parsed_date = date.fromisoformat(briefing_date)
    except ValueError:
        return jsonify({"error": "Date must use the YYYY-MM-DD format."}), 400
    if parsed_date.isoformat() != briefing_date:
        return jsonify({"error": "Date must use the YYYY-MM-DD format."}), 400

    try:
        briefing = get_briefing_by_date(briefing_date)
    except RuntimeError:
        return _database_unavailable()
    if briefing is None:
        return jsonify({"error": "Briefing not found."}), 404
    return jsonify(_serialize(briefing))


@app.get("/settings/schedule")
def read_schedule():
    available = SCHEDULE_OPTIONS.copy()
    available["daily"] = (
        f"Daily at {config.NEWS_SCHEDULE_HOUR:02d}:"
        f"{config.NEWS_SCHEDULE_MINUTE:02d}"
    )
    return jsonify(
        {
            "current": get_refresh_schedule(),
            "available": available,
            "daily_time": {
                "hour": config.NEWS_SCHEDULE_HOUR,
                "minute": config.NEWS_SCHEDULE_MINUTE,
            },
        }
    )


@app.put("/settings/schedule")
def update_schedule():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "A JSON request body is required."}), 400

    schedule = body.get("schedule")
    if not isinstance(schedule, str):
        return jsonify({"error": "schedule must be a string."}), 400

    try:
        current_schedule = set_refresh_schedule(schedule)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError:
        return jsonify({"error": "The scheduler could not update its setting."}), 503
    return jsonify({"current": current_schedule})


@app.get("/health")
def health():
    try:
        client.admin.command("ping")
    except PyMongoError:
        return jsonify({"status": "unhealthy", "database": "unavailable"}), 503
    return jsonify({"status": "ok", "database": "connected"})


@app.errorhandler(404)
def handle_not_found(_error):
    return jsonify({"error": "Resource not found."}), 404


if __name__ == "__main__":
    try:
        start_scheduler()
    except (ConnectionError, RuntimeError) as error:
        print(f"Scheduler could not start: {error}")

    try:
        app.run(debug=False)
    finally:
        stop_scheduler()
