"""
Tests for the interactive Telegram bot: command dispatch, the clock-in/out
button flows, the create-task/subtask conversation flows, and the unlinked-chat
path. The Bot API HTTP layer (``telegram._request``) is stubbed, so no network
calls are made and we assert on the payloads the bot would have sent.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User

from ticktask import telegram, services
from ticktask.models import (
    Task,
    SubTask,
    TimeEntry,
    CalendarEvent,
    UserTelegramSettings,
    UserAccessRequest,
)

CHAT_ID = 42


@pytest.fixture(autouse=True)
def stub_telegram_http(monkeypatch):
    """Stubs the Bot API HTTP layer and records every call made."""
    calls = []

    def fake_request(method, payload):
        calls.append((method, payload))
        return {"ok": True, "result": []}

    monkeypatch.setattr(telegram, "_request", fake_request)
    return calls


@pytest.fixture(autouse=True)
def bot_config(settings):
    """Provides a configured bot."""
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    settings.TELEGRAM_BOT_USERNAME = "TickTaskBot"
    return settings


@pytest.fixture(autouse=True)
def clear_state():
    """Conversation state lives in the cache; isolate it per test."""
    cache.clear()
    yield
    cache.clear()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def linked_user(username="alice", chat_id=CHAT_ID, **user_kwargs) -> User:
    """Creates a user with a Telegram chat already linked."""
    user = User.objects.create_user(username=username, password="pw", **user_kwargs)
    UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, chat_id=str(chat_id), connected_at=timezone.now()
    )
    return user


def pending_request(username="pending-user") -> UserAccessRequest:
    """Creates an inactive account with a pending access request."""
    user = User.objects.create_user(username=username, password="pw", is_active=False)
    return UserAccessRequest.objects.create(user=user)  # pylint: disable=no-member


def command(text, chat_id=CHAT_ID):
    return {"message": {"text": text, "chat": {"id": chat_id}}}


def text_reply(text, chat_id=CHAT_ID):
    return {"message": {"text": text, "chat": {"id": chat_id}}}


def callback(data, chat_id=CHAT_ID, message_id=100):
    return {
        "callback_query": {
            "id": "cb",
            "data": data,
            "message": {"message_id": message_id, "chat": {"id": chat_id}},
        }
    }


def sent_texts(calls):
    """Texts of every sendMessage / editMessageText call."""
    return [p["text"] for m, p in calls if m in ("sendMessage", "editMessageText")]


def last_markup(calls):
    """The reply_markup of the last send/edit call that had one."""
    for _, payload in reversed(calls):
        if "reply_markup" in payload:
            return payload["reply_markup"]
    return None


def callback_datas(markup):
    """All callback_data strings in an inline keyboard."""
    if not markup or "inline_keyboard" not in markup:
        return []
    return [btn["callback_data"] for row in markup["inline_keyboard"] for btn in row]


# --------------------------------------------------------------------------- #
# Linking / unlinked chat
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_unlinked_chat_is_told_to_connect(stub_telegram_http):
    """A command from a chat with no account gets a connect prompt."""
    telegram.process_update(command("/tasks", chat_id=999))
    assert any("connect" in t.lower() for t in sent_texts(stub_telegram_http))


@pytest.mark.django_db
def test_start_with_token_still_links(stub_telegram_http):
    """The /start linking flow keeps working alongside the new commands."""
    user = User.objects.create_user(username="bob", password="pw")
    row = UserTelegramSettings.objects.create(  # pylint: disable=no-member
        user=user, link_token="tok", link_token_created_at=timezone.now()
    )

    telegram.process_update(command("/start tok", chat_id=77))

    row.refresh_from_db()
    assert row.chat_id == "77"


# --------------------------------------------------------------------------- #
# Read commands
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_help_lists_commands(stub_telegram_http):
    linked_user()
    telegram.process_update(command("/help"))
    text = "\n".join(sent_texts(stub_telegram_http))
    assert "/clockin" in text and "/events" in text


@pytest.mark.django_db
def test_tasks_lists_recent_activity(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member
    sub = SubTask.objects.create(task=task, name="Code", description="")  # pylint: disable=no-member
    now = timezone.now()
    TimeEntry.objects.create(  # pylint: disable=no-member
        subtask=sub,
        clock_in=now - timedelta(hours=2),
        clock_out=now - timedelta(hours=1),
    )

    telegram.process_update(command("/tasks"))

    text = "\n".join(sent_texts(stub_telegram_http))
    assert "Proj ▸ Code" in text
    assert "1h" in text


@pytest.mark.django_db
def test_tasks_marks_open_entry_in_progress(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member
    sub = SubTask.objects.create(task=task, name="Code", description="")  # pylint: disable=no-member
    TimeEntry.objects.create(subtask=sub)  # pylint: disable=no-member  (open)

    telegram.process_update(command("/tasks"))
    assert any("in progress" in t for t in sent_texts(stub_telegram_http))


@pytest.mark.django_db
def test_events_lists_upcoming(stub_telegram_http):
    user = linked_user()
    CalendarEvent.objects.create(  # pylint: disable=no-member
        user=user, title="Standup", start=timezone.now() + timedelta(days=1)
    )
    CalendarEvent.objects.create(  # pylint: disable=no-member
        user=user, title="Old", start=timezone.now() - timedelta(days=3)
    )

    telegram.process_update(command("/events"))

    text = "\n".join(sent_texts(stub_telegram_http))
    assert "Standup" in text
    assert "Old" not in text


@pytest.mark.django_db
def test_events_empty_state(stub_telegram_http):
    linked_user()
    telegram.process_update(command("/events"))
    assert any("No upcoming events" in t for t in sent_texts(stub_telegram_http))


@pytest.mark.django_db
def test_events_formatted_in_user_timezone(stub_telegram_http):
    """Event times are shown in the user's configured timezone, not UTC."""
    user = linked_user()
    row = UserTelegramSettings.objects.get(user=user)  # pylint: disable=no-member
    row.timezone = "Asia/Kolkata"  # UTC+5:30, no DST → deterministic
    row.save(update_fields=["timezone"])
    start = timezone.now() + timedelta(days=1)
    CalendarEvent.objects.create(user=user, title="Call", start=start)  # pylint: disable=no-member

    telegram.process_update(command("/events"))

    expected = start.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M %Z")
    assert any(expected in t for t in sent_texts(stub_telegram_http))


