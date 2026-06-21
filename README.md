# TickTask

⚠️ **This project is under active development and not yet ready for production use. Expect changes, bugs, and incomplete features.**

**TickTask** is a web application to clock in/out and track the time spent across
tasks and subtasks, with a dashboard and a calendar to review past time and plan ahead.

## Stack

- **Backend** — Django 5 + Django Ninja (REST API) with JWT auth, Celery + Redis for
  background jobs, and SQLite for development.
- **Frontend** — Nuxt 3 (SPA, SSR disabled) styled with Tailwind CSS and Lucide icons.

## Requirements

- Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js ≥ 18 and npm
- Redis — only needed for the Celery background jobs

## Backend

From the repository root:

```sh
uv sync                                       # install dependencies
uv run python ticktask/manage.py migrate
uv run python ticktask/manage.py createsuperuser
uv run python ticktask/manage.py runserver    # http://localhost:8000
```

The API is served under `/api`, with interactive docs at <http://localhost:8000/api/docs>.

### Tests

```sh
uv run pytest
```

## Frontend

```sh
cd gui
npm install
npm run dev                                   # http://localhost:3000
```

The frontend reads the backend URL from `gui/.env` (`NUXT_PUBLIC_API_URL`, defaults to
`http://localhost:8000/api`). Copy `gui/.env.example` to `gui/.env` to customise it.

## Celery (optional)

The background jobs (e.g. auto-closing stale time entries) need Redis on `:6379`:

```sh
docker run -d --name redis -p 6379:6379 redis:7
```

Then run the worker and the beat scheduler in separate terminals:

```sh
uv run celery -A ticktask worker -l info
uv run celery -A ticktask beat -l info
```
