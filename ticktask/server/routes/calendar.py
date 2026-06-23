"""
Endpoints to manage the user's calendar/agenda events.
"""

import os
from datetime import datetime

import django
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.calendar_event_schema import (
    CalendarEventSchema,
    CalendarOccurrenceSchema,
    CalendarEventCreateSchema,
    CalendarEventUpdateSchema,
    CalendarSchema,
)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
except RuntimeError:
    pass

from django.db.models import Q
from ticktask import services
from ticktask.models import CalendarEvent, TimeEntry, SentReminder

calendar_router = Router()

VALID_RECURRENCES = {choice for choice, _ in CalendarEvent.RECURRENCE_CHOICES}


def _validate_range(start: datetime, end: datetime | None) -> None:
    """
    Ensures the event end (when present) is not before its start.
    """
    if end is not None and end < start:
        raise HttpError(422, "The event end cannot be before its start.")


def _validate_title(title: str) -> None:
    """
    Ensures the event title is not blank once surrounding whitespace is stripped.
    """
    if not title:
        raise HttpError(422, "The event title cannot be empty.")


def _validate_recurrence(
    recurrence: str, start: datetime, until: datetime | None
) -> None:
    """Validates the recurrence kind and its optional cut-off date."""
    if recurrence not in VALID_RECURRENCES:
        raise HttpError(422, "Invalid recurrence.")
    if until is not None:
        if not recurrence:
            raise HttpError(
                422, "A repeat-until date only applies to a recurring event."
            )
        if until < start:
            raise HttpError(422, "The repeat-until date cannot be before the start.")


def _events_in_range(user, start: datetime, end: datetime):
    """
    Returns the user's event rows relevant to ``[start, end]``: one-off events
    that overlap the window, plus any recurring series that started on or before
    the window and hasn't ended before it (occurrences are expanded separately).
    """
    one_off = Q(recurrence="") & Q(start__lte=end) & (
        Q(end__gte=start) | Q(end__isnull=True, start__gte=start)
    )
    recurring = (
        ~Q(recurrence="")
        & Q(start__lte=end)
        & (Q(recurrence_until__isnull=True) | Q(recurrence_until__gte=start))
    )
    return (
        CalendarEvent.objects.filter(user=user)  # pylint: disable=no-member
        .filter(one_off | recurring)
        .order_by("start")
    )


def _expand_events(user, start: datetime, end: datetime) -> list[dict]:
    """
    Expands the relevant events into occurrence dicts within ``[start, end]``,
    each carrying its own ``series_start``/``series_end`` so the UI can edit the
    whole series. Sorted by occurrence start.
    """
    occurrences: list[dict] = []
    for event in _events_in_range(user, start, end):
        duration = (event.end - event.start) if event.end else None
        # One-off events already passed the overlap filter, so keep them as-is
        # (their start may sit just before the window). Recurring events are
        # expanded to the occurrences whose start falls inside the window.
        if not event.recurrence:
            occ_starts = [event.start]
        else:
            occ_starts = services.occurrences_between(
                event.start, event.recurrence, event.recurrence_until, start, end
            )
        for occ_start in occ_starts:
            occurrences.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "start": occ_start,
                    "end": (occ_start + duration) if duration else None,
                    "all_day": event.all_day,
                    "color": event.color,
                    "recurrence": event.recurrence,
                    "recurrence_until": event.recurrence_until,
                    "series_start": event.start,
                    "series_end": event.end,
                }
            )
    occurrences.sort(key=lambda occ: occ["start"])
    return occurrences


@calendar_router.post(
    "/user/create-event/",
    response=CalendarEventSchema,
    tags=["Calendar"],
    auth=JWTAuth(),
)
def create_event(request, data: CalendarEventCreateSchema):
    """
    Creates a new calendar event for the authenticated user.
    """
    _validate_range(data.start, data.end)
    title = data.title.strip()
    _validate_title(title)
    _validate_recurrence(data.recurrence, data.start, data.recurrence_until)

    return CalendarEvent.objects.create(  # pylint: disable=no-member
        user=request.auth,
        title=title,
        description=data.description.strip(),
        start=data.start,
        end=data.end,
        all_day=data.all_day,
        color=data.color.strip(),
        recurrence=data.recurrence,
        recurrence_until=data.recurrence_until,
    )


