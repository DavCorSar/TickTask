"""
Domain operations shared between the HTTP API and the Telegram bot.

These functions own the business rules (ownership scoping, soft-delete checks,
duplicate-name validation, the clock-in/out flow) so the same behaviour is used
whether the user acts through the web API or from a chat. They raise
:class:`ServiceError` (carrying an HTTP-style ``status`` and a user-facing
``message``) instead of framework-specific exceptions; each caller translates
that into its own error shape (``HttpError`` for the API, a reply for the bot).
"""

from datetime import date, datetime, timedelta

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
    Returns ``(entries, total)``: the user's most recent time entries (newest
    first, capped at ``limit``) on live tasks/subtasks with their subtask and
    task preloaded, plus the total number available (for a "and N more" hint).
    """
    qs = (
        TimeEntry.objects.select_related("subtask__task")  # pylint: disable=no-member
        .filter(
            subtask__task__user=user,
            subtask__deleted_at__isnull=True,
            subtask__task__deleted_at__isnull=True,
        )
        .order_by("-clock_in")
    )
    return list(qs[:limit]), qs.count()


def upcoming_events(user, days: int = 7, limit: int = 10):
    """
    Returns ``(events, total)``: the user's upcoming calendar events starting
    within the next ``days`` days (or already ongoing), ordered by start and
    capped at ``limit``, plus the total number available.
    """
    now = timezone.now()
    # Future events, plus ones already ongoing (started but not yet ended).
    not_over_yet = Q(start__gte=now) | Q(end__gte=now)
    qs = CalendarEvent.objects.filter(  # pylint: disable=no-member
        not_over_yet, user=user, start__lte=now + timedelta(days=days)
    ).order_by("start")
    return list(qs[:limit]), qs.count()


def tracked_total(user, start, end):
    """Total tracked time (closed entries) on live tasks within ``[start, end]``."""
    total = timedelta()
    rows = TimeEntry.objects.filter(  # pylint: disable=no-member
        subtask__task__user=user,
        clock_out__isnull=False,
        clock_in__gte=start,
        clock_in__lte=end,
        subtask__deleted_at__isnull=True,
        subtask__task__deleted_at__isnull=True,
    ).values("clock_in", "clock_out")
    for row in rows:
        total += row["clock_out"] - row["clock_in"]
    return total


def events_in_window(user, start, end):
    """
    Returns ``(event, occurrence_start)`` pairs whose occurrence falls within
    ``[start, end]`` (recurring events expanded), sorted by occurrence start.
    """
    candidates = CalendarEvent.objects.filter(  # pylint: disable=no-member
        user=user, start__lte=end
    ).filter(
        Q(recurrence="")
        | Q(recurrence_until__isnull=True)
        | Q(recurrence_until__gte=start)
    )

    pairs = []
    for event in candidates:
        if not event.recurrence:
            event_end = event.end or event.start
            if event.start <= end and event_end >= start:
                pairs.append((event, event.start))
        else:
            for occ in occurrences_between(
                event.start, event.recurrence, event.recurrence_until, start, end
            ):
                pairs.append((event, occ))
    pairs.sort(key=lambda pair: pair[1])
    return pairs


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
# Dashboard aggregation
# --------------------------------------------------------------------------- #
#
# Aggregation is done in Python over the closed time entries. Following
# ``TimeEntry.get_time_dedicated``, only entries with a ``clock_out`` count, and
# each entry is attributed to the bucket its ``clock_in`` falls in. These power
# both the dashboard API routes and the on-demand Telegram report.

_DASHBOARD_BUCKETS = ("day", "week", "month")


def _hours(delta: timedelta) -> float:
    """Converts a duration to decimal hours rounded to 4 decimals."""
    return round(delta.total_seconds() / 3600, 4)


def _filter_deleted(queryset, include_deleted: bool):
    """
    Unless ``include_deleted`` is set, drops time entries whose subtask or task
    has been soft-deleted.
    """
    if include_deleted:
        return queryset
    return queryset.filter(
        subtask__deleted_at__isnull=True, subtask__task__deleted_at__isnull=True
    )


def _bucket_start(day: date, bucket: str) -> date:
    """Returns the date the bucket containing ``day`` starts on."""
    if bucket == "week":
        return day - timedelta(days=day.weekday())
    if bucket == "month":
        return day.replace(day=1)
    return day


def _next_bucket(day: date, bucket: str) -> date:
    """Returns the start date of the bucket following the one at ``day``."""
    if bucket == "week":
        return day + timedelta(days=7)
    if bucket == "month":
        return (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return day + timedelta(days=1)


def _iter_buckets(start: date, end: date, bucket: str):
    """Yields every bucket start from ``start`` to ``end`` inclusive."""
    current = _bucket_start(start, bucket)
    last = _bucket_start(end, bucket)
    while current <= last:
        yield current
        current = _next_bucket(current, bucket)


def dashboard_summary(user, include_deleted: bool = False) -> dict:
    """
    Returns the headline hours for the stat cards: time tracked today, this
    week, this month and overall, plus the number of tasks worked on this week.
    Windows are relative to the current UTC instant and entries are attributed
    by their ``clock_in``.
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    today = week = month = total = timedelta()
    entries_qs = TimeEntry.objects.filter(  # pylint: disable=no-member
        subtask__task__user=user, clock_out__isnull=False
    )
    entries_qs = _filter_deleted(entries_qs, include_deleted)
    entries = entries_qs.values("clock_in", "clock_out")
    for entry in entries:
        duration = entry["clock_out"] - entry["clock_in"]
        total += duration
        clock_in = entry["clock_in"]
        if clock_in >= today_start:
            today += duration
        if clock_in >= week_start:
            week += duration
        if clock_in >= month_start:
            month += duration

    # "Active" means worked on this week, so an entry still open counts too.
    active_qs = TimeEntry.objects.filter(  # pylint: disable=no-member
        subtask__task__user=user, clock_in__gte=week_start
    )
    active_qs = _filter_deleted(active_qs, include_deleted)
    active_tasks = active_qs.values("subtask__task_id").distinct().count()

    return {
        "today_hours": _hours(today),
        "week_hours": _hours(week),
        "month_hours": _hours(month),
        "total_hours": _hours(total),
        "active_tasks": active_tasks,
    }


