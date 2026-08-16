"""
Thin client for Google's OAuth2 + Calendar v3 REST API, used to sync
``CalendarEvent`` rows with a user's Google Calendar (see ``ticktask.tasks
.sync_google_calendar`` for the actual sync logic, and
``ticktask.server.routes.google_calendar`` for the connect/disconnect
endpoints).

Uses ``urllib.request`` directly rather than a client library, the same
convention already used for the Telegram Bot API in ``ticktask/telegram.py``
— no new HTTP dependency for a handful of calls.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone as dj_timezone

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API_BASE = "https://www.googleapis.com/calendar/v3"
SCOPE = "https://www.googleapis.com/auth/calendar.events"

# Refresh the access token a bit early to avoid racing its real expiry.
_EXPIRY_MARGIN = timedelta(seconds=60)


def is_configured() -> bool:
    """Whether an OAuth client is set up for this deployment."""
    return bool(
        settings.GOOGLE_CALENDAR_CLIENT_ID and settings.GOOGLE_CALENDAR_CLIENT_SECRET
    )


def build_auth_url(state: str) -> str:
    """Builds the Google consent-screen URL to send the user to."""
    params = {
        "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        # Forces Google to (re-)issue a refresh token even on a repeat consent.
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def _token_request(payload: dict) -> dict:
    data = urllib.parse.urlencode(payload).encode()
    request = urllib.request.Request(TOKEN_URL, data=data)
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        return json.loads(response.read().decode())


def exchange_code(code: str) -> dict:
    """Exchanges an OAuth ``code`` for an access/refresh token pair."""
    return _token_request(
        {
            "code": code,
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    )


def refresh_access_token(refresh_token: str) -> dict:
    """Trades a stored refresh token for a fresh access token."""
    return _token_request(
        {
            "refresh_token": refresh_token,
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "grant_type": "refresh_token",
        }
    )


def revoke(token: str) -> None:
    """Revokes a token with Google. Best-effort — an already-invalid token is fine."""
    data = urllib.parse.urlencode({"token": token}).encode()
    request = urllib.request.Request(REVOKE_URL, data=data)
    try:
        urllib.request.urlopen(request, timeout=15)  # nosec B310
    except urllib.error.HTTPError:
        pass


def get_valid_access_token(account) -> str:
    """Returns a usable access token for ``account``, refreshing it if needed."""
    if (
        account.access_token
        and account.token_expiry
        and account.token_expiry > dj_timezone.now() + _EXPIRY_MARGIN
    ):
        return account.access_token
    token_data = refresh_access_token(account.refresh_token)
    account.access_token = token_data["access_token"]
    account.token_expiry = dj_timezone.now() + timedelta(
        seconds=token_data.get("expires_in", 3600)
    )
    account.save(update_fields=["access_token", "token_expiry"])
    return account.access_token


def _api_request(
    method: str,
    path: str,
    access_token: str,
    payload: dict | None = None,
    params: dict | None = None,
):
    url = f"{API_BASE}{path}"
    if params:
        url += f"?{urllib.parse.urlencode(params)}"
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        body = response.read()
        return json.loads(body.decode()) if body else None


def _event_body(event) -> dict:
    """Shapes a ``CalendarEvent`` into a Google Calendar event body."""
    body = {
        "summary": event.title,
        "description": event.description,
        # Tags the event as TickTask's so a later pull can recognize its own
        # echo instead of importing a duplicate (see ``tasks._apply_google_event``).
        "extendedProperties": {"private": {"ticktask_event_id": str(event.id)}},
    }
    if event.all_day:
        end_date = (event.end or event.start + timedelta(days=1)).date()
        body["start"] = {"date": event.start.date().isoformat()}
        body["end"] = {"date": end_date.isoformat()}
    else:
        end = event.end or event.start + timedelta(hours=1)
        body["start"] = {"dateTime": event.start.isoformat()}
        body["end"] = {"dateTime": end.isoformat()}
    return body


def push_event(account, event) -> str:
    """Creates or updates ``event`` in Google Calendar. Returns its Google event id."""
    access_token = get_valid_access_token(account)
    body = _event_body(event)
    if event.google_event_id:
        result = _api_request(
            "PATCH",
            f"/calendars/{account.calendar_id}/events/{event.google_event_id}",
            access_token,
            payload=body,
        )
    else:
        result = _api_request(
            "POST",
            f"/calendars/{account.calendar_id}/events",
            access_token,
            payload=body,
        )
    return result["id"]


def delete_event(account, google_event_id: str) -> None:
    """Deletes a Google Calendar event. Already-gone (404/410) is not an error."""
    access_token = get_valid_access_token(account)
    try:
        _api_request(
            "DELETE",
            f"/calendars/{account.calendar_id}/events/{google_event_id}",
            access_token,
        )
    except urllib.error.HTTPError as exc:
        if exc.code not in (404, 410):
            raise


def list_changes(account) -> tuple[list[dict], str | None]:
    """
    Returns ``(events, next_sync_token)`` for ``account``. Uses Google's
    incremental sync (``syncToken``) once one is stored; otherwise does an
    initial sync from now. If the stored token has expired
    (``HTTP 410 Gone``), returns ``([], None)`` — the caller should clear it
    and retry once (see ``tasks._pull_for_account``).
    """
    access_token = get_valid_access_token(account)
    params = {"singleEvents": "true", "showDeleted": "true", "maxResults": "250"}
    if account.sync_token:
        params["syncToken"] = account.sync_token
    else:
        params["timeMin"] = dj_timezone.now().isoformat()

    events: list[dict] = []
    next_sync_token = None
    page_token = None
    while True:
        page_params = dict(params)
        if page_token:
            page_params["pageToken"] = page_token
        try:
            result = _api_request(
                "GET",
                f"/calendars/{account.calendar_id}/events",
                access_token,
                params=page_params,
            )
        except urllib.error.HTTPError as exc:
            if exc.code == 410:
                return [], None
            raise
        events.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            next_sync_token = result.get("nextSyncToken")
            break
    return events, next_sync_token


def parse_google_datetime(value: dict):
    """Parses a Google event's ``start``/``end`` object into an aware datetime."""
    if not value:
        return None
    if "dateTime" in value:
        parsed = datetime.fromisoformat(value["dateTime"])
        if dj_timezone.is_naive(parsed):
            parsed = dj_timezone.make_aware(parsed)
        return parsed
    if "date" in value:
        naive = datetime.combine(datetime.fromisoformat(value["date"]).date(), time.min)
        return dj_timezone.make_aware(naive, dj_timezone.get_default_timezone())
    return None
