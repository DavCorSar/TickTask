"""
Domain operations shared between the HTTP API and the Telegram bot.

These functions own the business rules (ownership scoping, soft-delete checks,
duplicate-name validation, the clock-in/out flow) so the same behaviour is used
whether the user acts through the web API or from a chat. They raise
:class:`ServiceError` (carrying an HTTP-style ``status`` and a user-facing
``message``) instead of framework-specific exceptions; each caller translates
that into its own error shape (``HttpError`` for the API, a reply for the bot).
"""

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.utils import timezone

from ticktask.models import (
    Task,
    SubTask,
    TimeEntry,
    CalendarEvent,
    UserAccessRequest,
)


class ServiceError(Exception):
    """A domain error with an HTTP-style status code and a user-facing message."""

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


# --------------------------------------------------------------------------- #
# Tasks & subtasks
# --------------------------------------------------------------------------- #


def list_active_tasks(user):
    """Returns the user's active (non-deleted) tasks, ordered by name."""
    return list(
        Task.objects.filter(user=user, deleted_at__isnull=True).order_by("name")  # pylint: disable=no-member
    )


def list_active_subtasks(user, task_id: int):
    """Returns the active subtasks of one of the user's tasks, ordered by name."""
    task = _get_owned_task(user, task_id)
    return list(
        task.subtasks.filter(deleted_at__isnull=True).order_by("name")  # pylint: disable=no-member
    )


def create_task(user, name: str) -> Task:
    """
    Creates a task for ``user``. Raises :class:`ServiceError` on an empty name
    (422) or a name already taken by an active or soft-deleted task (409).
    """
    name = (name or "").strip()
    if not name:
        raise ServiceError(422, "El nombre de la tarea no puede estar vacío.")

    existing = Task.objects.filter(user=user, name=name).first()  # pylint: disable=no-member
    if existing is not None:
        if existing.is_deleted:
            raise ServiceError(
                409,
                "Ya existe una tarea eliminada con ese nombre. "
                "Restáurala en lugar de crear una nueva.",
            )
        raise ServiceError(409, "Ya existe una tarea con ese nombre.")

    return Task.objects.create(user=user, name=name)  # pylint: disable=no-member


def create_subtask(user, task_id: int, name: str, description: str = "") -> SubTask:
    """
    Creates a subtask under one of ``user``'s tasks. Raises
    :class:`ServiceError` if the task is missing (404), the name is empty (422),
    or the name clashes with an active/soft-deleted subtask of that task (409).
    """
    task = _get_owned_task(user, task_id)

    name = (name or "").strip()
    if not name:
        raise ServiceError(422, "El nombre de la subtarea no puede estar vacío.")

    existing = SubTask.objects.filter(task=task, name=name).first()  # pylint: disable=no-member
    if existing is not None:
        if existing.is_deleted:
            raise ServiceError(
                409,
                "Ya existe una subtarea eliminada con ese nombre en esta tarea. "
                "Restáurala en lugar de crear una nueva.",
            )
        raise ServiceError(409, "Ya existe una subtarea con ese nombre en esta tarea.")

    return SubTask.objects.create(  # pylint: disable=no-member
        name=name, description=(description or "").strip(), task=task
    )


# --------------------------------------------------------------------------- #
# Clock in / out
# --------------------------------------------------------------------------- #


def get_open_entry(user):
    """Returns the user's currently open time entry (on a live task), or None."""
    return (
        TimeEntry.objects.select_related("subtask__task")  # pylint: disable=no-member
        .filter(
            clock_out__isnull=True,
            subtask__task__user=user,
            subtask__deleted_at__isnull=True,
            subtask__task__deleted_at__isnull=True,
        )
        .first()
    )


def clock_in(user, subtask_id: int) -> TimeEntry:
    """
    Opens a time entry on one of ``user``'s subtasks. Raises
    :class:`ServiceError` if the subtask is missing/not owned (404) or
    soft-deleted (409).
    """
    subtask = _get_owned_subtask(user, subtask_id)
    if subtask.is_deleted or subtask.task.is_deleted:
        raise ServiceError(409, "No se puede fichar en una subtarea eliminada.")
    return TimeEntry.objects.create(subtask=subtask)  # pylint: disable=no-member


def clock_out(user, entry_id: int) -> TimeEntry:
    """
    Closes the given open time entry. Raises :class:`ServiceError` if it does
    not exist, is already closed, or is not the user's (404).
    """
    entry = (
        TimeEntry.objects.select_related("subtask__task")  # pylint: disable=no-member
        .filter(id=entry_id, clock_out__isnull=True, subtask__task__user=user)
        .first()
    )
    if entry is None:
        raise ServiceError(404, "Entrada no encontrada o ya cerrada.")
    entry.clock_out = timezone.now()
    entry.save(update_fields=["clock_out"])
    return entry