def weekly_task_hours(user, include_deleted: bool = False) -> dict:
    """
    Returns the hours tracked per task over the trailing 7 days, with each
    task's share (``percent``) of the total tracked that week. Only tasks with
    time in the window are returned (sorted by hours, most first); soft-deleted
    tasks/subtasks are excluded unless ``include_deleted`` is set.
    """
    now = timezone.now()
    start = now - timedelta(days=7)

    entries = _filter_deleted(
        TimeEntry.objects.select_related("subtask__task").filter(  # pylint: disable=no-member
            subtask__task__user=user,
            clock_out__isnull=False,
            clock_in__gte=start,
            clock_in__lte=now,
        ),
        include_deleted,
    )

    totals: dict[int, dict] = {}
    grand = timedelta()
    for entry in entries:
        duration = entry.clock_out - entry.clock_in
        grand += duration
        task = entry.subtask.task
        agg = totals.setdefault(
            task.id,
            {"name": task.name, "deleted": task.is_deleted, "total": timedelta()},
        )
        agg["total"] += duration

    grand_seconds = grand.total_seconds()
    tasks = [
        {
            "task_id": task_id,
            "task_name": agg["name"],
            "deleted": agg["deleted"],
            "hours": _hours(agg["total"]),
            "percent": (
                round(agg["total"].total_seconds() / grand_seconds * 100, 1)
                if grand_seconds
                else 0.0
            ),
        }
        for task_id, agg in sorted(
            totals.items(),
            key=lambda kv: (-kv[1]["total"].total_seconds(), kv[1]["name"].lower()),
        )
    ]

    return {
        "start": start,
        "end": now,
        "total_hours": _hours(grand),
        "tasks": tasks,
    }


