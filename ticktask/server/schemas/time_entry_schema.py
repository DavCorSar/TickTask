"""
Definiton of the schemas used for the time entries.
"""

from datetime import datetime

from ninja import Schema


class ClockInSchema(Schema):
    """
    Model used to store the necessary data when clocking in.
    """

    subtask_id: int


class ClockOutSchema(Schema):
    """
    Model used to store the necessary data when clocking out.
    """

    entity_id: int


class TimeEntrySchema(Schema):
    """
    Model used to store all the data associated with a `TimeEntry`.
    """

    id: int
    clock_in: datetime
    clock_out: datetime | None


class TimeEntryHistoryRequestSchema(Schema):
    """
    Schema used to request the last time entries of
    a given `SubTask` during the past `last_hours`.
    """

    subtask_id: int
    last_hours: int


class TimeEntryCreateSchema(Schema):
    """
    Payload to manually log a completed time entry on a subtask.
    """

    subtask_id: int
    clock_in: datetime
    clock_out: datetime


class TimeEntryUpdateSchema(Schema):
    """
    Payload to edit the start/end of an existing time entry.
    """

    entity_id: int
    clock_in: datetime
    clock_out: datetime


class HistoryEntrySchema(Schema):
    """
    A time entry as shown on the history page: flattened with the names of its
    owning subtask and task, and whether either of them is soft-deleted.
    """

    id: int
    clock_in: datetime
    clock_out: datetime | None
    subtask_id: int
    subtask_name: str
    task_id: int
    task_name: str
    deleted: bool = False
