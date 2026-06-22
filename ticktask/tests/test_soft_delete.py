"""
Tests for soft-deleting (and restoring) tasks and subtasks, the uniqueness
rules around deleted rows, and how deleted items are filtered across the time
tracking, dashboard and calendar endpoints.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from django.test import Client
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

from ticktask.models import Task, SubTask, TimeEntry

TT = "/api/ticktask/user"
DASH = "/api/dashboard/user"
CAL = "/api/calendar/user"


def make_user(username: str = "alice") -> User:
    """Creates a user that owns the tasks under test."""
    return User.objects.create_user(username=username, password="pw")


def auth_client(user: User) -> Client:
    """Returns a Django test client authenticated as ``user`` via JWT."""
    token = str(RefreshToken.for_user(user).access_token)
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


def post(client: Client, path: str, payload: dict):
    """POSTs a JSON body."""
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def closed_entry(subtask: SubTask, clock_in: datetime, clock_out: datetime) -> TimeEntry:
    """Creates a closed time entry with explicit timestamps (clock_in is auto)."""
    entry = TimeEntry.objects.create(subtask=subtask)  # pylint: disable=no-member
    TimeEntry.objects.filter(id=entry.id).update(  # pylint: disable=no-member
        clock_in=clock_in, clock_out=clock_out
    )
    return entry


def task_names(client: Client) -> set:
    """Task names visible in time tracking."""
    resp = client.get(f"{TT}/get-tasks-and-subtasks/")
    return {t["name"] for t in resp.json()}


# --------------------------------------------------------------------------- #
# Time tracking visibility
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_deleted_task_disappears_from_time_tracking():
    """A soft-deleted task is gone from the time-tracking tree."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="Gone")  # pylint: disable=no-member

    assert post(client, f"{TT}/delete-task/", {"task_id": task.id}).status_code == 200

    assert task_names(client) == set()
    task.refresh_from_db()
    assert task.is_deleted  # the row is kept (soft delete)


@pytest.mark.django_db
def test_deleted_subtask_disappears_but_task_stays():
    """Deleting a subtask hides it; its task and siblings remain."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="T")  # pylint: disable=no-member
    gone = SubTask.objects.create(task=task, name="gone", description="d")  # pylint: disable=no-member
    SubTask.objects.create(task=task, name="kept", description="d")  # pylint: disable=no-member

    post(client, f"{TT}/delete-subtask/", {"subtask_id": gone.id})

    tree = client.get(f"{TT}/get-tasks-and-subtasks/").json()
    assert len(tree) == 1
    assert {s["name"] for s in tree[0]["subtasks"]} == {"kept"}


@pytest.mark.django_db
def test_delete_closes_open_time_entry():
    """Deleting a task closes any still-open entry beneath it."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="T")  # pylint: disable=no-member
    subtask = SubTask.objects.create(task=task, name="s", description="d")  # pylint: disable=no-member
    entry = TimeEntry.objects.create(subtask=subtask)  # pylint: disable=no-member
    assert entry.clock_out is None

    post(client, f"{TT}/delete-task/", {"task_id": task.id})

    entry.refresh_from_db()
    assert entry.clock_out is not None


@pytest.mark.django_db
def test_cannot_clock_in_on_deleted_subtask():
    """Clocking in on a deleted subtask is rejected."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="T")  # pylint: disable=no-member
    subtask = SubTask.objects.create(task=task, name="s", description="d")  # pylint: disable=no-member
    post(client, f"{TT}/delete-subtask/", {"subtask_id": subtask.id})

    resp = post(client, f"{TT}/clock-in/", {"subtask_id": subtask.id})
    assert resp.status_code == 409


@pytest.mark.django_db
def test_delete_task_scoped_to_user():
    """A user cannot delete another user's task."""
    owner = make_user("alice")
    intruder = make_user("bob")
    task = Task.objects.create(user=owner, name="Owned")  # pylint: disable=no-member

    resp = post(auth_client(intruder), f"{TT}/delete-task/", {"task_id": task.id})
    assert resp.status_code == 404
    task.refresh_from_db()
    assert not task.is_deleted


# --------------------------------------------------------------------------- #
# Restore
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_restore_task_brings_it_back():
    """Restoring a deleted task makes it visible again."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="Back")  # pylint: disable=no-member
    post(client, f"{TT}/delete-task/", {"task_id": task.id})
    assert task_names(client) == set()

    resp = post(client, f"{TT}/restore-task/", {"task_id": task.id})
    assert resp.status_code == 200
    assert task_names(client) == {"Back"}


@pytest.mark.django_db
def test_restore_subtask_brings_it_back():
    """Restoring a deleted subtask makes it visible again."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="T")  # pylint: disable=no-member
    subtask = SubTask.objects.create(task=task, name="s", description="d")  # pylint: disable=no-member
    post(client, f"{TT}/delete-subtask/", {"subtask_id": subtask.id})

    post(client, f"{TT}/restore-subtask/", {"subtask_id": subtask.id})

    tree = client.get(f"{TT}/get-tasks-and-subtasks/").json()
    assert {s["name"] for s in tree[0]["subtasks"]} == {"s"}


