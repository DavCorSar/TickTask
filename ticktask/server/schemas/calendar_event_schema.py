"""
Definition of the schemas used for the calendar/agenda events.
"""

from datetime import datetime

from ninja import Schema


class CalendarEventSchema(Schema):
    """
    Full representation of a `CalendarEvent` returned by the API.
    """

    id: int
    title: str
    description: str
    start: datetime
    end: datetime | None
    all_day: bool
    color: str
    recurrence: str = ""
    recurrence_until: datetime | None = None


class CalendarOccurrenceSchema(CalendarEventSchema):
    """
    One occurrence of an event as shown on the calendar. ``start``/``end`` are
    the occurrence's; ``series_start``/``series_end`` are the underlying event's
    own times, so the UI can edit the whole series from any occurrence.
    """

    series_start: datetime
    series_end: datetime | None = None


class CalendarEventCreateSchema(Schema):
    """
    Payload required to create a new `CalendarEvent`.
    """

    title: str
    description: str = ""
    start: datetime
    end: datetime | None = None
    all_day: bool = False
    color: str = ""
    recurrence: str = ""
    recurrence_until: datetime | None = None


class CalendarEventUpdateSchema(Schema):
    """
    Payload to partially update a `CalendarEvent`. Only the fields that are
    explicitly provided are applied.
    """

    title: str | None = None
    description: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    all_day: bool | None = None
    color: str | None = None
    recurrence: str | None = None
    recurrence_until: datetime | None = None


class CalendarTimeEntrySchema(Schema):
    """
    A tracked time entry as shown on the calendar, flattened with its
    owning subtask and task names.
    """

    id: int
    clock_in: datetime
    clock_out: datetime | None
    subtask_id: int
    subtask_name: str
    task_id: int
    task_name: str
    deleted: bool = False


class CalendarSchema(Schema):
    """
    Unified calendar payload for a date range: scheduled events (expanded into
    occurrences) plus the time already tracked.
    """

    events: list[CalendarOccurrenceSchema]
    time_entries: list[CalendarTimeEntrySchema]
