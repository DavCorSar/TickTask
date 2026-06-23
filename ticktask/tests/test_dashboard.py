"""
Tests for the dashboard aggregation endpoints (summary + time series).
"""

from datetime import datetime, timedelta, timezone

import pytest
from django.test import Client
from django.utils import timezone as dj_timezone
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

from ticktask.models import Task, SubTask, TimeEntry

BASE = "/api/dashboard/user"


def make_user(username: str = "alice") -> User:
    """Creates a user that owns the tracked time under test."""
    return User.objects.create_user(username=username, password="pw")


def auth_client(user: User) -> Client:
    """Returns a Django test client authenticated as ``user`` via JWT."""
    token = str(RefreshToken.for_user(user).access_token)
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


def make_subtask(user: User, task_name: str, subtask_name: str) -> SubTask:
    """Creates a task + subtask owned by ``user``."""
    task, _ = Task.objects.get_or_create(user=user, name=task_name)  # pylint: disable=no-member
    return SubTask.objects.create(  # pylint: disable=no-member
        task=task, name=subtask_name, description="d"
    )


def make_entry(subtask: SubTask, clock_in: datetime, clock_out) -> TimeEntry:
    """Creates a time entry with explicit clock_in/out (clock_in is auto_now_add)."""
    entry = TimeEntry.objects.create(subtask=subtask)  # pylint: disable=no-member
    TimeEntry.objects.filter(id=entry.id).update(  # pylint: disable=no-member
        clock_in=clock_in, clock_out=clock_out
    )
    return entry


def iso(dt: datetime) -> str:
    """Serializes a datetime to ISO 8601."""
    return dt.isoformat()


# --------------------------------------------------------------------------- #
# Weekly task hours (share of the last 7 days)
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_weekly_task_hours_shares():
    """Each task's hours and its percent of the week's total are returned."""
    user = make_user()
    now = dj_timezone.now()
    a = make_subtask(user, "Alpha", "s")
    b = make_subtask(user, "Beta", "s")
    # 3h on Alpha and 1h on Beta, both within the last 7 days → 75% / 25%.
    make_entry(a, now - timedelta(days=1), now - timedelta(days=1) + timedelta(hours=3))
    make_entry(b, now - timedelta(days=2), now - timedelta(days=2) + timedelta(hours=1))

    body = auth_client(user).get(f"{BASE}/get-weekly-task-hours/").json()

    assert body["total_hours"] == 4.0
    names = [t["task_name"] for t in body["tasks"]]
    assert names == ["Alpha", "Beta"]  # sorted by hours, most first
    by_name = {t["task_name"]: t for t in body["tasks"]}
    assert by_name["Alpha"]["hours"] == 3.0 and by_name["Alpha"]["percent"] == 75.0
    assert by_name["Beta"]["percent"] == 25.0


@pytest.mark.django_db
def test_weekly_task_hours_excludes_old_and_untracked():
    """Entries older than 7 days and tasks with no recent time are left out."""
    user = make_user()
    now = dj_timezone.now()
    recent = make_subtask(user, "Recent", "s")
    old = make_subtask(user, "Old", "s")
    make_entry(recent, now - timedelta(hours=2), now - timedelta(hours=1))
    make_entry(old, now - timedelta(days=10), now - timedelta(days=10) + timedelta(hours=5))

    body = auth_client(user).get(f"{BASE}/get-weekly-task-hours/").json()

    assert [t["task_name"] for t in body["tasks"]] == ["Recent"]
    assert body["tasks"][0]["percent"] == 100.0


