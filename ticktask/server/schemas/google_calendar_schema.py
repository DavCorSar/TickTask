"""
Definition of the schemas used for the Google Calendar integration.
"""

from datetime import datetime

from ninja import Schema


class GoogleCalendarStatusSchema(Schema):
    """
    The authenticated user's Google Calendar connection status.
    """

    connected: bool
    calendar_id: str
    connected_at: datetime | None = None
    last_synced_at: datetime | None = None


class GoogleCalendarAuthUrlSchema(Schema):
    """
    The consent-screen URL the frontend should redirect the browser to.
    """

    auth_url: str
