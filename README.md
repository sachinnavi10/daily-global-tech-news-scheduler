# Daily Global Tech News Scheduler

A beginner-friendly Python project that collects technology news, stores it in MongoDB, creates a daily briefing, and displays the results in a small browser UI.

The Python application must stay running for scheduled collection and UI updates to continue.

## Project objective

The project requests English technology stories from NewsAPI, assigns each one a category using editable keywords, avoids duplicate URLs in MongoDB, scores stories with simple rules, and creates a concise daily briefing. Each NewsAPI request asks for up to 100 recent results; only articles with a non-empty title and URL are stored.

The briefing groups stories under AI, Agentic AI, Quantum Computing, Cloud & Software, Cybersecurity, and Technology Business. It also suggests one learning topic and relevant career skills. Stories are selected by category, publication recency, and high-impact terms; no stories are selected randomly.

### How a refresh works

1. The scheduler requests English results for technology, AI, quantum computing, cloud, cybersecurity, programming, developer tools, and startup-related search terms.
2. Article metadata is normalized and categorized using the keyword rules in `models.py`.
3. MongoDB stores each URL once. A duplicate URL is skipped rather than updating the existing article.
4. The briefing ranks articles using category weights, publication recency, and high-impact terms. It considers articles from the last seven days, selects up to three per category, and builds the briefing sections, learning topic, and career skills.
5. The briefing for the current date is inserted or replaced in MongoDB. Its original `created_at` value is preserved when it is regenerated.

These are rule-based results, not AI-generated summaries. Article summaries come from the source's description when available.

## Technologies

- Python 3.9 or newer
- Flask REST API
- Requests and JSON
- MongoDB and PyMongo
- APScheduler
- HTML, CSS, and JavaScript
- VS Code, Postman, and MongoDB Compass
- NewsAPI for the sample news provider

