"""
Tests for the Celery task that sends Telegram reminders for calendar events.
The Telegram send is stubbed so no network calls are made.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from django.contrib.auth.models import User

from ticktask import telegram
from ticktask.tasks import send_due_event_reminders
from ticktask.models import CalendarEvent, SentReminder, UserTelegramSettings


@pytest.fixture
def sent_messages(monkeypatch):
    """Captures messages the scheduler would send, instead of hitting Telegram."""
    messages = []
    monkeypatch.setattr(
        telegram, "send_message", lambda chat_id, text: messages.append((chat_id, text))
    )
    return messages


def make_user_with_telegram(username="alice", *, enabled=True, chat_id="123", lead=15):
    """Creates a user with Telegram settings."""
    user = User.objects.create_user(username=username, password="pw")
    UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, enabled=enabled, chat_id=chat_id, reminder_lead_minutes=lead
    )
    return user


def make_event(user, start, title="Meeting"):
    """Creates a calendar event for the user."""
    return CalendarEvent.objects.create(user=user, title=title, start=start)  # pylint: disable=no-member


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
