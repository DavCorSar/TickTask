"""
Tests for the Google Calendar integration: the per-user connect/status/
disconnect endpoints, and the periodic ``sync_google_calendar`` task. The
Google API layer (``ticktask.google_calendar``) is stubbed throughout so no
network calls are made.
"""

import json

import pytest
from django.core import signing
from django.test import Client
from django.utils import timezone
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

from ticktask import google_calendar
from ticktask.models import (
    CalendarEvent,
    GoogleCalendarAccount,
    GoogleCalendarPendingDeletion,
)
from ticktask.tasks import sync_google_calendar

BASE = "/api/google-calendar"


@pytest.fixture(autouse=True)
def google_config(settings):
    """Provides a configured OAuth client for the tests."""
    settings.GOOGLE_CALENDAR_CLIENT_ID = "client-id"
    settings.GOOGLE_CALENDAR_CLIENT_SECRET = "client-secret"
    settings.GOOGLE_CALENDAR_REDIRECT_URI = "http://testserver/api/google-calendar/oauth/callback/"
    settings.FRONTEND_URL = "http://testserver"
    return settings


def make_user(username: str = "alice") -> User:
    return User.objects.create_user(username=username, password="pw")


def auth_client(user: User) -> Client:
    token = str(RefreshToken.for_user(user).access_token)
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


def post(client, path, payload=None):
    return client.post(
        path,
        data=json.dumps(payload or {}),
        content_type="application/json",
    )


def make_account(user, **kwargs) -> GoogleCalendarAccount:
    defaults = {"refresh_token": "refresh-token", "connected_at": timezone.now()}
    defaults.update(kwargs)
    return GoogleCalendarAccount.objects.create(user=user, **defaults)  # pylint: disable=no-member


def make_event(user, start=None, **kwargs) -> CalendarEvent:
    kwargs.setdefault("title", "Meeting")
    return CalendarEvent.objects.create(  # pylint: disable=no-member
        user=user, start=start or timezone.now(), **kwargs
    )


# --------------------------------------------------------------------------- #
# Connect / status / disconnect endpoints
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_status_defaults_to_not_connected():
    body = auth_client(make_user()).get(f"{BASE}/status/").json()
    assert body["connected"] is False
    assert body["calendar_id"] == "primary"


@pytest.mark.django_db
def test_connect_returns_auth_url_with_signed_state():
    user = make_user()
    resp = post(auth_client(user), f"{BASE}/connect/")
    assert resp.status_code == 200
    auth_url = resp.json()["auth_url"]
    assert auth_url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=client-id" in auth_url


@pytest.mark.django_db
def test_connect_rejects_when_not_configured(settings):
    settings.GOOGLE_CALENDAR_CLIENT_ID = ""
    resp = post(auth_client(make_user()), f"{BASE}/connect/")
    assert resp.status_code == 503


@pytest.mark.django_db
def test_oauth_callback_missing_code_redirects_with_error():
    resp = Client().get(f"{BASE}/oauth/callback/")
    assert resp.status_code == 302
    assert resp.url == "http://testserver/#/settings?google_calendar=error"


@pytest.mark.django_db
def test_oauth_callback_bad_state_redirects_with_error():
    resp = Client().get(f"{BASE}/oauth/callback/?code=abc&state=tampered")
    assert resp.status_code == 302
    assert "google_calendar=error" in resp.url


@pytest.mark.django_db
def test_oauth_callback_success_stores_tokens_and_redirects(monkeypatch):
    user = make_user()
    monkeypatch.setattr(
        google_calendar,
        "exchange_code",
        lambda code: {
            "access_token": "access-123",
            "refresh_token": "refresh-123",
            "expires_in": 3600,
        },
    )
    state = signing.dumps({"user_id": user.id}, salt="google-calendar-oauth")

    resp = Client().get(f"{BASE}/oauth/callback/?code=abc&state={state}")

    assert resp.status_code == 302
    assert resp.url == "http://testserver/#/settings?google_calendar=connected"
    account = GoogleCalendarAccount.objects.get(user=user)  # pylint: disable=no-member
    assert account.access_token == "access-123"
    assert account.refresh_token == "refresh-123"
    assert account.connected is True


