"""
Tests for the Celery task that sends Telegram reminders for calendar events.
The Telegram send is stubbed so no network calls are made.
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone
from django.contrib.auth.models import User

from ticktask import telegram
from ticktask.tasks import send_due_event_reminders, _days_before
from ticktask.models import CalendarEvent, SentReminder, UserTelegramSettings


@pytest.fixture
def sent_messages(monkeypatch):
    """Captures messages the scheduler would send, instead of hitting Telegram."""
    messages = []
    monkeypatch.setattr(
        telegram, "send_message", lambda chat_id, text: messages.append((chat_id, text))
    )
    return messages


def make_user_with_telegram(
    username="alice", *, enabled=True, chat_id="123", lead=15, tz=""
):
    """Creates a user with Telegram settings."""
    user = User.objects.create_user(username=username, password="pw")
    UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user,
        enabled=enabled,
        chat_id=chat_id,
        reminder_lead_minutes=lead,
        timezone=tz,
    )
    return user


def make_event(user, start, title="Meeting", **extra):
    """Creates a calendar event for the user."""
    return CalendarEvent.objects.create(  # pylint: disable=no-member
        user=user, title=title, start=start, **extra
    )


@pytest.mark.django_db
def test_start_reminder_fires_once(sent_messages):
    """A just-started event sends the 'start' reminder, exactly once."""
    user = make_user_with_telegram(lead=0)
    make_event(user, timezone.now() - timedelta(seconds=30))

    assert send_due_event_reminders() == 1
    assert len(sent_messages) == 1
    assert "starting now" in sent_messages[0][1]
    assert SentReminder.objects.filter(kind="start").count() == 1  # pylint: disable=no-member

    # A second run does not resend.
    assert send_due_event_reminders() == 0
    assert len(sent_messages) == 1


@pytest.mark.django_db
def test_lead_reminder_fires_before_start(sent_messages):
    """The 'X minutes before' reminder fires when its instant has passed."""
    user = make_user_with_telegram(lead=15)
    # Starts in 10 min → the lead instant (start - 15m) is 5 min in the past.
    make_event(user, timezone.now() + timedelta(minutes=10))

    assert send_due_event_reminders() == 1
    assert "in 15 minutes" in sent_messages[0][1]
    assert SentReminder.objects.filter(kind="lead").count() == 1  # pylint: disable=no-member


@pytest.mark.django_db
def test_skips_unconnected_user(sent_messages):
    """No reminder is sent to a user without a linked chat."""
    user = make_user_with_telegram(chat_id=None, lead=0)
    make_event(user, timezone.now() - timedelta(seconds=30))

    assert send_due_event_reminders() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_skips_disabled_user(sent_messages):
    """No reminder is sent when the user disabled them."""
    user = make_user_with_telegram(enabled=False, lead=0)
    make_event(user, timezone.now() - timedelta(seconds=30))

    assert send_due_event_reminders() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_future_event_not_yet_due(sent_messages):
    """An event whose instants are still in the future sends nothing."""
    user = make_user_with_telegram(lead=15)
    make_event(user, timezone.now() + timedelta(hours=2))

    assert send_due_event_reminders() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_old_event_outside_catchup_window(sent_messages):
    """An event whose moment passed long ago is not (re)sent on a late run."""
    user = make_user_with_telegram(lead=0)
    make_event(user, timezone.now() - timedelta(hours=2))

    assert send_due_event_reminders() == 0
    assert sent_messages == []


# ---------------------------------------------------------------------------
# Day-ahead reminders (per event)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "days, phrase", [(1, "tomorrow"), (3, "in 3 days"), (7, "in 1 week")]
)
def test_day_ahead_reminder_fires_once(sent_messages, days, phrase):
    """An 'N days before' reminder fires when its instant passes, only once."""
    user = make_user_with_telegram(lead=0)
    # Its day-ahead instant was 5 minutes ago.
    make_event(
        user,
        timezone.now() + timedelta(days=days, minutes=-5),
        title="Essay",
        reminder_days_before=[days],
    )

    assert send_due_event_reminders() == 1
    assert len(sent_messages) == 1
    assert f'"Essay" is {phrase}' in sent_messages[0][1]
    assert SentReminder.objects.filter(kind=f"days-{days}").count() == 1  # pylint: disable=no-member

    assert send_due_event_reminders() == 0
    assert len(sent_messages) == 1


@pytest.mark.django_db
def test_day_ahead_reminder_not_yet_due(sent_messages):
    """A week-ahead reminder doesn't fire while its instant is still ahead."""
    user = make_user_with_telegram(lead=15)
    make_event(user, timezone.now() + timedelta(days=7, hours=2), reminder_days_before=[7])

    assert send_due_event_reminders() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_day_ahead_reminder_missed_long_ago_is_skipped(sent_messages):
    """An event created after its day-ahead instant (beyond catch-up) skips it."""
    user = make_user_with_telegram(lead=15)
    make_event(user, timezone.now() + timedelta(days=2), reminder_days_before=[3])

    assert send_due_event_reminders() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_event_without_day_ahead_reminders_sends_none(sent_messages):
    """Without ``reminder_days_before`` nothing fires days ahead (old behaviour)."""
    user = make_user_with_telegram(lead=15)
    make_event(user, timezone.now() + timedelta(days=1, minutes=-5))

    assert send_due_event_reminders() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_day_ahead_reminder_shows_local_time(sent_messages):
    """The message shows the occurrence in the user's timezone."""
    user = make_user_with_telegram(lead=0, tz="Europe/Madrid")
    start = timezone.now() + timedelta(days=3, minutes=-5)
    make_event(user, start, title="Essay", reminder_days_before=[3])

    assert send_due_event_reminders() == 1
    local = start.astimezone(ZoneInfo("Europe/Madrid"))
    assert local.strftime("%a %d %b, %H:%M") in sent_messages[0][1]


def test_days_before_keeps_local_wall_time_across_dst():
    """'1 week before' keeps the local time even if DST changes in between."""
    zone = ZoneInfo("Europe/Madrid")
    # 2026-10-25 is the CEST→CET switch; the event is the Friday after.
    occurrence = datetime(2026, 10, 30, 23, 55, tzinfo=zone)

    instant = _days_before(occurrence, 7, zone)

    assert instant.astimezone(zone).replace(tzinfo=None) == datetime(
        2026, 10, 23, 23, 55
    )
    # In UTC that's 21:55 (CEST, UTC+2), not 22:55.
    assert instant.astimezone(dt_timezone.utc).hour == 21


@pytest.mark.django_db
def test_weekly_event_day_ahead_reminder_per_occurrence(sent_messages):
    """A weekly event reminds 1 day ahead of its upcoming occurrence."""
    user = make_user_with_telegram(lead=0)
    first = timezone.now() - timedelta(weeks=3) + timedelta(days=1, minutes=-5)
    make_event(
        user, first, title="Class", recurrence="weekly", reminder_days_before=[1]
    )

    assert send_due_event_reminders() == 1
    assert '"Class" is tomorrow' in sent_messages[0][1]
    reminder = SentReminder.objects.get(kind="days-1")  # pylint: disable=no-member
    assert reminder.occurrence == first + timedelta(weeks=3)
