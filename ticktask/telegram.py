"""
Telegram bot integration: sending messages and handling incoming bot updates
for account linking. All HTTP goes through ``_request`` so it can be stubbed in
tests. The bot is a single app-wide credential (``TELEGRAM_BOT_TOKEN``); who to
message is stored per user as a ``chat_id`` (see ``UserTelegramSettings``).
"""

import json
import logging
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_API_URL = "https://api.telegram.org/bot{token}/{method}"
LINK_TOKEN_TTL_MINUTES = 15


def is_configured() -> bool:
    """Whether a bot token is available."""
    return bool(settings.TELEGRAM_BOT_TOKEN)


def _request(method: str, payload: dict) -> dict:
    """POSTs ``payload`` to a Bot API ``method`` and returns the parsed JSON."""
    url = _API_URL.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        return json.loads(response.read().decode())


def send_message(chat_id, text: str) -> None:
    """Sends a text message to a chat. Raises if the bot isn't configured."""
    if not is_configured():
        raise RuntimeError("Telegram bot is not configured (TELEGRAM_BOT_TOKEN).")
    _request("sendMessage", {"chat_id": chat_id, "text": text})


def get_updates(offset=None, timeout: int = 25) -> list:
    """Long-polls the Bot API for new updates."""
    payload = {"timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    return _request("getUpdates", payload).get("result", [])


def set_webhook(url: str) -> dict:
    """Registers ``url`` as the bot's webhook."""
    return _request("setWebhook", {"url": url})


def delete_webhook() -> dict:
    """Removes any configured webhook."""
    return _request("deleteWebhook", {})


def deep_link(token: str) -> str:
    """Builds the ``t.me`` deep link that starts the bot with a link token."""
    return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}"


def process_update(update: dict) -> None:
    """
    Handles an incoming bot update. A ``/start <token>`` message links the
    sending chat to the account that issued ``token``.
    """
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not chat_id or not text.startswith("/start"):
        return

    parts = text.split(maxsplit=1)
    token = parts[1].strip() if len(parts) > 1 else ""
    if not token:
        _safe_send(
            chat_id, "Open the link from TickTask settings to connect your account."
        )
        return
    _link_account(chat_id, token)


def _link_account(chat_id, token: str) -> None:
    """Links ``chat_id`` to the account holding an unexpired ``token``."""
    from ticktask.models import UserTelegramSettings  # pylint: disable=import-outside-toplevel

    cutoff = timezone.now() - timedelta(minutes=LINK_TOKEN_TTL_MINUTES)
    row = UserTelegramSettings.objects.filter(  # pylint: disable=no-member
        link_token=token, link_token_created_at__gte=cutoff
    ).first()
    if row is None:
        _safe_send(
            chat_id,
            "That link is invalid or has expired. Generate a new one in TickTask settings.",
        )
        return

    row.chat_id = str(chat_id)
    row.connected_at = timezone.now()
    row.link_token = None
    row.link_token_created_at = None
    row.save(
        update_fields=["chat_id", "connected_at", "link_token", "link_token_created_at"]
    )
    _safe_send(
        chat_id, "✅ Connected to TickTask. You'll get your event reminders here."
    )


def _safe_send(chat_id, text: str) -> None:
    """Best-effort send that never raises (used inside update handling)."""
    try:
        send_message(chat_id, text)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to send Telegram message to %s", chat_id)
