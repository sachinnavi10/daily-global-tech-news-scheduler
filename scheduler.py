"""Schedule automatic news refreshes."""

from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

import config
from briefing_service import format_briefing, generate_daily_briefing, save_briefing
from database import (
    connect_to_mongodb,
    get_recent_news,
    get_saved_refresh_schedule,
    save_news_articles,
    save_refresh_schedule,
)
from news_service import NewsServiceError, fetch_latest_news

DEFAULT_REFRESH_SCHEDULE = "daily"
SCHEDULE_OPTIONS = {
    "daily": "Daily at the configured time",
    "1_minute": "Every 1 minute",
    "5_minutes": "Every 5 minutes",
    "1_hour": "Every 1 hour",
    "1_day": "Every 24 hours",
}
INTERVALS = {
    "1_minute": {"minutes": 1},
    "5_minutes": {"minutes": 5},
    "1_hour": {"hours": 1},
    "1_day": {"days": 1},
}
REFRESH_JOB_ID = "technology-news-refresh"

scheduler = BackgroundScheduler()
_current_schedule = DEFAULT_REFRESH_SCHEDULE


def _add_refresh_job(schedule: str) -> None:
    job_options: dict[str, Any] = {
        "id": REFRESH_JOB_ID,
        "replace_existing": True,
        "coalesce": True,
        "max_instances": 1,
        "next_run_time": datetime.now(scheduler.timezone),
    }

    if schedule == "daily":
        scheduler.add_job(
            run_news_refresh,
            "cron",
            hour=config.NEWS_SCHEDULE_HOUR,
            minute=config.NEWS_SCHEDULE_MINUTE,
            **job_options,
        )
    elif schedule in INTERVALS:
        scheduler.add_job(
            run_news_refresh,
            "interval",
            **INTERVALS[schedule],
            **job_options,
        )
    else:
        raise ValueError("Choose a supported news refresh schedule.")


def run_news_refresh() -> None:
    """Fetch news, store it, generate today's briefing, and print it."""
    try:
        connect_to_mongodb()
        fetched_articles = fetch_latest_news()
        inserted_count, duplicate_count = save_news_articles(fetched_articles)
        recent_articles = get_recent_news()
        briefing = generate_daily_briefing(recent_articles)
        save_briefing(briefing)

        print(
            f"News refresh complete: fetched {len(fetched_articles)}, "
            f"inserted {inserted_count}, duplicates {duplicate_count}."
        )
        print(format_briefing(briefing))
    except (ConnectionError, NewsServiceError, RuntimeError) as error:
        print(f"News refresh failed: {error}")


def start_scheduler() -> str:
    """Load the saved schedule and start automatic refreshes."""
    global _current_schedule

    if scheduler.running:
        return _current_schedule

    connect_to_mongodb()
    saved_schedule = get_saved_refresh_schedule()
    selected_schedule = saved_schedule or DEFAULT_REFRESH_SCHEDULE
    if selected_schedule not in SCHEDULE_OPTIONS:
        raise RuntimeError("The saved news refresh schedule is not supported.")

    _add_refresh_job(selected_schedule)
    scheduler.start()
    _current_schedule = selected_schedule
    return _current_schedule


def set_refresh_schedule(schedule: str) -> dict[str, str]:
    """Change and persist the automatic news refresh interval."""
    global _current_schedule

    if schedule not in SCHEDULE_OPTIONS:
        raise ValueError("Choose a supported news refresh schedule.")
    if not scheduler.running:
        raise RuntimeError("The news scheduler is not running.")

    previous_schedule = _current_schedule
    _add_refresh_job(schedule)
    try:
        save_refresh_schedule(schedule)
    except RuntimeError:
        _add_refresh_job(previous_schedule)
        raise

    _current_schedule = schedule
    return get_refresh_schedule()


def get_refresh_schedule() -> dict[str, str]:
    """Return the selected schedule and a label suitable for the UI."""
    if _current_schedule == "daily":
        label = (
            f"Daily at {config.NEWS_SCHEDULE_HOUR:02d}:"
            f"{config.NEWS_SCHEDULE_MINUTE:02d}"
        )
    else:
        label = SCHEDULE_OPTIONS[_current_schedule]

    return {"value": _current_schedule, "label": label}


def stop_scheduler() -> None:
    """Stop the background scheduler when the application shuts down."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
