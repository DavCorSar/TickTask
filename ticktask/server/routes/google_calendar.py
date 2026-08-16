"""
Endpoints for the Google Calendar integration: starting/finishing the OAuth
connection, checking status, and disconnecting. The actual event sync (both
directions) runs in the periodic ``sync_google_calendar`` Celery task (see
``ticktask/tasks.py`` and ``ticktask/google_calendar.py``) — these routes only
manage the per-user connection itself.
"""

import os
import urllib.error
import logging
from datetime import timedelta

import django
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.google_calendar_schema import (
    GoogleCalendarStatusSchema,
    GoogleCalendarAuthUrlSchema,
)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
except RuntimeError:
    pass

from django.conf import settings
from django.core import signing
from django.http import HttpResponseRedirect
from django.utils import timezone

from ticktask import google_calendar
from ticktask.models import GoogleCalendarAccount

logger = logging.getLogger(__name__)

google_calendar_router = Router()

_STATE_SALT = "google-calendar-oauth"
# Long enough to get through the Google consent screen, short enough that a
# stale/replayed callback link stops working.
_STATE_MAX_AGE = 600
# The SPA uses a hash-mode router (see gui/nuxt.config.ts), so the query string
# has to live inside the `#/...` fragment to reach the settings page.
_SETTINGS_PATH = "/#/settings"


def _settings_redirect(status_value: str) -> HttpResponseRedirect:
    """Redirects the browser back to the SPA's settings page."""
    frontend = settings.FRONTEND_URL.rstrip("/")
    return HttpResponseRedirect(
        f"{frontend}{_SETTINGS_PATH}?google_calendar={status_value}"
    )


def _get_account(user) -> GoogleCalendarAccount:
    """Returns the user's Google Calendar account row, creating it on first access."""
    row, _ = GoogleCalendarAccount.objects.get_or_create(user=user)  # pylint: disable=no-member
    return row


def _serialize(row: GoogleCalendarAccount) -> dict:
    return {
        "connected": row.connected,
        "calendar_id": row.calendar_id,
        "connected_at": row.connected_at,
        "last_synced_at": row.last_synced_at,
    }


@google_calendar_router.get(
    "/status/",
    response=GoogleCalendarStatusSchema,
    tags=["Google Calendar"],
    auth=JWTAuth(),
)
def status(request):
    """Returns the authenticated user's Google Calendar connection status."""
    return _serialize(_get_account(request.auth))


@google_calendar_router.post(
    "/connect/",
    response=GoogleCalendarAuthUrlSchema,
    tags=["Google Calendar"],
    auth=JWTAuth(),
)
def connect(request):
    """Returns the Google consent-screen URL the frontend should redirect to."""
    if not google_calendar.is_configured():
        raise HttpError(503, "Google Calendar is not configured on the server.")
    state = signing.dumps({"user_id": request.auth.id}, salt=_STATE_SALT)
    return {"auth_url": google_calendar.build_auth_url(state)}


@google_calendar_router.get("/oauth/callback/", tags=["Google Calendar"])
def oauth_callback(request, code: str = "", state: str = "", error: str = ""):
    """
    Public redirect target Google sends the browser back to after the consent
    screen — not JWT-authed, since the browser lands here directly rather than
    the SPA calling it. The signed ``state`` (minted by ``connect`` above) is
    what ties this callback back to the user who started the flow.
    """
    if error or not code or not state:
        return _settings_redirect("error")
    try:
        payload = signing.loads(state, salt=_STATE_SALT, max_age=_STATE_MAX_AGE)
    except signing.BadSignature:
        return _settings_redirect("error")

    try:
        tokens = google_calendar.exchange_code(code)
    except urllib.error.HTTPError:
        logger.exception("Google Calendar token exchange failed")
        return _settings_redirect("error")

    account, _ = GoogleCalendarAccount.objects.get_or_create(  # pylint: disable=no-member
        user_id=payload["user_id"]
    )
    account.access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    if refresh_token:
        # Google only issues a refresh token on the first consent (or when
        # `prompt=consent` forces a re-grant) — keep the existing one otherwise.
        account.refresh_token = refresh_token
    account.token_expiry = timezone.now() + timedelta(
        seconds=tokens.get("expires_in", 3600)
    )
    account.connected_at = timezone.now()
    account.sync_token = ""  # force a fresh full sync on the next periodic run
    account.save()
    return _settings_redirect("connected")


@google_calendar_router.post(
    "/disconnect/",
    response=GoogleCalendarStatusSchema,
    tags=["Google Calendar"],
    auth=JWTAuth(),
)
def disconnect(request):
    """Revokes and clears the user's Google Calendar connection."""
    account = _get_account(request.auth)
    if account.refresh_token:
        google_calendar.revoke(account.refresh_token)
    account.access_token = ""
    account.refresh_token = ""
    account.token_expiry = None
    account.connected_at = None
    account.sync_token = ""
    account.save()
    return _serialize(account)
