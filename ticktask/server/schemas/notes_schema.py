"""
Definition of the schemas used for the grouped notes feature.
"""

from datetime import datetime

from ninja import Schema


class NoteSchema(Schema):
    """
    Full representation of a `Note` returned by the API.
    """

    id: int
    group_id: int
    title: str
    body: str
    done: bool
    order: int
    created_at: datetime
    updated_at: datetime


class NoteGroupSchema(Schema):
    """
    A `NoteGroup` with its notes nested (ordered).
    """

    id: int
    name: str
    color: str
    order: int
    notes: list[NoteSchema]


class NoteGroupCreateSchema(Schema):
    """
    Payload to create a new `NoteGroup`.
    """

    name: str
    color: str = ""


class NoteGroupUpdateSchema(Schema):
    """
    Payload to partially update a `NoteGroup`. Only the fields explicitly
    provided are applied.
    """

    name: str | None = None
    color: str | None = None


class NoteCreateSchema(Schema):
    """
    Payload to create a new `Note` inside a group.
    """

    group_id: int
    title: str
    body: str = ""


class NoteUpdateSchema(Schema):
    """
    Payload to partially update a `Note`. Only the fields explicitly provided
    are applied.
    """

    title: str | None = None
    body: str | None = None
    done: bool | None = None
