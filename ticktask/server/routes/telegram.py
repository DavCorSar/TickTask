"""
Endpoints for per-user Telegram settings: reading/updating reminder
preferences, linking/unlinking a Telegram chat, sending a test message, and the
public webhook that receives bot updates.
"""

import os
import json
import secrets

import django
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.telegram_schema import (
    TelegramSettingsSchema,
    TelegramSettingsUpdateSchema,
    TelegramLinkSchema,
)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
except RuntimeError:
    pass

from zoneinfo import available_timezones

from django.conf import settings
from django.utils import timezone
from ticktask import telegram
from ticktask.models import UserTelegramSettings

telegram_router = Router()


def _get_settings(user) -> UserTelegramSettings:
    """Returns the user's Telegram settings row, creating it on first access."""
    row, _ = UserTelegramSettings.objects.get_or_create(user=user)  # pylint: disable=no-member
    return row


def _validate_timezone(name: str) -> None:
    """Ensures ``name`` is a known IANA timezone (or empty, meaning UTC)."""
    if name and name not in available_timezones():
        raise HttpError(422, "Unknown timezone.")


def _serialize(row: UserTelegramSettings) -> dict:
    """Shapes a settings row into the response payload."""
    return {
        "enabled": row.enabled,
        "reminder_lead_minutes": row.reminder_lead_minutes,
        "timezone": row.timezone,
        "connected": row.connected,
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
    }


@telegram_router.get(
    "/settings/",
    response=TelegramSettingsSchema,
    tags=["Telegram"],
    auth=JWTAuth(),
)
def get_settings(request):
    """Returns the user's Telegram reminder settings and connection status."""
    return _serialize(_get_settings(request.auth))


@telegram_router.post(
    "/settings/",
    response=TelegramSettingsSchema,
    tags=["Telegram"],
    auth=JWTAuth(),
)
def update_settings(request, data: TelegramSettingsUpdateSchema):
    """Updates the user's reminder preferences."""
    _validate_timezone(data.timezone)
    row = _get_settings(request.auth)
    row.enabled = data.enabled
    row.reminder_lead_minutes = data.reminder_lead_minutes
    row.timezone = data.timezone
    row.save(update_fields=["enabled", "reminder_lead_minutes", "timezone"])
    return _serialize(row)


@telegram_router.post(
    "/link/",
    response=TelegramLinkSchema,
    tags=["Telegram"],
    auth=JWTAuth(),
)
def start_link(request):
    """
    Issues a one-time token and returns the deep link the user opens to connect
    their Telegram chat to this account.
    """
    if not telegram.is_configured() or not settings.TELEGRAM_BOT_USERNAME:
        raise HttpError(503, "Telegram bot is not configured on the server.")

    row = _get_settings(request.auth)
    row.link_token = secrets.token_urlsafe(16)
    row.link_token_created_at = timezone.now()
    row.save(update_fields=["link_token", "link_token_created_at"])
    return {"deep_link": telegram.deep_link(row.link_token)}


@telegram_router.post(
    "/unlink/",
    response=TelegramSettingsSchema,
    tags=["Telegram"],
    auth=JWTAuth(),
)
def unlink(request):
    """Disconnects the user's Telegram chat."""
    row = _get_settings(request.auth)
    row.chat_id = None
    row.connected_at = None
    row.save(update_fields=["chat_id", "connected_at"])
    return _serialize(row)


@telegram_router.post(
    "/test/",
    response={200: dict},
    tags=["Telegram"],
    auth=JWTAuth(),
)
def send_test(request):
    """Sends a test message to the user's linked Telegram chat."""
    row = _get_settings(request.auth)
    if not row.connected:
        raise HttpError(409, "Connect your Telegram first.")
    try:
        telegram.send_message(
            row.chat_id,
            "🔔 Test reminder from TickTask — notifications are working!",
        )
    except Exception as exc:  # pylint: disable=broad-except
        raise HttpError(
            502, "Couldn't reach Telegram. Please try again later."
        ) from exc
    return {"success": True}


@telegram_router.post("/webhook/{secret}/", tags=["Telegram"])
def webhook(request, secret: str):
    """
    Public endpoint that receives bot updates when running in webhook mode. The
    ``secret`` in the path must match ``TELEGRAM_WEBHOOK_SECRET``.
    """
    if not settings.TELEGRAM_WEBHOOK_SECRET or not secrets.compare_digest(
        secret, settings.TELEGRAM_WEBHOOK_SECRET
    ):
        raise HttpError(404, "Not found.")

    try:
        update = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {"ok": True}

    telegram.process_update(update)
    return {"ok": True}
