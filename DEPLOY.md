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
- `FRONTEND_URL` / `GOOGLE_CALENDAR_CLIENT_ID` / `GOOGLE_CALENDAR_CLIENT_SECRET`
  / `GOOGLE_CALENDAR_REDIRECT_URI` — if enabling Google Calendar sync (optional,
  see below).

`.env` holds secrets — keep it off version control (it's git-ignored).

### Google Calendar sync (optional)

Lets each user connect their own Google Calendar from **Settings** in the app;
non-recurring events then sync both ways automatically (see
`ticktask/google_calendar.py` for what's in scope — recurring events aren't
synced yet). Skip this whole section to leave the feature off — it stays
hidden with a "not configured" response until these are set.

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a
   project (or reuse one) and enable the **Google Calendar API** (APIs &
   Services → Library).
2. **OAuth consent screen** (APIs & Services → OAuth consent screen): choose
   **External**, fill in the required fields, and add your own Google account
   under **Test users** (the app stays in "Testing" mode — fine for a private,
   single/few-user deployment, no Google review needed).
3. **Credentials** (APIs & Services → Credentials → **Create credentials** →
   **OAuth client ID**): application type **Web application**. Under
   **Authorized redirect URIs**, add
   `https://<your-public-url>/api/google-calendar/oauth/callback/` (the same
   host as `DJANGO_ALLOWED_HOSTS`, with `https://` and that exact path).
4. Copy the generated **Client ID** and **Client secret** into `.env`:
   `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`. Set
   `GOOGLE_CALENDAR_REDIRECT_URI` to the same URL you registered in step 3, and
   `FRONTEND_URL` to your public URL (no trailing path) — it's where the OAuth
   callback sends the browser back to.
5. Restart the stack (`docker compose -f docker-compose.prod.yml up --build -d`)
   so the backend picks up the new env vars, then connect from **Settings** in
   the app.

The `beat` service polls each connected account every 5 minutes (task
`ticktask.tasks.sync_google_calendar`) — no public webhook/push subscription
needed.

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

## 6. Continuous deployment (optional)

`.github/workflows/deploy.yml` deploys automatically on every push to `main`
(i.e. when a PR is merged): it runs the full test suite on GitHub-hosted runners
and, **only if everything passes**, tells a **self-hosted runner on the home server**
to pull `main` and rebuild the stack, then health-checks the app and pings
Telegram with the outcome.

The runner connects **outbound** to GitHub, so there are no open ports and
nothing to expose — the same reason the rest of the stack is outbound-only. It is
independent from the Tailscale SSH access; you don't need SSH for deploys.

### One-time setup on the home server

1. **Deploy from a git clone.** The runner deploys *in place* from an existing
   clone that holds the real `.env` and owns the running Docker volumes (so your
   database is preserved). If you already deploy by `git pull` from a directory,
   use that one. Otherwise clone the repo and do the first manual launch (steps
   2–4) there.

2. **Install the runner.** In GitHub: **repo → Settings → Actions → Runners →
   New self-hosted runner** (Linux/x64). Follow the shown `download` + `config.sh`
   commands on the home server; when `config.sh` asks for labels, add **`ticktask`**
   (the workflow targets `runs-on: [self-hosted, ticktask]`). Run it as a
   service so it survives reboots:

   ```sh
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

   The runner's user must be able to run Docker without sudo:

   ```sh
   sudo usermod -aG docker "$USER"   # then re-login (or reboot) so it takes effect
   ```

3. **Point the workflow at your deploy directory.** In GitHub: **repo → Settings
   → Secrets and variables → Actions → Variables → New repository variable**,
   name `DEPLOY_DIR`, value the absolute path of the clone from step 1 (e.g.
   `/home/david/Escritorio/deploy/TickTask`).

4. **(Optional) Telegram deploy alerts.** Add two **repository secrets** (same
   screen, *Secrets* tab): `TELEGRAM_BOT_TOKEN` (your bot token) and
   `TELEGRAM_ALERT_CHAT_ID` (the chat to notify — your own chat id; it's stored on
   your `UserTelegramSettings` row in the Django admin once you've linked the
   bot). If either is missing, the notify step is simply skipped.

### How a deploy runs

On merge to `main`: tests run → if green, the runner does
`git fetch && git reset --hard origin/main` in `DEPLOY_DIR` and
`docker compose -f docker-compose.prod.yml --profile public up --build -d`
(migrations + `collectstatic` still run on backend start), waits for
`http://localhost/api/openapi.json` to answer, prunes dangling images, and
reports success/failure to Telegram. Watch it under the repo's **Actions** tab.

That health check reaches the backend with a `localhost` Host header, so keep
`localhost` / `127.0.0.1` in `DJANGO_ALLOWED_HOSTS` (see `.env.prod.example`) or
it will be rejected with a 400 and the deploy will be marked failed even though
the app is up.

You can still deploy manually any time with the `git pull` + `up --build -d`
commands in section 5 — the CD just automates exactly that.

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
