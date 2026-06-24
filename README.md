# TickTask

**TickTask** is a personal time-tracking and productivity web app. You break work
into **tasks** and **subtasks**, clock in/out to record **time entries**, review
where your time went on a **dashboard**, and plan ahead on a **calendar** — with an
optional **Telegram bot** to get reminders and drive the app from chat.

## Features

- **Time tracking** — tasks ▸ subtasks ▸ clock in/out, one open entry at a time,
  manual entries with explicit times, and automatic closing of entries left open
  over 12h.
- **Dashboard** — hours today/this week/total, a bucketed trend chart, a per-task /
  per-subtask breakdown, and a "this week by task" share view.
- **Calendar** — month / week / day views; scheduled events with **recurrence**
  (weekly / monthly / yearly) shown alongside your tracked time.
- **History** — time entries grouped by day with search and range presets.
- **Accounts** — self-service signup **gated by admin approval**; management
  (renaming, deleting, restoring) via the Django admin.
- **Telegram bot** — event reminders, plus interactive commands (`/clockin`,
  `/clockout`, `/today`, `/tasks`, `/events`, `/newtask`, …) and a per-user timezone.

## Architecture

Two apps in one repository:

- **Backend** (`ticktask/`) — Django 5 + [Django Ninja](https://django-ninja.dev/)
  REST API with JWT auth, Celery + Redis for background jobs, SQLite by default.
- **Frontend** (`gui/`) — Nuxt 3 SPA (SSR disabled, hash-mode router) styled with
  Tailwind CSS and Lucide icons. Talks to the API over HTTP.

The API is served under `/api` (interactive docs at `/api/docs`).

## Run locally with Docker (recommended)

Brings up everything — API, frontend, Celery worker/beat, the Telegram bot and
Redis — with one command. The only prerequisite is Docker + Docker Compose.

```sh
git clone https://github.com/DavCorSar/TickTask.git
cd TickTask
cp .env.example .env                 # fill in TELEGRAM_* if you want the bot
docker compose up --build -d
```

- Frontend: <http://localhost:3000>
- API: <http://localhost:8000/api> (docs at `/api/docs`)

Create your admin user once, then log in:

```sh
docker compose exec backend uv run python ticktask/manage.py createsuperuser
```

Useful commands:

```sh
docker compose logs -f backend       # follow logs
docker compose down                  # stop the stack
```

## Run locally without Docker

You'll need Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/), Node.js ≥ 18, and
(optionally) Redis for the background jobs.

```sh
git clone https://github.com/DavCorSar/TickTask.git
cd TickTask
```

**Backend** (from the repo root) — `migrate` creates the SQLite database
(`db.sqlite3`) on first run:

```sh
uv sync                                            # install Python deps
uv run python ticktask/manage.py migrate           # create / update the database
uv run python ticktask/manage.py createsuperuser   # create your login
uv run python ticktask/manage.py runserver         # http://localhost:8000
```

**Frontend**:

```sh
cd gui
npm install
npm run dev                                        # http://localhost:3000
```

The frontend reads the API URL from `NUXT_PUBLIC_API_URL` (defaults to
`http://localhost:8000/api`); copy `gui/.env.example` to `gui/.env` to change it.

**Background jobs** (optional) — need Redis on `:6379`:

```sh
docker run -d --name redis -p 6379:6379 redis:7
uv run celery -A ticktask worker -l info
uv run celery -A ticktask beat -l info
```

## Telegram bot (optional)

1. Create a bot with [@BotFather](https://t.me/BotFather) and put the token and the
   bot's `@username` in `.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`).
2. The Docker stack runs the bot automatically (long-polling). Running by hand:
   `uv run python ticktask/manage.py run_telegram_bot`.
3. In the app, open **Settings → Connect Telegram** and follow the link to link your
   chat. From then on you'll get reminders and can use the bot commands.

## Tests

```sh
uv run pytest          # backend (pytest + pytest-django)
cd gui && npm test     # frontend unit tests (Vitest)
```

## Deploy to production

A hardened single-host Docker setup is in `docker-compose.prod.yml` (gunicorn +
Celery worker/beat + the bot + an nginx that serves the built SPA and proxies the
API + Redis), exposed to the internet for free via **Tailscale Funnel** — no
domain, no static IP, no open ports. From a brand-new machine:

**1. Install Docker** (+ Docker Compose) and **get the code**:

```sh
git clone https://github.com/DavCorSar/TickTask.git
cd TickTask
```

**2. Set up Tailscale Funnel** (free, no domain): create a
[Tailscale](https://login.tailscale.com) account, enable **HTTPS** and the
**Funnel** feature for your tailnet, and generate an **auth key**. Your public URL
will be `https://ticktask.<your-tailnet>.ts.net` (the `ticktask` part is the
`hostname:` of the `tailscale` service in `docker-compose.prod.yml`).

**3. Configure the environment** — copy the template and fill it in:

```sh
cp .env.prod.example .env
```

Key variables to set in `.env`:

| Variable | What to put |
| --- | --- |
| `DJANGO_SECRET_KEY` | A long random string (`python -c "import secrets; print(secrets.token_urlsafe(64))"`). |
| `DJANGO_DEBUG` | `False`. |
| `DJANGO_ALLOWED_HOSTS` | Your public hostname, e.g. `ticktask.<your-tailnet>.ts.net`. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | The same, with scheme: `https://ticktask.<your-tailnet>.ts.net`. |
| `TS_AUTHKEY` | The Tailscale auth key from step 2. |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_BOT_USERNAME` | Optional — only if you want the bot. |

`.env` holds secrets and is git-ignored — never commit it.

**4. Launch** the stack with the public tunnel, then create your admin user:

```sh
docker compose -f docker-compose.prod.yml --profile public up --build -d
docker compose -f docker-compose.prod.yml exec backend \
    uv run python ticktask/manage.py createsuperuser
```

The `backend` service runs migrations (creating the database on the persistent
`app-data` volume) and `collectstatic` automatically on start. The app is then
live at your `.ts.net` URL. New users sign up at `/#/signup` and you approve them
from the Django admin (`/admin/`) or the Telegram buttons.

See **[DEPLOY.md](DEPLOY.md)** for the full guide: the one-time Tailscale Funnel
setup in detail, Cloudflare Tunnel as an alternative, operating/updating the
stack, backups, and limits.

### Docker images at a glance

| Purpose      | Compose file                | Backend image | Frontend image          |
| ------------ | --------------------------- | ------------- | ----------------------- |
| Local dev    | `docker-compose.yml`        | `Dockerfile`  | `gui/Dockerfile` (Nuxt dev) |
| Production   | `docker-compose.prod.yml`   | `Dockerfile`  | `gui/Dockerfile.prod` (Nuxt build → nginx) |

## Repository layout

```
ticktask/          Django backend (models, Ninja API, Celery tasks, Telegram bot)
gui/               Nuxt 3 frontend (pages, components, composables, utils)
docker-compose.yml         Local dev stack
docker-compose.prod.yml    Production stack
DEPLOY.md          Production deployment guide
```