# --------------------------------------------------------------------------- #
# Read helpers (for the bot's list commands)
# --------------------------------------------------------------------------- #


def recent_time_entries(user, limit: int = 10):
    """
    Returns the user's most recent time entries (newest first) on live
    tasks/subtasks, with their subtask and task preloaded.
    """
    return list(
        TimeEntry.objects.select_related("subtask__task")  # pylint: disable=no-member
        .filter(
            subtask__task__user=user,
            subtask__deleted_at__isnull=True,
            subtask__task__deleted_at__isnull=True,
        )
        .order_by("-clock_in")[:limit]
    )


def upcoming_events(user, days: int = 7, limit: int = 10):
    """
    Returns the user's upcoming calendar events starting within the next
    ``days`` days (or already ongoing), ordered by start.
    """
    now = timezone.now()
    # Future events, plus ones already ongoing (started but not yet ended).
    not_over_yet = Q(start__gte=now) | Q(end__gte=now)
    return list(
        CalendarEvent.objects.filter(  # pylint: disable=no-member
            not_over_yet, user=user, start__lte=now + timedelta(days=days)
        ).order_by("start")[:limit]
    )


# --------------------------------------------------------------------------- #
# Calendar recurrence
# --------------------------------------------------------------------------- #


def add_recurrence(start: datetime, recurrence: str, n: int) -> datetime:
    """
    Returns the ``n``-th occurrence start of a recurring series, anchored to the
    first occurrence ``start`` (so month/year steps don't drift: monthly from
    Jan 31 gives Feb 28, Mar 31, … instead of creeping earlier each month).
    """
    if recurrence == CalendarEvent.WEEKLY:
        return start + timedelta(weeks=n)
    if recurrence == CalendarEvent.MONTHLY:
        return start + relativedelta(months=n)
    if recurrence == CalendarEvent.YEARLY:
        return start + relativedelta(years=n)
    raise ValueError(f"Unknown recurrence: {recurrence!r}")


def occurrences_between(start, recurrence, until, range_start, range_end):
    """
    Lists the occurrence start datetimes of an event within
    ``[range_start, range_end]`` (inclusive). A non-recurring event yields its
    own ``start`` when it falls in the window. ``until`` (if set) caps the
    series: no occurrence starts after it.
    """
    if not recurrence:
        return [start] if range_start <= start <= range_end else []

    occurrences = []
    n = _lower_bound_index(start, recurrence, range_start)
    guard = 0
    while guard < 2000:
        occ = add_recurrence(start, recurrence, n)
        if occ > range_end:
            break
        if occ >= range_start and (until is None or occ <= until):
            occurrences.append(occ)
        n += 1
        guard += 1
    return occurrences


def _lower_bound_index(start, recurrence, range_start) -> int:
    """
    A safe lower bound for the occurrence index at or before ``range_start``, so
    the caller starts iterating just below the window (never skipping past it).
    """
    if range_start <= start:
        return 0
    if recurrence == CalendarEvent.WEEKLY:
        weeks = (range_start - start).days // 7
        return max(0, weeks - 1)
    if recurrence == CalendarEvent.MONTHLY:
        months = (range_start.year - start.year) * 12 + (range_start.month - start.month)
        return max(0, months - 1)
    if recurrence == CalendarEvent.YEARLY:
        return max(0, range_start.year - start.year - 1)
    return 0


# --------------------------------------------------------------------------- #
# Access requests (self-service signup gate)
# --------------------------------------------------------------------------- #


def approve_access(req: UserAccessRequest) -> None:
    """Approves a pending request and activates the account."""
    req.status = UserAccessRequest.APPROVED
    req.decided_at = timezone.now()
    req.save(update_fields=["status", "decided_at"])
    user = req.user
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])


def reject_access(req: UserAccessRequest) -> None:
    """Rejects a request and keeps the account deactivated."""
    req.status = UserAccessRequest.REJECTED
    req.decided_at = timezone.now()
    req.save(update_fields=["status", "decided_at"])
    user = req.user
    if user.is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])


# --------------------------------------------------------------------------- #
# Internal
# --------------------------------------------------------------------------- #


def _get_owned_task(user, task_id: int) -> Task:
    """Fetches one of ``user``'s tasks or raises a 404 ServiceError."""
    task = Task.objects.filter(id=task_id, user=user).first()  # pylint: disable=no-member
    if task is None:
        raise ServiceError(404, "Tarea no encontrada.")
    return task


def _get_owned_subtask(user, subtask_id: int) -> SubTask:
    """Fetches one of ``user``'s subtasks or raises a 404 ServiceError."""
    subtask = (
        SubTask.objects.select_related("task")  # pylint: disable=no-member
        .filter(id=subtask_id, task__user=user)
        .first()
    )
    if subtask is None:
        raise ServiceError(404, "Subtarea no encontrada.")
    return subtask
