"""
Tests for the Celery task that sends the weekly Telegram time-tracking
summary. The Telegram send is stubbed so no network calls are made.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from django.contrib.auth.models import User

from ticktask import telegram
from ticktask.tasks import send_weekly_summaries, TOP_TASKS_SHOWN
from ticktask.models import Task, SubTask, TimeEntry, UserTelegramSettings


@pytest.fixture
def sent_messages(monkeypatch):
    """Captures messages the task would send, instead of hitting Telegram."""
    messages = []
    monkeypatch.setattr(
        telegram, "send_message", lambda chat_id, text: messages.append((chat_id, text))
    )
    return messages


def make_user_with_telegram(username="alice", *, enabled=True, chat_id="123"):
    """Creates a user with Telegram settings."""
    user = User.objects.create_user(username=username, password="pw")
    UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, enabled=enabled, chat_id=chat_id
    )
    return user


def make_subtask(user, task_name, subtask_name="s"):
    task, _ = Task.objects.get_or_create(user=user, name=task_name)  # pylint: disable=no-member
    return SubTask.objects.create(task=task, name=subtask_name, description="d")  # pylint: disable=no-member


def make_entry(subtask, clock_in, clock_out):
    entry = TimeEntry.objects.create(subtask=subtask)  # pylint: disable=no-member
    TimeEntry.objects.filter(id=entry.id).update(clock_in=clock_in, clock_out=clock_out)  # pylint: disable=no-member
    return entry


@pytest.mark.django_db
def test_summary_lists_tasks_by_hours(sent_messages):
    """Sends one message with tasks ordered by tracked hours, most first."""
    user = make_user_with_telegram()
    now = timezone.now()
    alpha = make_subtask(user, "Alpha")
    beta = make_subtask(user, "Beta")
    make_entry(alpha, now - timedelta(days=1), now - timedelta(days=1) + timedelta(hours=1))
    make_entry(beta, now - timedelta(days=2), now - timedelta(days=2) + timedelta(hours=3))

    assert send_weekly_summaries() == 1
    assert len(sent_messages) == 1
    chat_id, text = sent_messages[0]
    assert chat_id == "123"
    assert "Total tracked: 4h" in text
    assert text.index("Beta") < text.index("Alpha")


@pytest.mark.django_db
def test_caps_top_tasks_and_notes_the_rest(sent_messages):
    """Only the top N tasks are listed by name; the remainder is summarized."""
    user = make_user_with_telegram()
    now = timezone.now()
    for i in range(TOP_TASKS_SHOWN + 2):
        subtask = make_subtask(user, f"Task {i}")
        make_entry(subtask, now - timedelta(hours=i + 1), now - timedelta(hours=i))

    send_weekly_summaries()
    text = sent_messages[0][1]
    assert text.count(" — ") == TOP_TASKS_SHOWN + 1  # the header line + each listed task
    assert "…and 2 more." in text


@pytest.mark.django_db
def test_skips_user_with_nothing_tracked(sent_messages):
    """No message is sent to a user with no time tracked in the window."""
    make_user_with_telegram()

    assert send_weekly_summaries() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_skips_unconnected_user(sent_messages):
    """No summary is sent to a user without a linked chat."""
    user = make_user_with_telegram(chat_id=None)
    now = timezone.now()
    make_entry(make_subtask(user, "Alpha"), now - timedelta(hours=1), now)

    assert send_weekly_summaries() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_skips_disabled_user(sent_messages):
    """No summary is sent when the user disabled notifications."""
    user = make_user_with_telegram(enabled=False)
    now = timezone.now()
    make_entry(make_subtask(user, "Alpha"), now - timedelta(hours=1), now)

    assert send_weekly_summaries() == 0
    assert sent_messages == []


@pytest.mark.django_db
def test_ignores_entries_older_than_a_week(sent_messages):
    """Time tracked outside the trailing 7 days doesn't count towards the summary."""
    user = make_user_with_telegram()
    now = timezone.now()
    make_entry(make_subtask(user, "Old"), now - timedelta(days=30), now - timedelta(days=30) + timedelta(hours=2))

    assert send_weekly_summaries() == 0
    assert sent_messages == []
