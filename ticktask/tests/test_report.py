"""
Tests for the on-demand ``/report``: the matplotlib chart renderers, the report
orchestration, and the Telegram command that ships the album. The Bot API HTTP
layers (``telegram._request`` and ``telegram._request_files``) are stubbed, so no
network calls are made and we assert on the payloads the bot would have sent.
"""

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone as dj_timezone
from django.contrib.auth.models import User

from ticktask import telegram, reports
from ticktask.models import Task, SubTask, TimeEntry, UserTelegramSettings

CHAT_ID = 77
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def stub_telegram_http(monkeypatch):
    """Stubs both Bot API transports and records every call made."""
    calls = {"json": [], "files": []}

    def fake_request(method, payload):
        calls["json"].append((method, payload))
        return {"ok": True, "result": []}

    def fake_request_files(method, data, files):
        calls["files"].append((method, data, files))
        return {"ok": True, "result": []}

    monkeypatch.setattr(telegram, "_request", fake_request)
    monkeypatch.setattr(telegram, "_request_files", fake_request_files)
    return calls


@pytest.fixture(autouse=True)
def bot_config(settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    settings.TELEGRAM_BOT_USERNAME = "TickTaskBot"
    return settings


def make_subtask(user, task_name, subtask_name="s"):
    task, _ = Task.objects.get_or_create(user=user, name=task_name)  # pylint: disable=no-member
    return SubTask.objects.create(task=task, name=subtask_name, description="d")  # pylint: disable=no-member


def make_entry(subtask, clock_in, clock_out):
    entry = TimeEntry.objects.create(subtask=subtask)  # pylint: disable=no-member
    TimeEntry.objects.filter(id=entry.id).update(clock_in=clock_in, clock_out=clock_out)  # pylint: disable=no-member
    return entry


def user_with_time(username="alice"):
    """A user with some tracked time on two tasks within the last week."""
    user = User.objects.create_user(username=username, password="pw")
    now = dj_timezone.now()
    a = make_subtask(user, "Alpha")
    b = make_subtask(user, "Beta")
    make_entry(a, now - timedelta(days=1), now - timedelta(days=1) + timedelta(hours=3))
    make_entry(b, now - timedelta(days=2), now - timedelta(days=2) + timedelta(hours=1))
    return user


def sample_series(days=30):
    """A minimal `time_series`-shaped dict for the renderers."""
    start = date(2026, 6, 1)
    buckets = [
        {"period_start": start + timedelta(days=i), "hours": float(i % 4)}
        for i in range(days)
    ]
    by_task = [
        {
            "task_id": 1, "task_name": "Alpha", "deleted": False, "hours": 30.0,
            "series": [float(i % 3) for i in range(days)],
        },
        {
            "task_id": 2, "task_name": "Beta", "deleted": False, "hours": 15.0,
            "series": [float(i % 2) for i in range(days)],
        },
    ]
    return {
        "bucket": "day",
        "start": datetime(2026, 6, 1),
        "end": datetime(2026, 6, 30),
        "buckets": buckets,
        "by_task": by_task,
    }


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #


def test_renderers_return_png_bytes():
    series = sample_series()
    for png in (
        reports.render_trend(series),
        reports.render_composition(series),
        reports.render_share(series),
        reports.render_heatmap(series, weeks=6, end=date(2026, 6, 30)),
    ):
        assert isinstance(png, (bytes, bytearray))
        assert png[:8] == PNG_MAGIC


def test_share_handles_no_tracked_time():
    """An all-zero range still renders (an empty-state donut), not a crash."""
    series = sample_series()
    for t in series["by_task"]:
        t["hours"] = 0.0
    png = reports.render_share(series)
    assert png[:8] == PNG_MAGIC


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_has_data():
    empty = User.objects.create_user(username="empty", password="pw")
    assert reports.has_data(empty) is False
    assert reports.has_data(user_with_time()) is True


@pytest.mark.django_db
def test_build_report_returns_caption_and_four_charts():
    user = user_with_time()
    caption, images = reports.build_report(user, ZoneInfo("UTC"))

    assert "TickTask report" in caption
    assert "Alpha" in caption  # the top task shows up in the summary
    assert [name for name, _ in images] == [
        "trend.png", "composition.png", "share.png", "heatmap.png",
    ]
    assert all(png[:8] == PNG_MAGIC for _, png in images)


# --------------------------------------------------------------------------- #
# Transport
# --------------------------------------------------------------------------- #


def test_send_media_group_puts_caption_on_first_item(stub_telegram_http):
    telegram.send_media_group(
        CHAT_ID, [("a.png", b"a"), ("b.png", b"b")], caption="hello"
    )
    method, data, files = stub_telegram_http["files"][0]
    assert method == "sendMediaGroup"
    media = json.loads(data["media"])
    assert media[0]["media"] == "attach://photo0"
    assert media[0]["caption"] == "hello"
    assert "caption" not in media[1]
    assert set(files) == {"photo0", "photo1"}


# --------------------------------------------------------------------------- #
# Command
# --------------------------------------------------------------------------- #


def link_chat(user):
    UserTelegramSettings.objects.create(user=user, chat_id=str(CHAT_ID), enabled=True)  # pylint: disable=no-member


@pytest.mark.django_db
def test_report_command_sends_album(stub_telegram_http):
    user = user_with_time()
    link_chat(user)

    telegram.process_update({"message": {"chat": {"id": CHAT_ID}, "text": "/report"}})

    assert len(stub_telegram_http["files"]) == 1
    method, data, files = stub_telegram_http["files"][0]
    assert method == "sendMediaGroup"
    assert len(files) == 4
    assert "TickTask report" in json.loads(data["media"])[0]["caption"]


@pytest.mark.django_db
def test_report_command_without_data_sends_text(stub_telegram_http):
    user = User.objects.create_user(username="empty", password="pw")
    link_chat(user)

    telegram.process_update({"message": {"chat": {"id": CHAT_ID}, "text": "/report"}})

    assert stub_telegram_http["files"] == []
    texts = [p["text"] for m, p in stub_telegram_http["json"] if m == "sendMessage"]
    assert any("No tracked time yet" in t for t in texts)


def test_report_is_in_command_menu():
    assert any(c == "report" for c, _ in telegram.BOT_COMMANDS)
