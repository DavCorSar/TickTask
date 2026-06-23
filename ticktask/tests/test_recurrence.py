"""
Tests for the recurrence date math (`services.occurrences_between` /
`add_recurrence`) and for recurring events surfacing through the calendar
endpoints and the reminder scheduler.
"""

from datetime import datetime, timedelta, timezone as tz

import json
import pytest
from django.test import Client
from django.utils import timezone
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

from ticktask import services, telegram
from ticktask.tasks import send_due_event_reminders
from ticktask.models import CalendarEvent, SentReminder, UserTelegramSettings

CAL = "/api/calendar/user"


def dt(y, m, d, h=9):
    return datetime(y, m, d, h, 0, tzinfo=tz.utc)


# --------------------------------------------------------------------------- #
# Date math
# --------------------------------------------------------------------------- #


def test_weekly_occurrences_within_range():
    start = dt(2026, 7, 1)
    occ = services.occurrences_between(
        start, CalendarEvent.WEEKLY, None, dt(2026, 7, 1), dt(2026, 7, 31)
    )
    assert occ == [dt(2026, 7, 1), dt(2026, 7, 8), dt(2026, 7, 15), dt(2026, 7, 22), dt(2026, 7, 29)]


def test_weekly_occurrences_when_series_started_before_range():
    """A window after the first occurrence still lands on the right days."""
    start = dt(2026, 1, 7)  # a Wednesday
    occ = services.occurrences_between(
        start, CalendarEvent.WEEKLY, None, dt(2026, 7, 1), dt(2026, 7, 15)
    )
    assert occ == [dt(2026, 7, 1), dt(2026, 7, 8), dt(2026, 7, 15)]


def test_monthly_clamps_to_end_of_short_months():
    """Monthly from Jan 31 lands on the last valid day, anchored to the start."""
    start = dt(2026, 1, 31)
    occ = services.occurrences_between(
        start, CalendarEvent.MONTHLY, None, dt(2026, 1, 1), dt(2026, 4, 30)
    )
    assert occ == [dt(2026, 1, 31), dt(2026, 2, 28), dt(2026, 3, 31), dt(2026, 4, 30)]


def test_yearly_occurrences():
    start = dt(2024, 2, 29)  # leap day
    occ = services.occurrences_between(
        start, CalendarEvent.YEARLY, None, dt(2024, 1, 1), dt(2027, 12, 31)
    )
    # 2025/2026/2027 are not leap years → clamp to Feb 28.
    assert occ == [dt(2024, 2, 29), dt(2025, 2, 28), dt(2026, 2, 28), dt(2027, 2, 28)]


def test_recurrence_until_caps_the_series():
    start = dt(2026, 7, 1)
    occ = services.occurrences_between(
        start, CalendarEvent.WEEKLY, dt(2026, 7, 15), dt(2026, 7, 1), dt(2026, 7, 31)
    )
    assert occ == [dt(2026, 7, 1), dt(2026, 7, 8), dt(2026, 7, 15)]


def test_non_recurring_returns_itself_only_in_window():
    start = dt(2026, 7, 1)
    assert services.occurrences_between(start, "", None, dt(2026, 7, 1), dt(2026, 7, 31)) == [start]
    assert services.occurrences_between(start, "", None, dt(2026, 8, 1), dt(2026, 8, 31)) == []


# --------------------------------------------------------------------------- #
# Calendar endpoints
# --------------------------------------------------------------------------- #


def make_user(username="alice"):
    return User.objects.create_user(username=username, password="pw")


def auth_client(user):
    token = str(RefreshToken.for_user(user).access_token)
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


@pytest.mark.django_db
def test_create_recurring_event_persists_fields():
    user = make_user()
    resp = auth_client(user).post(
        f"{CAL}/create-event/",
        data=json.dumps(
            {
                "title": "Standup",
                "start": dt(2026, 7, 1).isoformat(),
                "end": dt(2026, 7, 1, 9).isoformat(),
                "recurrence": "weekly",
            }
        ),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["recurrence"] == "weekly"


@pytest.mark.django_db
def test_get_calendar_expands_recurring_occurrences():
    user = make_user()
    CalendarEvent.objects.create(  # pylint: disable=no-member
        user=user, title="Standup", start=dt(2026, 7, 1), recurrence="weekly"
    )

    resp = auth_client(user).get(
        f"{CAL}/get-calendar/",
        {"start": dt(2026, 7, 1, 0).isoformat(), "end": dt(2026, 7, 31, 23).isoformat()},
    )
    events = resp.json()["events"]
    standups = [e for e in events if e["title"] == "Standup"]
    assert len(standups) == 5  # Jul 1, 8, 15, 22, 29
    # Every occurrence carries the series' own start for whole-series editing.
    assert all(
        datetime.fromisoformat(e["series_start"]) == dt(2026, 7, 1) for e in standups
    )
    starts = sorted(datetime.fromisoformat(e["start"]) for e in standups)
    assert starts == [dt(2026, 7, d) for d in (1, 8, 15, 22, 29)]


@pytest.mark.django_db
def test_invalid_recurrence_rejected():
    user = make_user()
    resp = auth_client(user).post(
        f"{CAL}/create-event/",
        data=json.dumps(
            {"title": "X", "start": dt(2026, 7, 1).isoformat(), "recurrence": "daily"}
        ),
        content_type="application/json",
    )
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Reminders per occurrence
# --------------------------------------------------------------------------- #


@pytest.fixture
def sent_messages(monkeypatch):
    messages = []
    monkeypatch.setattr(
        telegram, "send_message", lambda chat_id, text: messages.append((chat_id, text))
    )
    return messages


@pytest.mark.django_db
def test_recurring_reminder_fires_for_current_occurrence(sent_messages):
    """A weekly event started weeks ago still reminds for today's occurrence."""
    user = make_user()
    UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, chat_id="123", reminder_lead_minutes=0
    )
    # First occurrence ~3 weeks ago so that this week's occurrence started 30s ago.
    first = timezone.now() - timedelta(weeks=3, seconds=30)
    CalendarEvent.objects.create(  # pylint: disable=no-member
        user=user, title="Weekly sync", start=first, recurrence="weekly"
    )

    assert send_due_event_reminders() == 1
    assert len(sent_messages) == 1
    # Dedup: a second run for the same occurrence sends nothing more.
    assert send_due_event_reminders() == 0
    assert SentReminder.objects.filter(kind="start").count() == 1  # pylint: disable=no-member