# --------------------------------------------------------------------------- #
# Clock-in flow (buttons)
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_clockin_shows_task_picker(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member

    telegram.process_update(command("/clockin"))

    datas = callback_datas(last_markup(stub_telegram_http))
    assert f"ci:t:{task.id}" in datas
    assert "ci:newt" in datas


@pytest.mark.django_db
def test_clockin_pick_task_shows_subtasks(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member
    sub = SubTask.objects.create(task=task, name="Code", description="")  # pylint: disable=no-member

    telegram.process_update(callback(f"ci:t:{task.id}"))

    datas = callback_datas(last_markup(stub_telegram_http))
    assert f"ci:s:{sub.id}" in datas
    assert f"ci:news:{task.id}" in datas
    assert "ci:tasks" in datas  # back button


@pytest.mark.django_db
def test_clockin_pick_subtask_creates_entry(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member
    sub = SubTask.objects.create(task=task, name="Code", description="")  # pylint: disable=no-member

    telegram.process_update(callback(f"ci:s:{sub.id}"))

    entry = TimeEntry.objects.get(subtask=sub)  # pylint: disable=no-member
    assert entry.clock_out is None
    assert any("Clocked in" in t for t in sent_texts(stub_telegram_http))


@pytest.mark.django_db
def test_clockin_answers_the_callback_query(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member
    SubTask.objects.create(task=task, name="Code", description="")  # pylint: disable=no-member

    telegram.process_update(callback(f"ci:t:{task.id}"))
    assert any(m == "answerCallbackQuery" for m, _ in stub_telegram_http)


@pytest.mark.django_db
def test_clockin_blocked_when_already_clocked_in(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member
    sub = SubTask.objects.create(task=task, name="Code", description="")  # pylint: disable=no-member
    open_entry = TimeEntry.objects.create(subtask=sub)  # pylint: disable=no-member

    telegram.process_update(command("/clockin"))

    datas = callback_datas(last_markup(stub_telegram_http))
    assert f"co:{open_entry.id}" in datas  # offered a clock-out button


@pytest.mark.django_db
def test_callback_clock_in_rejected_on_deleted_subtask(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member
    sub = SubTask.objects.create(  # pylint: disable=no-member
        task=task, name="Code", description="", deleted_at=timezone.now()
    )

    telegram.process_update(callback(f"ci:s:{sub.id}"))

    assert not TimeEntry.objects.filter(subtask=sub).exists()  # pylint: disable=no-member
    assert any("⚠️" in t for t in sent_texts(stub_telegram_http))


# --------------------------------------------------------------------------- #
# Clock-out
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_clockout_closes_open_entry(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member
    sub = SubTask.objects.create(task=task, name="Code", description="")  # pylint: disable=no-member
    entry = TimeEntry.objects.create(  # pylint: disable=no-member
        subtask=sub, clock_in=timezone.now() - timedelta(minutes=90)
    )

    telegram.process_update(command("/clockout"))

    entry.refresh_from_db()
    assert entry.clock_out is not None
    assert any("Clocked out" in t for t in sent_texts(stub_telegram_http))


@pytest.mark.django_db
def test_clockout_when_not_clocked_in(stub_telegram_http):
    linked_user()
    telegram.process_update(command("/clockout"))
    assert any("not clocked in" in t.lower() for t in sent_texts(stub_telegram_http))


# --------------------------------------------------------------------------- #
# Create flows (ForceReply + state)
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_newtask_flow_creates_task(stub_telegram_http):
    user = linked_user()

    telegram.process_update(command("/newtask"))
    # Bot should prompt with a ForceReply.
    assert any(
        p.get("reply_markup", {}).get("force_reply")
        for m, p in stub_telegram_http
        if m == "sendMessage"
    )

    telegram.process_update(text_reply("Marketing"))
    assert Task.objects.filter(user=user, name="Marketing").exists()  # pylint: disable=no-member


@pytest.mark.django_db
def test_newtask_duplicate_name_is_reported(stub_telegram_http):
    user = linked_user()
    Task.objects.create(user=user, name="Dup")  # pylint: disable=no-member

    telegram.process_update(command("/newtask"))
    telegram.process_update(text_reply("Dup"))

    assert Task.objects.filter(user=user, name="Dup").count() == 1  # pylint: disable=no-member
    assert any("⚠️" in t for t in sent_texts(stub_telegram_http))


@pytest.mark.django_db
def test_newsubtask_flow_creates_subtask(stub_telegram_http):
    user = linked_user()
    task = Task.objects.create(user=user, name="Proj")  # pylint: disable=no-member

    telegram.process_update(command("/newsubtask"))
    # Pick the parent task.
    datas = callback_datas(last_markup(stub_telegram_http))
    assert f"ci:news:{task.id}" in datas

    telegram.process_update(callback(f"ci:news:{task.id}"))
    telegram.process_update(text_reply("Design"))

    assert SubTask.objects.filter(task=task, name="Design").exists()  # pylint: disable=no-member


@pytest.mark.django_db
def test_cancel_drops_pending_flow(stub_telegram_http):
    user = linked_user()

    telegram.process_update(command("/newtask"))
    telegram.process_update(command("/cancel"))
    telegram.process_update(text_reply("ShouldNotExist"))

    assert not Task.objects.filter(user=user, name="ShouldNotExist").exists()  # pylint: disable=no-member


@pytest.mark.django_db
def test_new_command_cancels_previous_flow(stub_telegram_http):
    """Starting a new command mid-flow drops the old pending action."""
    user = linked_user()

    telegram.process_update(command("/newtask"))
    telegram.process_update(command("/help"))  # interrupts the flow
    telegram.process_update(text_reply("Orphan"))

    assert not Task.objects.filter(user=user, name="Orphan").exists()  # pylint: disable=no-member


# --------------------------------------------------------------------------- #
# Access requests (notify admins + approve/reject buttons)
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_notify_admins_messages_linked_superusers(stub_telegram_http):
    """Linked admins get a message with approve/reject buttons; others don't."""
    linked_user("boss", chat_id=500, is_superuser=True)
    linked_user("regular", chat_id=501)  # not an admin
    req = pending_request("applicant")

    telegram.notify_admins_of_access_request(req)

    sends = [p for m, p in stub_telegram_http if m == "sendMessage"]
    assert len(sends) == 1
    assert sends[0]["chat_id"] == "500"
    assert sends[0]["text"].startswith(telegram.ADMIN_PREFIX)
    datas = callback_datas(sends[0]["reply_markup"])
    assert f"acc:approve:{req.id}" in datas
    assert f"acc:reject:{req.id}" in datas


@pytest.mark.django_db
def test_admin_can_approve_via_button(stub_telegram_http):
    """An admin tapping approve activates the applicant's account."""
    linked_user("boss", chat_id=500, is_superuser=True)
    req = pending_request("applicant")

    telegram.process_update(callback(f"acc:approve:{req.id}", chat_id=500))

    req.refresh_from_db()
    assert req.status == UserAccessRequest.APPROVED
    assert User.objects.get(username="applicant").is_active is True  # pylint: disable=no-member


@pytest.mark.django_db
def test_admin_can_reject_via_button(stub_telegram_http):
    """An admin tapping reject leaves the applicant inactive."""
    linked_user("boss", chat_id=500, is_superuser=True)
    req = pending_request("applicant")

    telegram.process_update(callback(f"acc:reject:{req.id}", chat_id=500))

    req.refresh_from_db()
    assert req.status == UserAccessRequest.REJECTED
    assert User.objects.get(username="applicant").is_active is False  # pylint: disable=no-member


@pytest.mark.django_db
def test_non_admin_cannot_decide_access(stub_telegram_http):
    """A non-admin tapping the button changes nothing."""
    linked_user("regular", chat_id=501)  # not an admin
    req = pending_request("applicant")

    telegram.process_update(callback(f"acc:approve:{req.id}", chat_id=501))

    req.refresh_from_db()
    assert req.status == UserAccessRequest.PENDING
    assert User.objects.get(username="applicant").is_active is False  # pylint: disable=no-member


@pytest.mark.django_db
def test_already_decided_request_is_noop(stub_telegram_http):
    """Tapping a button on an already-decided request doesn't flip it."""
    linked_user("boss", chat_id=500, is_superuser=True)
    req = pending_request("applicant")
    services.approve_access(req)

    telegram.process_update(callback(f"acc:reject:{req.id}", chat_id=500))

    req.refresh_from_db()
    assert req.status == UserAccessRequest.APPROVED
