"""
Tests for the per-user Telegram settings endpoints and the update-handling /
account-linking logic. The Telegram HTTP layer (``telegram._request``) is
stubbed so no network calls are made.
"""

import json
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

from ticktask import telegram
from ticktask.models import UserTelegramSettings

BASE = "/api/telegram"


@pytest.fixture(autouse=True)
def stub_telegram_http(monkeypatch):
    """Stubs the Bot API HTTP layer and records the calls made."""
    calls = []

    def fake_request(method, payload):
        calls.append((method, payload))
        return {"ok": True, "result": []}

    monkeypatch.setattr(telegram, "_request", fake_request)
    return calls


@pytest.fixture(autouse=True)
def bot_config(settings):
    """Provides a configured bot for the tests."""
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    settings.TELEGRAM_BOT_USERNAME = "TickTaskBot"
    settings.TELEGRAM_WEBHOOK_SECRET = "hook-secret"
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


# --------------------------------------------------------------------------- #
# Settings endpoints
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_get_settings_returns_defaults():
    """First access returns defaults and the bot username."""
    body = auth_client(make_user()).get(f"{BASE}/settings/").json()
    assert body == {
        "enabled": True,
        "reminder_lead_minutes": 15,
        "connected": False,
        "bot_username": "TickTaskBot",
    }


@pytest.mark.django_db
def test_update_settings():
    """Preferences are updated and persisted per user."""
    user = make_user()
    resp = post(
        auth_client(user),
        f"{BASE}/settings/",
        {"enabled": False, "reminder_lead_minutes": 30},
    )
    assert resp.status_code == 200
    row = UserTelegramSettings.objects.get(user=user)  # pylint: disable=no-member
    assert row.enabled is False
    assert row.reminder_lead_minutes == 30


@pytest.mark.django_db
def test_start_link_returns_deep_link_with_token():
    """A link request stores a token and returns the matching deep link."""
    user = make_user()
    resp = post(auth_client(user), f"{BASE}/link/")
    assert resp.status_code == 200
    row = UserTelegramSettings.objects.get(user=user)  # pylint: disable=no-member
    assert row.link_token
    assert (
        resp.json()["deep_link"] == f"https://t.me/TickTaskBot?start={row.link_token}"
    )


@pytest.mark.django_db
def test_start_link_requires_configured_bot(settings):
    """Linking is unavailable when the server has no bot configured."""
    settings.TELEGRAM_BOT_TOKEN = ""
    resp = post(auth_client(make_user()), f"{BASE}/link/")
    assert resp.status_code == 503


@pytest.mark.django_db
def test_unlink_clears_connection():
    """Unlinking removes the stored chat id."""
    user = make_user()
    UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, chat_id="999", connected_at=timezone.now()
    )
    resp = post(auth_client(user), f"{BASE}/unlink/")
    assert resp.status_code == 200
    assert resp.json()["connected"] is False
    row = UserTelegramSettings.objects.get(user=user)  # pylint: disable=no-member
    assert row.chat_id is None


@pytest.mark.django_db
def test_send_test_requires_connection():
    """A test message needs a linked chat."""
    resp = post(auth_client(make_user()), f"{BASE}/test/")
    assert resp.status_code == 409


@pytest.mark.django_db
def test_send_test_sends_message(stub_telegram_http):
    """When connected, the test endpoint sends a message via the bot."""
    user = make_user()
    UserTelegramSettings.objects.create(user=user, chat_id="555")  # pylint: disable=no-member
    resp = post(auth_client(user), f"{BASE}/test/")
    assert resp.status_code == 200
    assert any(method == "sendMessage" for method, _ in stub_telegram_http)


# --------------------------------------------------------------------------- #
# Update handling / linking
# --------------------------------------------------------------------------- #


def _start_update(token, chat_id=12345):
    return {"message": {"text": f"/start {token}", "chat": {"id": chat_id}}}


@pytest.mark.django_db
def test_process_update_links_account():
    """A valid /start token links the sending chat to the account."""
    user = make_user()
    row = UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, link_token="tok123", link_token_created_at=timezone.now()
    )

    telegram.process_update(_start_update("tok123", chat_id=42))

    row.refresh_from_db()
    assert row.chat_id == "42"
    assert row.connected is True
    assert row.link_token is None


@pytest.mark.django_db
def test_process_update_ignores_invalid_token():
    """An unknown token links nothing."""
    user = make_user()
    UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, link_token="real", link_token_created_at=timezone.now()
    )

    telegram.process_update(_start_update("wrong"))

    assert UserTelegramSettings.objects.get(user=user).chat_id is None  # pylint: disable=no-member


@pytest.mark.django_db
def test_process_update_rejects_expired_token():
    """A token older than the TTL no longer links."""
    user = make_user()
    old = timezone.now() - timedelta(minutes=telegram.LINK_TOKEN_TTL_MINUTES + 1)
    UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, link_token="stale", link_token_created_at=old
    )

    telegram.process_update(_start_update("stale"))

    assert UserTelegramSettings.objects.get(user=user).chat_id is None  # pylint: disable=no-member


# --------------------------------------------------------------------------- #
# Webhook
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_webhook_rejects_wrong_secret():
    """A wrong path secret is not found."""
    resp = post(Client(), f"{BASE}/webhook/nope/", _start_update("x"))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_webhook_processes_update_with_right_secret():
    """The correct secret routes the update through the linking logic."""
    user = make_user()
    row = UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, link_token="hooktok", link_token_created_at=timezone.now()
    )

    resp = post(Client(), f"{BASE}/webhook/hook-secret/", _start_update("hooktok", 77))
    assert resp.status_code == 200
    row.refresh_from_db()
    assert row.chat_id == "77"