@pytest.mark.django_db
def test_disconnect_clears_tokens(monkeypatch):
    user = make_user()
    make_account(user)
    revoked = []
    monkeypatch.setattr(google_calendar, "revoke", lambda token: revoked.append(token))

    resp = post(auth_client(user), f"{BASE}/disconnect/")

    assert resp.status_code == 200
    assert resp.json()["connected"] is False
    assert revoked == ["refresh-token"]
    account = GoogleCalendarAccount.objects.get(user=user)  # pylint: disable=no-member
    assert account.refresh_token == ""


@pytest.mark.django_db
def test_delete_event_leaves_tombstone_when_synced():
    user = make_user()
    account = make_account(user)
    event = make_event(user, google_event_id="g-1")

    resp = auth_client(user).delete(f"/api/calendar/user/delete-event/{event.id}/")

    assert resp.status_code == 200
    assert not CalendarEvent.objects.filter(id=event.id).exists()  # pylint: disable=no-member
    tombstone = GoogleCalendarPendingDeletion.objects.get(  # pylint: disable=no-member
        account=account
    )
    assert tombstone.google_event_id == "g-1"


@pytest.mark.django_db
def test_delete_event_without_google_sync_leaves_no_tombstone():
    user = make_user()
    make_account(user)
    event = make_event(user)  # never synced — no google_event_id

    auth_client(user).delete(f"/api/calendar/user/delete-event/{event.id}/")

    assert GoogleCalendarPendingDeletion.objects.count() == 0  # pylint: disable=no-member


# --------------------------------------------------------------------------- #
# sync_google_calendar task
# --------------------------------------------------------------------------- #


@pytest.fixture
def stub_google(monkeypatch):
    """Stubs the Google Calendar API client so no network calls are made."""
    pushed = []
    deleted = []

    def fake_push_event(account, event):
        pushed.append(event.id)
        return f"g-{event.id}"

    def fake_delete_event(account, google_event_id):
        deleted.append(google_event_id)

    monkeypatch.setattr(google_calendar, "push_event", fake_push_event)
    monkeypatch.setattr(google_calendar, "delete_event", fake_delete_event)
    monkeypatch.setattr(google_calendar, "list_changes", lambda account: ([], ""))
    return {"pushed": pushed, "deleted": deleted}


@pytest.mark.django_db
def test_sync_pushes_new_local_events(stub_google):
    user = make_user()
    make_account(user)
    event = make_event(user)

    sync_google_calendar()

    assert stub_google["pushed"] == [event.id]
    event.refresh_from_db()
    assert event.google_event_id == f"g-{event.id}"


@pytest.mark.django_db
def test_sync_skips_recurring_events(stub_google):
    user = make_user()
    make_account(user)
    make_event(user, recurrence=CalendarEvent.WEEKLY)

    sync_google_calendar()

    assert stub_google["pushed"] == []


@pytest.mark.django_db
def test_sync_does_not_repush_unchanged_synced_event(stub_google):
    user = make_user()
    make_event(user, google_event_id="g-existing")
    # Sync cursor set after the event's last write, so it isn't seen as changed.
    account = make_account(user, last_synced_at=timezone.now())

    sync_google_calendar()

    assert stub_google["pushed"] == []
    account.refresh_from_db()
    assert account.last_synced_at is not None


