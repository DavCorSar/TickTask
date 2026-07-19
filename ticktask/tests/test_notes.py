"""
Tests for the grouped-notes endpoints: group and note CRUD, ownership scoping,
validation and the group→note cascade.
"""

import json

import pytest
from django.test import Client
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

from ticktask.models import NoteGroup, Note

BASE = "/api/notes/user"


def make_user(username: str = "alice") -> User:
    """Creates a user to own the notes under test."""
    return User.objects.create_user(username=username, password="pw")


def auth_client(user: User) -> Client:
    """Returns a Django test client authenticated as ``user`` via JWT."""
    token = str(RefreshToken.for_user(user).access_token)
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


def post_json(client: Client, path: str, payload: dict):
    """Helper to POST a JSON body."""
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def patch_json(client: Client, path: str, payload: dict):
    """Helper to PATCH a JSON body."""
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


# --------------------------------------------------------------------------- #
# Groups
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_create_group():
    """A valid payload creates a group scoped to the user."""
    user = make_user()
    client = auth_client(user)

    resp = post_json(client, f"{BASE}/create-group/", {"name": "Ideas", "color": "#007CBF"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Ideas"
    assert body["color"] == "#007CBF"
    assert body["notes"] == []
    assert NoteGroup.objects.filter(user=user).count() == 1  # pylint: disable=no-member


@pytest.mark.django_db
def test_create_group_rejects_blank_name():
    """A whitespace-only name is rejected."""
    client = auth_client(make_user())
    resp = post_json(client, f"{BASE}/create-group/", {"name": "   "})
    assert resp.status_code == 422
    assert NoteGroup.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_create_group_rejects_duplicate_name():
    """A name already used by the user is rejected."""
    user = make_user()
    client = auth_client(user)
    NoteGroup.objects.create(user=user, name="Ideas")  # pylint: disable=no-member

    resp = post_json(client, f"{BASE}/create-group/", {"name": "Ideas"})

    assert resp.status_code == 409
    assert NoteGroup.objects.filter(user=user).count() == 1  # pylint: disable=no-member


@pytest.mark.django_db
def test_same_group_name_allowed_across_users():
    """Two different users may each have a group with the same name."""
    alice = make_user("alice")
    bob = make_user("bob")
    NoteGroup.objects.create(user=alice, name="Ideas")  # pylint: disable=no-member

    resp = post_json(auth_client(bob), f"{BASE}/create-group/", {"name": "Ideas"})

    assert resp.status_code == 200


@pytest.mark.django_db
def test_new_groups_are_appended_in_order():
    """Each new group gets an order after the previous ones."""
    user = make_user()
    client = auth_client(user)

    first = post_json(client, f"{BASE}/create-group/", {"name": "A"}).json()
    second = post_json(client, f"{BASE}/create-group/", {"name": "B"}).json()

    assert second["order"] > first["order"]


@pytest.mark.django_db
def test_update_group():
    """A group's name and color can be edited."""
    user = make_user()
    client = auth_client(user)
    group = NoteGroup.objects.create(user=user, name="Ideas")  # pylint: disable=no-member

    resp = patch_json(
        client, f"{BASE}/update-group/{group.id}/", {"name": "Thoughts", "color": "#F59E0B"}
    )

    assert resp.status_code == 200
    group.refresh_from_db()
    assert group.name == "Thoughts"
    assert group.color == "#F59E0B"


@pytest.mark.django_db
def test_update_group_rejects_duplicate_name():
    """Renaming onto another group's name is rejected."""
    user = make_user()
    client = auth_client(user)
    NoteGroup.objects.create(user=user, name="A")  # pylint: disable=no-member
    group = NoteGroup.objects.create(user=user, name="B")  # pylint: disable=no-member

    resp = patch_json(client, f"{BASE}/update-group/{group.id}/", {"name": "A"})

    assert resp.status_code == 409


@pytest.mark.django_db
def test_delete_group_cascades_to_notes():
    """Deleting a group removes the notes it contains."""
    user = make_user()
    client = auth_client(user)
    group = NoteGroup.objects.create(user=user, name="Ideas")  # pylint: disable=no-member
    Note.objects.create(group=group, title="One")  # pylint: disable=no-member

    resp = client.delete(f"{BASE}/delete-group/{group.id}/")

    assert resp.status_code == 200
    assert NoteGroup.objects.count() == 0  # pylint: disable=no-member
    assert Note.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_cannot_touch_another_users_group():
    """Group operations are scoped to the owner."""
    alice = make_user("alice")
    bob = make_user("bob")
    group = NoteGroup.objects.create(user=alice, name="Ideas")  # pylint: disable=no-member

    resp = patch_json(auth_client(bob), f"{BASE}/update-group/{group.id}/", {"name": "X"})

    assert resp.status_code == 404
    group.refresh_from_db()
    assert group.name == "Ideas"


# --------------------------------------------------------------------------- #
# Notes
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_create_note():
    """A note is created inside the given group."""
    user = make_user()
    client = auth_client(user)
    group = NoteGroup.objects.create(user=user, name="Ideas")  # pylint: disable=no-member

    resp = post_json(
        client, f"{BASE}/create-note/", {"group_id": group.id, "title": "Buy milk"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Buy milk"
    assert body["done"] is False
    assert body["group_id"] == group.id


@pytest.mark.django_db
def test_create_note_rejects_blank_title():
    """A whitespace-only title is rejected."""
    user = make_user()
    client = auth_client(user)
    group = NoteGroup.objects.create(user=user, name="Ideas")  # pylint: disable=no-member

    resp = post_json(client, f"{BASE}/create-note/", {"group_id": group.id, "title": "  "})

    assert resp.status_code == 422
    assert Note.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_create_note_in_foreign_group_is_404():
    """A note can't be added to another user's group."""
    alice = make_user("alice")
    bob = make_user("bob")
    group = NoteGroup.objects.create(user=alice, name="Ideas")  # pylint: disable=no-member

    resp = post_json(
        auth_client(bob), f"{BASE}/create-note/", {"group_id": group.id, "title": "X"}
    )

    assert resp.status_code == 404
    assert Note.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_update_note_fields():
    """Title, body and done can be edited."""
    user = make_user()
    client = auth_client(user)
    group = NoteGroup.objects.create(user=user, name="Ideas")  # pylint: disable=no-member
    note = Note.objects.create(group=group, title="Old")  # pylint: disable=no-member

    resp = patch_json(
        client,
        f"{BASE}/update-note/{note.id}/",
        {"title": "New", "body": "details", "done": True},
    )

    assert resp.status_code == 200
    note.refresh_from_db()
    assert note.title == "New"
    assert note.body == "details"
    assert note.done is True


@pytest.mark.django_db
def test_toggle_note_flips_done():
    """Toggling flips the done flag each time."""
    user = make_user()
    client = auth_client(user)
    group = NoteGroup.objects.create(user=user, name="Ideas")  # pylint: disable=no-member
    note = Note.objects.create(group=group, title="Task")  # pylint: disable=no-member

    resp = client.post(f"{BASE}/toggle-note/{note.id}/")
    assert resp.status_code == 200
    note.refresh_from_db()
    assert note.done is True

    client.post(f"{BASE}/toggle-note/{note.id}/")
    note.refresh_from_db()
    assert note.done is False


@pytest.mark.django_db
def test_delete_note():
    """A note can be deleted, leaving its group in place."""
    user = make_user()
    client = auth_client(user)
    group = NoteGroup.objects.create(user=user, name="Ideas")  # pylint: disable=no-member
    note = Note.objects.create(group=group, title="Task")  # pylint: disable=no-member

    resp = client.delete(f"{BASE}/delete-note/{note.id}/")

    assert resp.status_code == 200
    assert Note.objects.count() == 0  # pylint: disable=no-member
    assert NoteGroup.objects.filter(id=group.id).exists()  # pylint: disable=no-member


@pytest.mark.django_db
def test_cannot_toggle_another_users_note():
    """Note operations are scoped to the owner."""
    alice = make_user("alice")
    bob = make_user("bob")
    group = NoteGroup.objects.create(user=alice, name="Ideas")  # pylint: disable=no-member
    note = Note.objects.create(group=group, title="Task")  # pylint: disable=no-member

    resp = auth_client(bob).post(f"{BASE}/toggle-note/{note.id}/")

    assert resp.status_code == 404
    note.refresh_from_db()
    assert note.done is False


# --------------------------------------------------------------------------- #
# Listing
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_get_notes_returns_groups_with_nested_notes():
    """The list endpoint nests each group's notes and scopes to the user."""
    alice = make_user("alice")
    bob = make_user("bob")
    group = NoteGroup.objects.create(user=alice, name="Ideas")  # pylint: disable=no-member
    Note.objects.create(group=group, title="One", order=1)  # pylint: disable=no-member
    Note.objects.create(group=group, title="Two", order=2)  # pylint: disable=no-member
    NoteGroup.objects.create(user=bob, name="Bob's")  # pylint: disable=no-member

    resp = auth_client(alice).get(f"{BASE}/get-notes/")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Ideas"
    assert [n["title"] for n in body[0]["notes"]] == ["One", "Two"]