@calendar_router.get(
    "/user/get-events/",
    response=list[CalendarOccurrenceSchema],
    tags=["Calendar"],
    auth=JWTAuth(),
)
def get_events(request, start: datetime, end: datetime):
    """
    Returns the authenticated user's event occurrences within the
    ``[start, end]`` window (recurring events expanded).
    """
    return _expand_events(request.auth, start, end)


@calendar_router.get(
    "/user/get-calendar/",
    response=CalendarSchema,
    tags=["Calendar"],
    auth=JWTAuth(),
)
def get_calendar(
    request, start: datetime, end: datetime, include_deleted: bool = False
):
    """
    Returns, for the ``[start, end]`` window, the user's scheduled events
    together with the time entries already tracked in that range. Entries whose
    subtask or task has been soft-deleted are excluded unless ``include_deleted``
    is set, in which case they are returned flagged with ``deleted: true``.
    """
    entries = (
        TimeEntry.objects.select_related("subtask__task")  # pylint: disable=no-member
        .filter(subtask__task__user=request.auth, clock_in__lte=end)
        .filter(Q(clock_out__gte=start) | Q(clock_out__isnull=True))
        .order_by("clock_in")
    )
    if not include_deleted:
        entries = entries.filter(
            subtask__deleted_at__isnull=True, subtask__task__deleted_at__isnull=True
        )

    time_entries = [
        {
            "id": entry.id,
            "clock_in": entry.clock_in,
            "clock_out": entry.clock_out,
            "subtask_id": entry.subtask_id,
            "subtask_name": entry.subtask.name,
            "task_id": entry.subtask.task_id,
            "task_name": entry.subtask.task.name,
            "deleted": entry.subtask.is_deleted or entry.subtask.task.is_deleted,
        }
        for entry in entries
    ]

    return {
        "events": _expand_events(request.auth, start, end),
        "time_entries": time_entries,
    }


@calendar_router.patch(
    "/user/update-event/{event_id}/",
    response=CalendarEventSchema,
    tags=["Calendar"],
    auth=JWTAuth(),
)
def update_event(request, event_id: int, data: CalendarEventUpdateSchema):
    """
    Partially updates one of the user's events.
    """
    try:
        event = CalendarEvent.objects.get(  # pylint: disable=no-member
            id=event_id, user=request.auth
        )
    except CalendarEvent.DoesNotExist:  # pylint: disable=no-member
        raise HttpError(404, "Event not found.")

    payload = data.dict(exclude_unset=True)
    for field in ("title", "description", "color"):
        if field in payload and payload[field] is not None:
            payload[field] = payload[field].strip()
    if "title" in payload and payload["title"] is not None:
        _validate_title(payload["title"])
    # Don't let an explicit null wipe the recurrence kind (it can't be None).
    if payload.get("recurrence") is None:
        payload.pop("recurrence", None)
    for attr, value in payload.items():
        setattr(event, attr, value)

    _validate_range(event.start, event.end)
    _validate_recurrence(event.recurrence, event.start, event.recurrence_until)
    event.save()
    # The event may have moved in time, so any reminders already sent for it no
    # longer apply — drop them so the scheduler reconsiders the new times.
    SentReminder.objects.filter(event=event).delete()  # pylint: disable=no-member
    return event


@calendar_router.delete(
    "/user/delete-event/{event_id}/",
    response={200: dict},
    tags=["Calendar"],
    auth=JWTAuth(),
)
def delete_event(request, event_id: int):
    """
    Deletes one of the user's events.
    """
    deleted, _ = CalendarEvent.objects.filter(  # pylint: disable=no-member
        id=event_id, user=request.auth
    ).delete()
    if not deleted:
        raise HttpError(404, "Event not found.")
    return {"success": True}
