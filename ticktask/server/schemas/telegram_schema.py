"""
Schemas for the per-user Telegram settings endpoints.
"""

from ninja import Schema


class TelegramSettingsSchema(Schema):
    """Current Telegram reminder settings and connection status for the user."""

    enabled: bool
    reminder_lead_minutes: int
    timezone: str
    connected: bool
    bot_username: str


class TelegramSettingsUpdateSchema(Schema):
    """Editable Telegram reminder preferences."""

    enabled: bool
    reminder_lead_minutes: int
    # IANA timezone name (e.g. "Europe/Madrid"); "" means UTC.
    timezone: str = ""


class TelegramLinkSchema(Schema):
    """The deep link the user opens to connect their Telegram chat."""

    deep_link: str
