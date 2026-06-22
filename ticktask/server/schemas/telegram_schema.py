"""
Schemas for the per-user Telegram settings endpoints.
"""

from ninja import Schema


class TelegramSettingsSchema(Schema):
    """Current Telegram reminder settings and connection status for the user."""

    enabled: bool
    reminder_lead_minutes: int
    connected: bool
    bot_username: str


class TelegramSettingsUpdateSchema(Schema):
    """Editable Telegram reminder preferences."""

    enabled: bool
    reminder_lead_minutes: int


class TelegramLinkSchema(Schema):
    """The deep link the user opens to connect their Telegram chat."""

    deep_link: str
