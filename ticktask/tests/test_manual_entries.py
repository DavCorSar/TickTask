"""
Tests for manually creating and editing time entries.
"""

import json
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


def make_subtask(user: User, task_name="Proj", subtask_name="Sub") -> SubTask:
    """Creates a task + subtask owned by ``user``."""
    task, _ = Task.objects.get_or_create(user=user, name=task_name)  # pylint: disable=no-member
    return SubTask.objects.create(  # pylint: disable=no-member
        task=task, name=subtask_name, description="d"
    )


def post(client: Client, path: str, payload: dict):
    """POSTs a JSON body."""
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def iso(dt: datetime) -> str:
    return dt.isoformat()


START = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
END = datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc)


@pytest.mark.django_db
def test_create_manual_entry():
    """A completed entry is logged with the given start and end."""
    user = make_user()
    subtask = make_subtask(user)

    resp = post(
        auth_client(user),
        f"{BASE}/create-time-entry/",
        {"subtask_id": subtask.id, "clock_in": iso(START), "clock_out": iso(END)},
    )

    assert resp.status_code == 200
    entry = TimeEntry.objects.get(subtask=subtask)  # pylint: disable=no-member
    assert entry.clock_in == START
    assert entry.clock_out == END


@pytest.mark.django_db
def test_create_rejects_end_before_start():
    """An end at or before the start is rejected."""
    user = make_user()
    subtask = make_subtask(user)

    resp = post(
        auth_client(user),
        f"{BASE}/create-time-entry/",
        {"subtask_id": subtask.id, "clock_in": iso(END), "clock_out": iso(START)},
    )

    assert resp.status_code == 422
    assert TimeEntry.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_create_on_deleted_subtask_rejected():
    """Logging time on a deleted subtask is rejected."""
    user = make_user()
    subtask = make_subtask(user)
    subtask.deleted_at = START
    subtask.save(update_fields=["deleted_at"])

    resp = post(
        auth_client(user),
        f"{BASE}/create-time-entry/",
        {"subtask_id": subtask.id, "clock_in": iso(START), "clock_out": iso(END)},
    )
    assert resp.status_code == 409


@pytest.mark.django_db
def test_create_on_another_users_subtask_returns_404():
    """A user cannot log time on someone else's subtask."""
    owner = make_user("alice")
    intruder = make_user("bob")
    subtask = make_subtask(owner)

    resp = post(
        auth_client(intruder),
        f"{BASE}/create-time-entry/",
        {"subtask_id": subtask.id, "clock_in": iso(START), "clock_out": iso(END)},
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_update_entry_times():
    """Editing an entry changes its start and end."""
    user = make_user()
    subtask = make_subtask(user)
    entry = TimeEntry.objects.create(  # pylint: disable=no-member
        subtask=subtask, clock_in=START, clock_out=END
    )
    new_in = datetime(2026, 3, 2, 8, 0, tzinfo=timezone.utc)
    new_out = datetime(2026, 3, 2, 10, 30, tzinfo=timezone.utc)

    resp = post(
        auth_client(user),
        f"{BASE}/update-time-entry/",
        {"entity_id": entry.id, "clock_in": iso(new_in), "clock_out": iso(new_out)},
    )

    assert resp.status_code == 200
    entry.refresh_from_db()
    assert entry.clock_in == new_in
    assert entry.clock_out == new_out


@pytest.mark.django_db
def test_update_rejects_end_before_start():
    """Editing to an end at or before the start is rejected."""
    user = make_user()
    subtask = make_subtask(user)
    entry = TimeEntry.objects.create(  # pylint: disable=no-member
        subtask=subtask, clock_in=START, clock_out=END
    )

    resp = post(
        auth_client(user),
        f"{BASE}/update-time-entry/",
        {"entity_id": entry.id, "clock_in": iso(END), "clock_out": iso(START)},
    )
    assert resp.status_code == 422
    entry.refresh_from_db()
    assert entry.clock_out == END


@pytest.mark.django_db
def test_update_another_users_entry_returns_404():
    """A user cannot edit someone else's entry."""
    owner = make_user("alice")
    intruder = make_user("bob")
    entry = TimeEntry.objects.create(  # pylint: disable=no-member
        subtask=make_subtask(owner), clock_in=START, clock_out=END
    )

    resp = post(
        auth_client(intruder),
        f"{BASE}/update-time-entry/",
        {"entity_id": entry.id, "clock_in": iso(START), "clock_out": iso(END)},
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_manual_entry_requires_authentication():
    """Unauthenticated requests are rejected."""
    resp = post(
        Client(),
        f"{BASE}/create-time-entry/",
        {"subtask_id": 1, "clock_in": iso(START), "clock_out": iso(END)},
    )
    assert resp.status_code == 401