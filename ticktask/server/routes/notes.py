"""
Endpoints to manage the user's grouped notes (pending items).

Business rules live in :mod:`ticktask.services` (shared with the Telegram bot);
these routes only scope to ``request.auth`` and translate a domain
:class:`ServiceError` into a Ninja ``HttpError``.
"""

import os

import django
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.notes_schema import (
    NoteSchema,
    NoteGroupSchema,
    NoteGroupCreateSchema,
    NoteGroupUpdateSchema,
    NoteCreateSchema,
    NoteUpdateSchema,
)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
except RuntimeError:
    pass

from ticktask import services

notes_router = Router()


def _raise_http(exc: services.ServiceError):
    """Translates a domain :class:`ServiceError` into a Ninja ``HttpError``."""
    raise HttpError(exc.status, exc.message)


@notes_router.get(
    "/user/get-notes/",
    response=list[NoteGroupSchema],
    tags=["Notes"],
    auth=JWTAuth(),
)
def get_notes(request):
    """Returns the user's note groups (ordered) with their notes nested."""
    return services.list_note_groups(request.auth)


@notes_router.post(
    "/user/create-group/",
    response=NoteGroupSchema,
    tags=["Notes"],
    auth=JWTAuth(),
)
def create_group(request, data: NoteGroupCreateSchema):
    """Creates a new note group for the authenticated user."""
    try:
        return services.create_note_group(request.auth, data.name, data.color)
    except services.ServiceError as exc:
        _raise_http(exc)


@notes_router.patch(
    "/user/update-group/{group_id}/",
    response=NoteGroupSchema,
    tags=["Notes"],
    auth=JWTAuth(),
)
def update_group(request, group_id: int, data: NoteGroupUpdateSchema):
    """Partially updates one of the user's note groups (name and/or color)."""
    try:
        return services.update_note_group(
            request.auth, group_id, name=data.name, color=data.color
        )
    except services.ServiceError as exc:
        _raise_http(exc)


@notes_router.delete(
    "/user/delete-group/{group_id}/",
    response={200: dict},
    tags=["Notes"],
    auth=JWTAuth(),
)
def delete_group(request, group_id: int):
    """Deletes one of the user's groups and all the notes it contains."""
    try:
        services.delete_note_group(request.auth, group_id)
    except services.ServiceError as exc:
        _raise_http(exc)
    return {"success": True}


@notes_router.post(
    "/user/create-note/",
    response=NoteSchema,
    tags=["Notes"],
    auth=JWTAuth(),
)
def create_note(request, data: NoteCreateSchema):
    """Creates a new note inside one of the user's groups."""
    try:
        return services.create_note(
            request.auth, data.group_id, data.title, data.body
        )
    except services.ServiceError as exc:
        _raise_http(exc)


@notes_router.patch(
    "/user/update-note/{note_id}/",
    response=NoteSchema,
    tags=["Notes"],
    auth=JWTAuth(),
)
def update_note(request, note_id: int, data: NoteUpdateSchema):
    """Partially updates one of the user's notes (title, body and/or done)."""
    try:
        return services.update_note(
            request.auth, note_id, title=data.title, body=data.body, done=data.done
        )
    except services.ServiceError as exc:
        _raise_http(exc)


@notes_router.post(
    "/user/toggle-note/{note_id}/",
    response=NoteSchema,
    tags=["Notes"],
    auth=JWTAuth(),
)
def toggle_note(request, note_id: int):
    """Flips the ``done`` flag of one of the user's notes."""
    try:
        return services.toggle_note(request.auth, note_id)
    except services.ServiceError as exc:
        _raise_http(exc)


@notes_router.delete(
    "/user/delete-note/{note_id}/",
    response={200: dict},
    tags=["Notes"],
    auth=JWTAuth(),
)
def delete_note(request, note_id: int):
    """Deletes one of the user's notes."""
    try:
        services.delete_note(request.auth, note_id)
    except services.ServiceError as exc:
        _raise_http(exc)
    return {"success": True}