@pytest.mark.django_db
def test_sync_applies_pending_deletions(stub_google):
    user = make_user()
    account = make_account(user)
    GoogleCalendarPendingDeletion.objects.create(  # pylint: disable=no-member
        account=account, google_event_id="g-gone"
    )

    sync_google_calendar()

    assert stub_google["deleted"] == ["g-gone"]
    assert GoogleCalendarPendingDeletion.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_sync_pulls_new_remote_event(stub_google, monkeypatch):
    user = make_user()
    make_account(user)
    remote_event = {
        "id": "g-remote-1",
        "status": "confirmed",
        "summary": "Dentist",
        "description": "",
        "start": {"dateTime": "2026-09-01T10:00:00+00:00"},
        "end": {"dateTime": "2026-09-01T11:00:00+00:00"},
    }
    monkeypatch.setattr(
        google_calendar, "list_changes", lambda account: ([remote_event], "next-token")
    )

    sync_google_calendar()

    created = CalendarEvent.objects.get(google_event_id="g-remote-1")  # pylint: disable=no-member
    assert created.title == "Dentist"
    assert created.all_day is False


@pytest.mark.django_db
def test_sync_skips_recurring_remote_events(stub_google, monkeypatch):
    user = make_user()
    make_account(user)
    remote_event = {
        "id": "g-remote-recurring",
        "status": "confirmed",
        "summary": "Standup",
        "recurrence": ["RRULE:FREQ=DAILY"],
        "start": {"dateTime": "2026-09-01T10:00:00+00:00"},
        "end": {"dateTime": "2026-09-01T10:15:00+00:00"},
    }
    monkeypatch.setattr(
        google_calendar, "list_changes", lambda account: ([remote_event], "next-token")
    )

    sync_google_calendar()

    assert not CalendarEvent.objects.filter(  # pylint: disable=no-member
        google_event_id="g-remote-recurring"
    ).exists()


@pytest.mark.django_db
def test_sync_deletes_local_event_on_remote_cancellation(stub_google, monkeypatch):
    user = make_user()
    event = make_event(user, google_event_id="g-cancelled")
    # Sync cursor set after the event's last write, so the push step leaves
    # its google_event_id alone (this test is only about the pull side).
    make_account(user, last_synced_at=timezone.now())
    cancelled = {"id": "g-cancelled", "status": "cancelled"}
    monkeypatch.setattr(
        google_calendar, "list_changes", lambda account: ([cancelled], "next-token")
    )

    sync_google_calendar()

    assert not CalendarEvent.objects.filter(id=event.id).exists()  # pylint: disable=no-member


@pytest.mark.django_db
def test_sync_skips_disconnected_accounts(stub_google):
    user = make_user()
    make_account(user, refresh_token="")
    make_event(user)

    sync_google_calendar()

    assert stub_google["pushed"] == []


@pytest.mark.django_db
def test_per_event_push_failure_does_not_stop_the_rest(stub_google, monkeypatch):
    """One event failing to push is logged and skipped, not fatal to the sync."""
    user = make_user()
    make_account(user)
    bad_event = make_event(user, title="Bad")
    good_event = make_event(user, title="Good")

    def flaky_push(account, event):
        if event.id == bad_event.id:
            raise RuntimeError("boom")
        return f"g-{event.id}"

    monkeypatch.setattr(google_calendar, "push_event", flaky_push)

    synced = sync_google_calendar()

    assert synced == 1
    bad_event.refresh_from_db()
    good_event.refresh_from_db()
    assert bad_event.google_event_id == ""
    assert good_event.google_event_id == f"g-{good_event.id}"


@pytest.mark.django_db
def test_sync_continues_after_one_account_fails(stub_google, monkeypatch):
    """An account-level failure (e.g. an expired grant) doesn't block others."""
    user_a = make_user("alice")
    user_b = make_user("bob")
    make_account(user_a)
    make_account(user_b)
    make_event(user_b)

    def failing_list_changes(account):
        if account.user_id == user_a.id:
            raise RuntimeError("token revoked")
        return [], "next-token"

    monkeypatch.setattr(google_calendar, "list_changes", failing_list_changes)

    synced = sync_google_calendar()

    assert synced == 1
