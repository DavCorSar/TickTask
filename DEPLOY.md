# Deploying TickTask

A single-host Docker deployment for a small, private user base. The stack:

| Service    | What it does                                                       |
| ---------- | ------------------------------------------------------------------ |
| `frontend` | nginx — serves the built Nuxt SPA and proxies `/api`, `/admin`     |
| `backend`  | gunicorn — Django API (runs migrations + `collectstatic` on start) |
| `worker`   | Celery worker (event reminders, auto-closing stale entries)        |
| `beat`     | Celery beat (scheduler)                                            |
| `bot`      | Telegram bot (long-polling)                                        |
| `redis`    | Celery broker/result backend + Django cache                        |

Only `frontend` (port 80) is published; everything else talks over the internal
Docker network.

## 1. Prerequisites

- A host with Docker + Docker Compose.
- A free [Tailscale](https://tailscale.com) account (for the public HTTPS URL —
  no domain required). See step 3 for alternatives.
- A Telegram bot from [@BotFather](https://t.me/BotFather) (optional, for
  reminders / the bot commands).

## 2. Configure

```sh
cp .env.prod.example .env
```

Edit `.env`:

- `DJANGO_SECRET_KEY` — a long random string
  (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).
- `DJANGO_DEBUG=False`.
- `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` — the public hostname
  you'll serve on (your Tailscale `.ts.net` URL, see step 3, or your domain).
- `TS_AUTHKEY` — a Tailscale auth key, if using Funnel (step 3).
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_BOT_USERNAME` — if using the bot.

`.env` holds secrets — keep it off version control (it's git-ignored).

## 3. Expose it to the internet (HTTPS)

Browsers and Telegram need HTTPS, and a home server has no static IP / open ports
by default. The recommended path needs neither — and it's **free, with no domain**.

### Tailscale Funnel (built into the stack)

A `tailscale` service is included (compose profile `public`). It connects
**outbound** to Tailscale, so there are **no open ports, no static IP**, it works
behind CGNAT, and Tailscale provides a **free public HTTPS URL** like
`https://<hostname>.<your-tailnet>.ts.net` — **no domain to buy**. The service
funnels that URL straight to the nginx frontend (see `tailscale/funnel.json`).

1. Create a free [Tailscale](https://login.tailscale.com) account. The onboarding
   may suggest connecting several devices — you can ignore that; **one device (this
   server) is enough** for Funnel.
2. **Enable Funnel for your tailnet**: in the admin console, the tailnet needs
   HTTPS certificates enabled (**DNS → enable HTTPS**) and the **Funnel** node
   attribute (**Access controls** ACL — add a `nodeAttrs` rule granting `funnel`,
   or use the Funnel toggle in the machine's menu). One-time setup.
3. **Generate an auth key**: admin console → **Settings → Keys → Generate auth
   key** (reusable is convenient). Put it in `.env` as `TS_AUTHKEY`.
4. The node's hostname is set on the `tailscale` service in
   `docker-compose.prod.yml` (`hostname: ticktask`, change if you like). Your URL
   becomes `https://ticktask.<your-tailnet>.ts.net` — put that **full hostname** in
   `DJANGO_ALLOWED_HOSTS` and (with `https://`) in `DJANGO_CSRF_TRUSTED_ORIGINS`.
5. Start with the `public` profile (see below). The app is live at that URL.

Keep `DJANGO_SECURE_SSL_REDIRECT=False` — Tailscale already serves HTTPS upstream.
Find your exact URL after start with
`docker compose -f docker-compose.prod.yml exec tailscale tailscale funnel status`.

### Alternative: Cloudflare Tunnel (needs a domain)

If you already own a domain, [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
is another outbound-only option with free HTTPS. Add a `cloudflared` service
(`image: cloudflare/cloudflared:latest`, `command: tunnel --no-autoupdate run`,
`environment: TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN}`), create the tunnel in the
Cloudflare Zero Trust dashboard, point its public hostname at `http://frontend:80`,
and set that hostname in `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS`.

### Other options

You can also terminate TLS at nginx here (add a `listen 443 ssl;` block with your
certs and publish `443`) or front the stack with Caddy / Traefik.

## 4. Launch

With the public tunnel (Tailscale Funnel):

```sh
docker compose -f docker-compose.prod.yml --profile public up --build -d
```

Without the tunnel (LAN only / testing), drop the profile:

```sh
docker compose -f docker-compose.prod.yml up --build -d
```

The `backend` service migrates the database and collects static on start. Create
your admin user once:

```sh
docker compose -f docker-compose.prod.yml exec backend \
    uv run python ticktask/manage.py createsuperuser
```

New users sign up at `/#/signup` and you approve them from the Django admin
(`/admin/`, model **User access requests**) or from the Telegram approve/reject
buttons.

## 5. Operate

```sh
# Logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f bot

# Update to a new version
git pull
docker compose -f docker-compose.prod.yml up --build -d

# Verify Django's production checklist (should report no issues)
docker compose -f docker-compose.prod.yml exec backend \
    uv run python ticktask/manage.py check --deploy
```

### Backups

All state is the SQLite database on the `app-data` volume. Back it up with:

```sh
docker compose -f docker-compose.prod.yml exec backend \
    sh -c "uv run python ticktask/manage.py dumpdata --natural-primary --natural-foreign > /data/backup.json"
```

or just copy `/data/db.sqlite3` from the volume while the stack is stopped.

## Notes & limits

- **SQLite** is fine for a small private deployment but serializes writes. If the
  user base or concurrency grows, switch `DATABASES` to PostgreSQL (add a `db`
  service and point `DJANGO_DB_PATH`'s replacement at it).
- The bot runs by **long-polling**, so no public webhook is required. To use a
  webhook instead, set `TELEGRAM_USE_WEBHOOK=True` + `TELEGRAM_WEBHOOK_SECRET`,
  drop the `bot` service, proxy `/api/telegram/webhook/` to the backend, and run
  `manage.py set_telegram_webhook --url https://your-domain`.
- The Django **cache** (bot conversation state) points at Redis in production so
  it survives restarts and is shared across workers.