def time_series(
    user,
    start: datetime,
    end: datetime,
    bucket: str = "day",
    include_deleted: bool = False,
) -> dict:
    """
    Returns the tracked hours within ``[start, end]`` grouped into contiguous
    ``bucket`` (``day``/``week``/``month``) buckets (zero-filled), together with
    the per-task and per-subtask totals for the same range. Soft-deleted
    tasks/subtasks are excluded unless ``include_deleted`` is set, in which case
    they are returned flagged with ``deleted: true``.

    Raises :class:`ServiceError` (422) on an unknown ``bucket`` or an ``end``
    that precedes ``start``.
    """
    if bucket not in _DASHBOARD_BUCKETS:
        raise ServiceError(
            422, f"bucket must be one of {', '.join(_DASHBOARD_BUCKETS)}."
        )
    if end < start:
        raise ServiceError(422, "end cannot be before start.")

    entries = (
        _filter_deleted(
            TimeEntry.objects.select_related("subtask__task").filter(  # pylint: disable=no-member
                subtask__task__user=user,
                clock_out__isnull=False,
                clock_in__gte=start,
                clock_in__lte=end,
            ),
            include_deleted,
        ).order_by("clock_in")
    )

    bucket_totals: dict[date, timedelta] = {}
    tasks: dict[int, dict] = {}
    for entry in entries:
        duration = entry.clock_out - entry.clock_in
        key = _bucket_start(entry.clock_in.date(), bucket)
        bucket_totals[key] = bucket_totals.get(key, timedelta()) + duration

        subtask = entry.subtask
        task = subtask.task
        task_agg = tasks.setdefault(
            task.id,
            {
                "name": task.name,
                "deleted": task.is_deleted,
                "total": timedelta(),
                "buckets": {},
                "subtasks": {},
            },
        )
        task_agg["total"] += duration
        task_agg["buckets"][key] = task_agg["buckets"].get(key, timedelta()) + duration
        sub_agg = task_agg["subtasks"].setdefault(
            subtask.id,
            {"name": subtask.name, "deleted": subtask.is_deleted, "total": timedelta()},
        )
        sub_agg["total"] += duration

    # Include every task the user owns, so a task with no tracked time in the
    # range still shows up (as a flat zero line) instead of disappearing.
    # Deleted tasks are only added in when explicitly requested.
    idle_tasks = Task.objects.filter(user=user)  # pylint: disable=no-member
    if not include_deleted:
        idle_tasks = idle_tasks.filter(deleted_at__isnull=True)
    for task in idle_tasks:
        tasks.setdefault(
            task.id,
            {
                "name": task.name,
                "deleted": task.is_deleted,
                "total": timedelta(),
                "buckets": {},
                "subtasks": {},
            },
        )

    bucket_keys = list(_iter_buckets(start.date(), end.date(), bucket))
    buckets = [
        {"period_start": day, "hours": _hours(bucket_totals.get(day, timedelta()))}
        for day in bucket_keys
    ]

    by_task = [
        {
            "task_id": task_id,
            "task_name": agg["name"],
            "deleted": agg["deleted"],
            "hours": _hours(agg["total"]),
            "series": [
                _hours(agg["buckets"].get(day, timedelta())) for day in bucket_keys
            ],
            "subtasks": [
                {
                    "subtask_id": sub_id,
                    "subtask_name": sub["name"],
                    "deleted": sub["deleted"],
                    "hours": _hours(sub["total"]),
                }
                for sub_id, sub in sorted(
                    agg["subtasks"].items(),
                    key=lambda kv: kv[1]["total"],
                    reverse=True,
                )
            ],
        }
        for task_id, agg in sorted(
            tasks.items(),
            key=lambda kv: (-kv[1]["total"].total_seconds(), kv[1]["name"].lower()),
        )
    ]

    return {
        "bucket": bucket,
        "start": start,
        "end": end,
        "buckets": buckets,
        "by_task": by_task,
    }


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