@pytest.mark.django_db
def test_weekly_task_hours_excludes_deleted_by_default():
    """Soft-deleted tasks are hidden unless include_deleted is set."""
    user = make_user()
    now = dj_timezone.now()
    sub = make_subtask(user, "Gone", "s")
    make_entry(sub, now - timedelta(hours=2), now - timedelta(hours=1))
    Task.objects.filter(name="Gone", user=user).update(deleted_at=now)  # pylint: disable=no-member

    client = auth_client(user)
    assert client.get(f"{BASE}/get-weekly-task-hours/").json()["tasks"] == []

    with_deleted = client.get(
        f"{BASE}/get-weekly-task-hours/", {"include_deleted": "true"}
    ).json()
    assert [t["task_name"] for t in with_deleted["tasks"]] == ["Gone"]
    assert with_deleted["tasks"][0]["deleted"] is True


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_summary_aggregates_windows():
    """Today/week/month include the recent entry; total also includes old time."""
    user = make_user()
    now = dj_timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    recent = make_subtask(user, "Recent", "s")
    old = make_subtask(user, "Old", "s")
    # 30 min today (anchored to midnight, always inside today/week/month).
    make_entry(recent, today_start, today_start + timedelta(minutes=30))
    # 2 h, 100 days ago (only counts towards the all-time total).
    old_in = today_start - timedelta(days=100)
    make_entry(old, old_in, old_in + timedelta(hours=2))

    resp = auth_client(user).get(f"{BASE}/get-summary/")

    assert resp.status_code == 200
    body = resp.json()
    assert body["today_hours"] == 0.5
    assert body["week_hours"] == 0.5
    assert body["month_hours"] == 0.5
    assert body["total_hours"] == 2.5
    # Only the task worked on this week is "active".
    assert body["active_tasks"] == 1


@pytest.mark.django_db
def test_summary_ignores_open_entries_for_hours_but_counts_active():
    """An open entry adds no hours but its task still counts as active."""
    user = make_user()
    today_start = dj_timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    subtask = make_subtask(user, "Live", "s")
    make_entry(subtask, today_start, None)

    body = auth_client(user).get(f"{BASE}/get-summary/").json()

    assert body["total_hours"] == 0.0
    assert body["active_tasks"] == 1


@pytest.mark.django_db
def test_summary_scoped_to_user():
    """Another user's tracked time is never aggregated."""
    user = make_user("alice")
    other = make_user("bob")
    today_start = dj_timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    make_entry(
        make_subtask(other, "Theirs", "s"),
        today_start,
        today_start + timedelta(hours=1),
    )

    body = auth_client(user).get(f"{BASE}/get-summary/").json()

    assert body["total_hours"] == 0.0
    assert body["active_tasks"] == 0


# --------------------------------------------------------------------------- #
# Time series
# --------------------------------------------------------------------------- #


def _series(client, start, end, bucket=None):
    params = {"start": iso(start), "end": iso(end)}
    if bucket:
        params["bucket"] = bucket
    return client.get(f"{BASE}/get-time-series/", params)


@pytest.mark.django_db
def test_time_series_day_buckets_zero_filled():
    """Daily buckets are contiguous and missing days are filled with zero."""
    user = make_user()
    subtask = make_subtask(user, "T", "s")
    make_entry(
        subtask,
        datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 10, tzinfo=timezone.utc),
    )  # 1 h
    make_entry(
        subtask,
        datetime(2026, 3, 3, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 3, 11, tzinfo=timezone.utc),
    )  # 2 h

    resp = _series(
        auth_client(user),
        datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 3, 23, 59, tzinfo=timezone.utc),
        bucket="day",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["bucket"] == "day"
    assert [(b["period_start"], b["hours"]) for b in body["buckets"]] == [
        ("2026-03-01", 1.0),
        ("2026-03-02", 0.0),
        ("2026-03-03", 2.0),
    ]


@pytest.mark.django_db
def test_time_series_by_task_breakdown_sorted():
    """by_task aggregates per task/subtask and is sorted by hours desc."""
    user = make_user()
    sub_a = make_subtask(user, "Alpha", "a1")
    sub_b = make_subtask(user, "Beta", "b1")
    make_entry(
        sub_a,
        datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 10, tzinfo=timezone.utc),
    )  # Alpha 1 h
    make_entry(
        sub_b,
        datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 12, tzinfo=timezone.utc),
    )  # Beta 3 h

    body = _series(
        auth_client(user),
        datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 23, tzinfo=timezone.utc),
    ).json()

    names = [(t["task_name"], t["hours"]) for t in body["by_task"]]
    assert names == [("Beta", 3.0), ("Alpha", 1.0)]
    beta = body["by_task"][0]
    assert beta["subtasks"] == [
        {"subtask_id": sub_b.id, "subtask_name": "b1", "hours": 3.0, "deleted": False}
    ]


