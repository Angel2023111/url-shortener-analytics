# URL Shortener & Analytics Platform

A full-stack URL shortening platform built with FastAPI, PostgreSQL, Redis, Celery, and React. It supports URL creation, redirects, click analytics, API-key authentication, rate limiting, and asynchronous analytics processing.

## Features

- **URL shortening:** Generate short codes for long URLs and redirect users to the original destinations.
- **Click analytics:** Record clicks and visualize analytics through an interactive dashboard.
- **Background processing:** Use Celery workers and Redis to process analytics refresh tasks asynchronously.
- **Caching:** Use Redis to cache URL lookups and reduce repeated database queries.
- **API-key authentication:** Protect URL creation and task-status endpoints with API keys.
- **Rate limiting:** Limit URL creation requests.
- **URL expiration:** Support expiration dates and reject expired links.
- **Task status tracking:** Track background tasks and restrict task-status access to their owners.
- **Automated tests:** Validate API behavior, redirects, analytics, authentication, rate limiting, and task ownership.

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL, Alembic |
| Caching and message broker | Redis |
| Background jobs | Celery |
| Frontend | React, Vite |
| Visualization | Recharts |
| Testing | Pytest |

## Architecture

1. The React dashboard sends requests to the FastAPI backend.
2. FastAPI validates requests, checks API keys and rate limits, and interacts with PostgreSQL.
3. Redis caches URL lookups and serves as the Celery message broker and result backend.
4. Celery workers execute analytics refresh tasks asynchronously.
5. The dashboard polls task status and displays analytics results.

## Running Locally

### Prerequisites

- Python and Node.js
- PostgreSQL
- Redis

### Backend

Create and activate a Python virtual environment, then install the project's dependencies using its dependency file.

Configure the following environment variables:

- `DATABASE_URL` — PostgreSQL connection URL for the application.
- `TEST_DATABASE_URL` — PostgreSQL connection URL for the test database.
- `CELERY_BROKER_URL` — Redis broker URL.
- `CELERY_RESULT_BACKEND` — Redis result-backend URL.

Run database migrations using Alembic, then start the API:

```bash
python -m uvicorn app.main:app --reload
```

Start the Celery worker in a separate terminal:

```bash
celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

From the project root, configure the test database URL and run:

```bash
python -m pytest -q
```

The current test suite contains 29 passing tests.

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/urls` | Create a short URL |
| `GET` | `/{short_code}` | Redirect to the original URL |
| `GET` | `/api/urls/{short_code}/analytics` | Retrieve click analytics |
| `GET` | `/api/urls/{short_code}/analytics/daily` | Retrieve daily click analytics |
| `POST` | `/api/urls/{short_code}/analytics/refresh` | Enqueue an analytics refresh |
| `GET` | `/api/tasks/{task_id}` | Retrieve background task status |

Refer to the application routes and schemas for exact request formats and authentication requirements.

## Engineering Highlights

- Implemented asynchronous task processing with task ownership isolation.
- Combined caching, relational persistence, and background processing in a single application.
- Added automated tests for important API behaviors and failure cases.
