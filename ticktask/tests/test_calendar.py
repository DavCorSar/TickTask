"""
Tests for the calendar/agenda event endpoints.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from django.test import Client
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

from ticktask.models import CalendarEvent

BASE = "/api/calendar/user"


def make_user(username: str = "alice") -> User:
    """Creates a user to own the events under test."""
    return User.objects.create_user(username=username, password="pw")


def auth_client(user: User) -> Client:
    """Returns a Django test client authenticated as ``user`` via JWT."""
    token = str(RefreshToken.for_user(user).access_token)
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


def iso(dt: datetime) -> str:
    """Serializes a datetime to ISO 8601."""
    return dt.isoformat()


def post_json(client: Client, path: str, payload: dict):
    """Helper to POST a JSON body."""
    return client.post(path, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
def test_create_event():
    """A valid payload creates an event scoped to the user."""
    user = make_user()
    client = auth_client(user)
    start = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)

    resp = post_json(
        client,
        f"{BASE}/create-event/",
        {"title": "Dentist", "start": iso(start), "color": "#5EA611"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Dentist"
    assert body["all_day"] is False
    assert body["end"] is None
    assert CalendarEvent.objects.filter(user=user).count() == 1  # pylint: disable=no-member


@pytest.mark.django_db
def test_create_event_rejects_end_before_start():
    """An end earlier than the start is rejected."""
    user = make_user()
    client = auth_client(user)
    start = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)

    resp = post_json(
        client,
        f"{BASE}/create-event/",
        {"title": "Bad", "start": iso(start), "end": iso(start - timedelta(hours=1))},
    )

    assert resp.status_code == 422
    assert CalendarEvent.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_get_events_filters_by_range():
    """Only events overlapping the requested window are returned."""
    user = make_user()
    client = auth_client(user)

    def create(title, start, end):
        CalendarEvent.objects.create(  # pylint: disable=no-member
            user=user, title=title, start=start, end=end
        )

    create("inside", datetime(2026, 7, 1, 9, tzinfo=timezone.utc),
           datetime(2026, 7, 1, 10, tzinfo=timezone.utc))
    create("overlaps-start", datetime(2026, 6, 30, 23, tzinfo=timezone.utc),
           datetime(2026, 7, 1, 0, 30, tzinfo=timezone.utc))
    create("after", datetime(2026, 7, 5, 9, tzinfo=timezone.utc), None)
    create("open-inside", datetime(2026, 7, 1, 12, tzinfo=timezone.utc), None)
    create("before", datetime(2026, 6, 1, 9, tzinfo=timezone.utc), None)

    resp = client.get(
        f"{BASE}/get-events/",
        {
            "start": iso(datetime(2026, 7, 1, 0, tzinfo=timezone.utc)),
            "end": iso(datetime(2026, 7, 2, 0, tzinfo=timezone.utc)),
        },
    )

    assert resp.status_code == 200
    titles = {e["title"] for e in resp.json()}
    assert titles == {"inside", "overlaps-start", "open-inside"}


@pytest.mark.django_db
def test_get_events_only_returns_own_events():
    """Events from other users are never returned."""
    user = make_user("alice")
    other = make_user("bob")
    CalendarEvent.objects.create(  # pylint: disable=no-member
        user=other, title="secret", start=datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    )

    resp = auth_client(user).get(
        f"{BASE}/get-events/",
        {
            "start": iso(datetime(2026, 7, 1, 0, tzinfo=timezone.utc)),
            "end": iso(datetime(2026, 7, 2, 0, tzinfo=timezone.utc)),
        },
    )

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_update_event():
    """A partial update only changes the provided fields."""
    user = make_user()
    event = CalendarEvent.objects.create(  # pylint: disable=no-member
        user=user, title="Old", start=datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    )
    new_end = datetime(2026, 7, 1, 10, tzinfo=timezone.utc)

    resp = auth_client(user).patch(
        f"{BASE}/update-event/{event.id}/",
        data=json.dumps({"title": "New", "end": iso(new_end)}),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New"
    event.refresh_from_db()
    assert event.title == "New"
    assert event.end == new_end


@pytest.mark.django_db
def test_update_event_of_another_user_returns_404():
    """A user cannot update an event they do not own."""
    owner = make_user("alice")
    intruder = make_user("bob")
    event = CalendarEvent.objects.create(  # pylint: disable=no-member
        user=owner, title="Owned", start=datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    )

    resp = auth_client(intruder).patch(
        f"{BASE}/update-event/{event.id}/",
        data=json.dumps({"title": "Hacked"}),
        content_type="application/json",
    )

    assert resp.status_code == 404
    event.refresh_from_db()
    assert event.title == "Owned"


@pytest.mark.django_db
def test_delete_event():
    """An event can be deleted by its owner."""
    user = make_user()
    event = CalendarEvent.objects.create(  # pylint: disable=no-member
        user=user, title="Bye", start=datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    )

    resp = auth_client(user).delete(f"{BASE}/delete-event/{event.id}/")

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    assert CalendarEvent.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_delete_event_of_another_user_returns_404():
    """Deleting someone else's event fails and leaves it intact."""
    owner = make_user("alice")
    intruder = make_user("bob")
    event = CalendarEvent.objects.create(  # pylint: disable=no-member
        user=owner, title="Owned", start=datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    )

    resp = auth_client(intruder).delete(f"{BASE}/delete-event/{event.id}/")

    assert resp.status_code == 404
    assert CalendarEvent.objects.filter(id=event.id).exists()  # pylint: disable=no-member


@pytest.mark.django_db
def test_endpoints_require_authentication():
    """Unauthenticated requests are rejected."""
    resp = Client().get(
        f"{BASE}/get-events/",
        {
            "start": iso(datetime(2026, 7, 1, 0, tzinfo=timezone.utc)),
            "end": iso(datetime(2026, 7, 2, 0, tzinfo=timezone.utc)),
        },
    )
    assert resp.status_code == 401