The NewsAPI key is sent in the `X-Api-Key` request header. Review the [NewsAPI documentation](https://newsapi.org/docs) and your account's access limits before using it.

## Project structure

```text
daily-tech-news/
├── main.py                 # Flask routes and application startup
├── config.py               # Environment-based settings
├── database.py             # MongoDB connection, queries, and writes
├── news_service.py         # NewsAPI request and article normalization
├── briefing_service.py     # Scoring, selection, and briefing formatting
├── scheduler.py            # APScheduler refresh job and interval settings
├── models.py               # Editable category keywords and categorization
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── static/
    ├── index.html
    ├── styles.css
    └── app.js
```

## Installation

Open PowerShell in the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell prevents environment activation, either allow activation for your user according to your organization's policy or run the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## MongoDB setup

1. Install [MongoDB Community Server](https://www.mongodb.com/try/download/community) and configure it to run as a Windows service.
2. Start the MongoDB service if the installer did not start it automatically.
3. Optionally install [MongoDB Compass](https://www.mongodb.com/products/tools/compass).
4. The default local connection URI is `mongodb://localhost:27017`.

The application uses the `tech_news` database. On startup it checks the connection and creates unique indexes for article URLs and briefing dates. MongoDB creates collections when they are first needed.

### Collections and documents

`news` stores one article document per URL:

```json
{
  "title": "Example AI tools announced",
  "description": "A short source-provided summary.",
  "source": "Example Technology News",
  "author": "Reporter Name",
  "url": "https://example.com/technology-story",
  "category": "AI",
  "published_at": "2026-10-28T07:30:00+00:00",
  "collected_at": "2026-10-28T08:00:00+00:00"
}
```

The `url` field has a unique index, so a later refresh cannot insert the same article URL again.

`daily_briefings` stores one current briefing per date. A later refresh updates that date's briefing; it preserves `created_at` and updates `generated_at`.

`app_settings` stores the selected scheduler interval so the application can restore it after a restart.

### Inspect data in MongoDB Compass

1. Open Compass and connect to `mongodb://localhost:27017`.
2. Start this application and save a schedule in the UI, or let its first scheduled refresh run.
3. Open the `tech_news` database.
4. Select `news` to inspect article documents and their categories.
5. Select `daily_briefings` to inspect generated briefings.
6. Select `app_settings` to inspect the saved schedule after changing it in the UI.

## Environment variables

Copy the example file and edit the local copy:

```powershell
Copy-Item .env.example .env
```

Set the values in `.env`:

```dotenv
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=tech_news
NEWS_API_KEY=your_real_newsapi_key
NEWS_SCHEDULE_HOUR=6
NEWS_SCHEDULE_MINUTE=0
```

Never commit `.env`, API keys, database passwords, or other secrets. The repository ignores `.env`; `.env.example` contains only a placeholder.

| Variable | Purpose | Default |
|---|---|---|
| `MONGODB_URI` | MongoDB connection URI | `mongodb://localhost:27017` |
| `MONGODB_DATABASE` | Database name | `tech_news` |
| `NEWS_API_KEY` | NewsAPI key | Empty; fetching reports a clear error |
| `NEWS_SCHEDULE_HOUR` | Hour for the default daily schedule, 0–23 | `6` |
| `NEWS_SCHEDULE_MINUTE` | Minute for the default daily schedule, 0–59 | `0` |

The UI-selected schedule is stored in MongoDB rather than written back to `.env`.

## Run the application

Activate the virtual environment, then run:

```powershell
python main.py
```

If you did not activate the environment, run the virtual environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe main.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

When MongoDB is available, the app starts the scheduler and starts an initial refresh. If the database is unavailable at startup, the Flask UI still starts, but health/news requests report that the database is unavailable and scheduled refreshes do not start. Fix the MongoDB connection and restart the application.

If the NewsAPI key is missing or invalid, the refresh fails and the error is printed in the terminal. Add a valid key to `.env` and restart the application.

### Troubleshooting

| Symptom | Check |
|---|---|
| The UI loads, but news and health checks report that the database is unavailable. | Confirm MongoDB is running and `MONGODB_URI` points to it, then restart the app. |
| Refreshes fail and no articles appear. | Confirm `NEWS_API_KEY` is set in `.env`, the key is valid, and your NewsAPI account can make the request. Check the application terminal for the refresh error. |
| No briefing appears yet. | A briefing is created by a successful scheduled refresh. Check MongoDB/API availability and the terminal output; the first refresh is attempted when the scheduler starts. |
| Saving a schedule returns an error. | The scheduler must have started successfully, which requires a working MongoDB connection. Restart the app after resolving a database startup problem. |

There is no manual refresh API endpoint; starting the scheduler or saving a new schedule triggers a refresh.

## Scheduler explanation

The scheduler runs inside the Python application in the background. It does not depend on a user opening the UI or calling a refresh endpoint.

- **Daily** is a fixed local server time, defaulting to 6:00 AM. The app also starts one refresh immediately when the scheduler starts.
- **Every 1 minute**, **Every 5 minutes**, **Every 1 hour**, and **Every 24 hours** are recurring intervals. Choosing an interval starts a refresh immediately and schedules the next one after that interval.
- The selected interval is saved in `app_settings` and restored when the app restarts.
- If one refresh is still running when the next is due, APScheduler does not start a second copy of that same refresh job.
- The browser reloads news and the latest briefing at the selected cadence, allowing time for the scheduled backend refresh to finish.
- The computer and Python app must remain on/running. A laptop that sleeps, or a stopped app, cannot run the job.

For the daily schedule, the backend uses the server's local time and the browser calculates its display refresh from the browser's local clock. They match on a local development computer. If the application is hosted in a different time zone, configure a shared time zone or expose the server's next-run time.

## API documentation

The API base URL is `http://127.0.0.1:5000`.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check application and MongoDB availability |
| `GET` | `/news?limit=50` | Get the newest stored articles |
| `GET` | `/news/<id>` | Get one article by MongoDB ObjectId |
| `GET` | `/news/category/<category>` | Filter by a known category |
| `GET` | `/news/search?keyword=python` | Search title, description, and category |
| `GET` | `/briefings?limit=50` | List previous daily briefings |
| `GET` | `/briefings/YYYY-MM-DD` | Get one briefing by date |
| `GET` | `/settings/schedule` | Read the current and available schedules |
| `PUT` | `/settings/schedule` | Change and persist a schedule |

The optional `limit` must be a whole number between 1 and 100. Search keywords are required and must be 100 characters or fewer. Category names are case-insensitive and must match a supported category: `Agentic AI`, `Quantum Computing`, `Cybersecurity`, `AI`, `Cloud`, `Developer Tools`, `Programming`, `Startups`, `Technology Companies`, or `Other Technology`.

### Sample requests

```http
GET /health
GET /news?limit=10
GET /news/category/Quantum%20Computing
GET /news/search?keyword=python
GET /briefings?limit=7
GET /briefings/2026-10-28
GET /settings/schedule
```

Change the schedule in Postman with:

```http
PUT /settings/schedule
Content-Type: application/json

{
  "schedule": "5_minutes"
}
```

Supported `schedule` values are `daily`, `1_minute`, `5_minutes`, `1_hour`, and `1_day`.

### Sample responses

`GET /news?limit=1`:

```json
{
  "count": 1,
  "news": [
    {
      "_id": "671f00000000000000000001",
      "title": "Example AI tools announced",
      "description": "A short source-provided summary.",
      "source": "Example Technology News",
      "author": "Reporter Name",
      "url": "https://example.com/technology-story",
      "category": "AI",
      "published_at": "2026-10-28T07:30:00+00:00",
      "collected_at": "2026-10-28T08:00:00+00:00"
    }
  ]
}
```

`GET /health`:

```json
{
  "status": "ok",
  "database": "connected"
}
```

`GET /settings/schedule`:

```json
{
  "current": {
    "value": "daily",
    "label": "Daily at 06:00"
  },
  "available": {
    "daily": "Daily at 06:00",
    "1_minute": "Every 1 minute",
    "5_minutes": "Every 5 minutes",
    "1_hour": "Every 1 hour",
    "1_day": "Every 24 hours"
  },
  "daily_time": {
    "hour": 6,
    "minute": 0
  }
}
```

`GET /briefings/2026-10-28` returns a document containing `briefing_date`, `generated_at`, `total_news`, `categories`, `top_news`, `learning_of_the_day`, `career_opportunity`, and `created_at`.

Errors use a JSON object such as `{"error":"Article not found."}`. Invalid input returns `400`, missing articles or briefings return `404`, and unavailable database/scheduler operations return `503`.

## Test with Postman

1. Start MongoDB and the Python application.
2. Send `GET http://127.0.0.1:5000/health`; expect `200` when MongoDB is connected.
3. Send `GET http://127.0.0.1:5000/news?limit=10`.
4. Search with `GET http://127.0.0.1:5000/news/search?keyword=python`.
5. Filter with `GET http://127.0.0.1:5000/news/category/AI`.
6. Send `GET http://127.0.0.1:5000/briefings`.
7. Change the schedule using the `PUT /settings/schedule` example above.
8. Try an invalid category or date and confirm the API returns `400`.
9. Try a valid but nonexistent article ID/date and confirm the API returns `404`.

## Data flow summary

```text
APScheduler
  → NewsAPI request
  → JSON parsing and category assignment
  → MongoDB URL deduplication and article storage
  → scoring and briefing generation
  → MongoDB briefing upsert
  → Flask JSON APIs
  → Browser UI and Postman
```

## Learning notes

The project deliberately uses simple keyword matching and transparent scoring rather than machine learning or an AI summarization service. Read each module, change a few category keywords, and verify how the output changes. Be prepared to explain where the scheduler runs, how duplicate URLs are blocked, and how the UI gets its data.