# --------------------------------------------------------------------------- #
# Uniqueness (deleted rows keep their name reserved)
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_duplicate_active_task_name_rejected():
    """Two active tasks cannot share a name (same user)."""
    user = make_user()
    client = auth_client(user)
    post(client, f"{TT}/create-task/", {"name": "Dup"})

    resp = post(client, f"{TT}/create-task/", {"name": "Dup"})
    assert resp.status_code == 409
    assert "eliminada" not in resp.json()["detail"]


@pytest.mark.django_db
def test_duplicate_with_deleted_task_mentions_it_is_deleted():
    """Colliding with a deleted task is reported as such."""
    user = make_user()
    client = auth_client(user)
    created = post(client, f"{TT}/create-task/", {"name": "Dup"}).json()
    post(client, f"{TT}/delete-task/", {"task_id": created["id"]})

    resp = post(client, f"{TT}/create-task/", {"name": "Dup"})
    assert resp.status_code == 409
    assert "eliminada" in resp.json()["detail"]


@pytest.mark.django_db
def test_duplicate_subtask_within_task_rejected_and_flags_deleted():
    """Subtask names are unique within a task; deleted ones still collide."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="T")  # pylint: disable=no-member

    post(client, f"{TT}/create-subtask/", {"task_id": task.id, "name": "S", "description": ""})
    dup = post(client, f"{TT}/create-subtask/", {"task_id": task.id, "name": "S", "description": ""})
    assert dup.status_code == 409
    assert "eliminada" not in dup.json()["detail"]

    sub = SubTask.objects.get(task=task, name="S")  # pylint: disable=no-member
    post(client, f"{TT}/delete-subtask/", {"subtask_id": sub.id})
    dup2 = post(client, f"{TT}/create-subtask/", {"task_id": task.id, "name": "S", "description": ""})
    assert dup2.status_code == 409
    assert "eliminada" in dup2.json()["detail"]


@pytest.mark.django_db
def test_same_subtask_name_allowed_in_different_tasks():
    """The same subtask name is fine under a different task."""
    user = make_user()
    client = auth_client(user)
    task_a = Task.objects.create(user=user, name="A")  # pylint: disable=no-member
    task_b = Task.objects.create(user=user, name="B")  # pylint: disable=no-member

    r1 = post(client, f"{TT}/create-subtask/", {"task_id": task_a.id, "name": "S", "description": ""})
    r2 = post(client, f"{TT}/create-subtask/", {"task_id": task_b.id, "name": "S", "description": ""})
    assert r1.status_code == 200
    assert r2.status_code == 200


# --------------------------------------------------------------------------- #
# Dashboard / calendar visibility
# --------------------------------------------------------------------------- #


def _range():
    return (
        datetime(2026, 3, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 2, 0, tzinfo=timezone.utc),
    )


@pytest.mark.django_db
def test_dashboard_hides_deleted_task_by_default_and_can_include_it():
    """A deleted task is dropped from the series unless include_deleted is set."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="Old")  # pylint: disable=no-member
    subtask = SubTask.objects.create(task=task, name="s", description="d")  # pylint: disable=no-member
    closed_entry(subtask, datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
                 datetime(2026, 3, 1, 10, tzinfo=timezone.utc))
    task.deleted_at = datetime(2026, 3, 1, 12, tzinfo=timezone.utc)
    task.save(update_fields=["deleted_at"])
    start, end = _range()

    default = client.get(
        f"{DASH}/get-time-series/", {"start": start.isoformat(), "end": end.isoformat()}
    ).json()
    assert default["by_task"] == []

    included = client.get(
        f"{DASH}/get-time-series/",
        {"start": start.isoformat(), "end": end.isoformat(), "include_deleted": "true"},
    ).json()
    assert len(included["by_task"]) == 1
    assert included["by_task"][0]["task_name"] == "Old"
    assert included["by_task"][0]["deleted"] is True


@pytest.mark.django_db
def test_calendar_hides_deleted_entries_by_default_and_can_include_them():
    """Tracked time of a deleted subtask is hidden unless include_deleted is set."""
    user = make_user()
    client = auth_client(user)
    task = Task.objects.create(user=user, name="T")  # pylint: disable=no-member
    subtask = SubTask.objects.create(task=task, name="s", description="d")  # pylint: disable=no-member
    closed_entry(subtask, datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
                 datetime(2026, 3, 1, 10, tzinfo=timezone.utc))
    subtask.deleted_at = datetime(2026, 3, 1, 12, tzinfo=timezone.utc)
    subtask.save(update_fields=["deleted_at"])
    start, end = _range()

    default = client.get(
        f"{CAL}/get-calendar/", {"start": start.isoformat(), "end": end.isoformat()}
    ).json()
    assert default["time_entries"] == []

    included = client.get(
        f"{CAL}/get-calendar/",
        {"start": start.isoformat(), "end": end.isoformat(), "include_deleted": "true"},
    ).json()
    assert len(included["time_entries"]) == 1
    assert included["time_entries"][0]["deleted"] is True