@pytest.mark.django_db
def test_time_series_per_task_series_aligns_with_buckets():
    """Each task carries a per-bucket series aligned with the bucket axis."""
    user = make_user()
    subtask = make_subtask(user, "T", "s")
    make_entry(subtask, datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
               datetime(2026, 3, 1, 10, tzinfo=timezone.utc))  # day 1: 1 h
    make_entry(subtask, datetime(2026, 3, 3, 9, tzinfo=timezone.utc),
               datetime(2026, 3, 3, 11, tzinfo=timezone.utc))  # day 3: 2 h

    body = _series(
        auth_client(user),
        datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 3, 23, 59, tzinfo=timezone.utc),
        bucket="day",
    ).json()

    assert [b["period_start"] for b in body["buckets"]] == [
        "2026-03-01",
        "2026-03-02",
        "2026-03-03",
    ]
    assert len(body["by_task"]) == 1
    # Series is aligned, in order, with the buckets above.
    assert body["by_task"][0]["series"] == [1.0, 0.0, 2.0]


@pytest.mark.django_db
def test_time_series_includes_tasks_without_activity():
    """Tasks with no tracked time in the range still appear, flat at zero."""
    user = make_user()
    active = make_subtask(user, "Active", "s")
    make_entry(active, datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
               datetime(2026, 3, 1, 10, tzinfo=timezone.utc))  # 1 h
    # A second task with no entries at all in the range.
    Task.objects.create(user=user, name="Idle")  # pylint: disable=no-member

    body = _series(
        auth_client(user),
        datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 2, 0, tzinfo=timezone.utc),
        bucket="day",
    ).json()

    by_name = {t["task_name"]: t for t in body["by_task"]}
    assert set(by_name) == {"Active", "Idle"}
    # The active task ranks first; the idle one is present but all zeros.
    assert body["by_task"][0]["task_name"] == "Active"
    assert by_name["Idle"]["hours"] == 0.0
    assert set(by_name["Idle"]["series"]) == {0.0}
    assert by_name["Idle"]["subtasks"] == []


@pytest.mark.django_db
def test_time_series_week_bucket_groups_same_week():
    """Entries in the same ISO week collapse into one weekly bucket."""
    user = make_user()
    subtask = make_subtask(user, "T", "s")
    # 2026-03-02 is a Monday; both entries fall in that week.
    make_entry(
        subtask,
        datetime(2026, 3, 3, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 3, 10, tzinfo=timezone.utc),
    )  # 1 h
    make_entry(
        subtask,
        datetime(2026, 3, 5, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 5, 10, tzinfo=timezone.utc),
    )  # 1 h

    body = _series(
        auth_client(user),
        datetime(2026, 3, 2, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 6, 0, tzinfo=timezone.utc),
        bucket="week",
    ).json()

    assert body["buckets"] == [{"period_start": "2026-03-02", "hours": 2.0}]


@pytest.mark.django_db
def test_time_series_rejects_invalid_bucket():
    """An unknown bucket size is rejected."""
    resp = _series(
        auth_client(make_user()),
        datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 2, 0, tzinfo=timezone.utc),
        bucket="year",
    )
    assert resp.status_code == 422


@pytest.mark.django_db
def test_time_series_rejects_end_before_start():
    """A range whose end precedes its start is rejected."""
    resp = _series(
        auth_client(make_user()),
        datetime(2026, 3, 2, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 422


@pytest.mark.django_db
def test_time_series_scoped_to_user():
    """Another user's entries never appear in the series or breakdown."""
    user = make_user("alice")
    other = make_user("bob")
    make_entry(
        make_subtask(other, "Theirs", "s"),
        datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 10, tzinfo=timezone.utc),
    )

    body = _series(
        auth_client(user),
        datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 23, tzinfo=timezone.utc),
    ).json()

    assert body["by_task"] == []
    assert all(b["hours"] == 0.0 for b in body["buckets"])


@pytest.mark.django_db
def test_dashboard_requires_authentication():
    """Unauthenticated requests are rejected."""
    assert Client().get(f"{BASE}/get-summary/").status_code == 401
