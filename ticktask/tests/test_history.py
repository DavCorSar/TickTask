"""
Tests for the time-entry history endpoint used by the history page.
"""

from datetime import datetime, timezone

import pytest
from django.test import Client
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

from ticktask.models import Task, SubTask, TimeEntry

BASE = "/api/ticktask/user"


def make_user(username: str = "alice") -> User:
    """Creates a user that owns the entries under test."""
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
    """Creates a time entry with explicit timestamps (clock_in is auto_now_add)."""
    entry = TimeEntry.objects.create(subtask=subtask)  # pylint: disable=no-member
    TimeEntry.objects.filter(id=entry.id).update(  # pylint: disable=no-member
        clock_in=clock_in, clock_out=clock_out
    )
    return entry


def history(client: Client, start: datetime, end: datetime, include_deleted=None):
    params = {"start": start.isoformat(), "end": end.isoformat()}
    if include_deleted is not None:
        params["include_deleted"] = include_deleted
    return client.get(f"{BASE}/get-time-history/", params)


RANGE = (
    datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
    datetime(2026, 3, 4, 0, tzinfo=timezone.utc),
)


@pytest.mark.django_db
def test_history_returns_flattened_entries_newest_first():
    """Entries in range come back with task/subtask names, newest first."""
    user = make_user()
    subtask = make_subtask(user, "Proj", "Sub")
    make_entry(
        subtask,
        datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 10, tzinfo=timezone.utc),
    )
    make_entry(
        subtask,
        datetime(2026, 3, 3, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 3, 10, tzinfo=timezone.utc),
    )

    resp = history(auth_client(user), *RANGE)

    assert resp.status_code == 200
    body = resp.json()
    assert [e["clock_in"][:10] for e in body] == ["2026-03-03", "2026-03-01"]
    assert body[0]["task_name"] == "Proj"
    assert body[0]["subtask_name"] == "Sub"
    assert body[0]["deleted"] is False


@pytest.mark.django_db
def test_history_filters_by_range():
    """Entries whose clock_in is outside the window are excluded."""
    user = make_user()
    subtask = make_subtask(user, "Proj", "Sub")
    make_entry(
        subtask,
        datetime(2026, 3, 2, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 2, 10, tzinfo=timezone.utc),
    )  # inside
    make_entry(
        subtask,
        datetime(2026, 2, 1, 9, tzinfo=timezone.utc),
        datetime(2026, 2, 1, 10, tzinfo=timezone.utc),
    )  # before

    body = history(auth_client(user), *RANGE).json()
    assert len(body) == 1
    assert body[0]["clock_in"][:10] == "2026-03-02"


@pytest.mark.django_db
def test_history_includes_open_entry():
    """An entry still clocked in is returned with a null clock_out."""
    user = make_user()
    subtask = make_subtask(user, "Proj", "Sub")
    make_entry(subtask, datetime(2026, 3, 2, 9, tzinfo=timezone.utc), None)

    body = history(auth_client(user), *RANGE).json()
    assert len(body) == 1
    assert body[0]["clock_out"] is None


@pytest.mark.django_db
def test_history_scoped_to_user():
    """Another user's entries are never returned."""
    user = make_user("alice")
    other = make_user("bob")
    make_entry(
        make_subtask(other, "Theirs", "Sub"),
        datetime(2026, 3, 2, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 2, 10, tzinfo=timezone.utc),
    )

    body = history(auth_client(user), *RANGE).json()
    assert body == []


@pytest.mark.django_db
def test_history_hides_deleted_by_default_and_can_include():
    """Deleted subtasks/tasks are excluded unless include_deleted is set."""
    user = make_user()
    subtask = make_subtask(user, "Proj", "Sub")
    make_entry(
        subtask,
        datetime(2026, 3, 2, 9, tzinfo=timezone.utc),
        datetime(2026, 3, 2, 10, tzinfo=timezone.utc),
    )
    subtask.deleted_at = datetime(2026, 3, 2, 12, tzinfo=timezone.utc)
    subtask.save(update_fields=["deleted_at"])

    assert history(auth_client(user), *RANGE).json() == []

    included = history(auth_client(user), *RANGE, include_deleted="true").json()
    assert len(included) == 1
    assert included[0]["deleted"] is True


@pytest.mark.django_db
def test_history_requires_authentication():
    """Unauthenticated requests are rejected."""
    assert history(Client(), *RANGE).status_code == 401
