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
from ticktask.models import CalendarEvent, TimeEntry

calendar_router = Router()


def _validate_range(start: datetime, end: datetime | None) -> None:
    """
    Ensures the event end (when present) is not before its start.
    """
    if end is not None and end < start:
        raise HttpError(422, "The event end cannot be before its start.")


def _events_in_range(user, start: datetime, end: datetime):
    """
    Returns the user's events overlapping the ``[start, end]`` window.
    """
    return (
        CalendarEvent.objects.filter(user=user)  # pylint: disable=no-member
        .filter(
            Q(start__lte=end)
            & (Q(end__gte=start) | Q(end__isnull=True, start__gte=start))
        )
        .order_by("start")
    )


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

    return CalendarEvent.objects.create(  # pylint: disable=no-member
        user=request.auth,
        title=data.title.strip(),
        description=data.description.strip(),
        start=data.start,
        end=data.end,
        all_day=data.all_day,
        color=data.color.strip(),
    )


@calendar_router.get(
    "/user/get-events/",
    response=list[CalendarEventSchema],
    tags=["Calendar"],
    auth=JWTAuth(),
)
def get_events(request, start: datetime, end: datetime):
    """
    Returns the events of the authenticated user that overlap the
    ``[start, end]`` window.
    """
    return _events_in_range(request.auth, start, end)


@calendar_router.get(
    "/user/get-calendar/",
    response=CalendarSchema,
    tags=["Calendar"],
    auth=JWTAuth(),
)
def get_calendar(request, start: datetime, end: datetime):
    """
    Returns, for the ``[start, end]`` window, the user's scheduled events
    together with the time entries already tracked in that range.
    """
    entries = (
        TimeEntry.objects.select_related("subtask__task")  # pylint: disable=no-member
        .filter(subtask__task__user=request.auth, clock_in__lte=end)
        .filter(Q(clock_out__gte=start) | Q(clock_out__isnull=True))
        .order_by("clock_in")
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
        }
        for entry in entries
    ]

    return {
        "events": list(_events_in_range(request.auth, start, end)),
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
    for attr, value in payload.items():
        setattr(event, attr, value)

    _validate_range(event.start, event.end)
    event.save()
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
