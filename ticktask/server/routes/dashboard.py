"""
Endpoints that aggregate the user's tracked time for the dashboard: a
headline summary for the stat cards and a bucketed time series (plus a
per-task / per-subtask breakdown) for the charts.

Aggregation is done in Python over the closed time entries. Following
``TimeEntry.get_time_dedicated``, only entries with a ``clock_out`` count,
and each entry is attributed to the bucket its ``clock_in`` falls in.
"""

import os
from datetime import date, datetime, timedelta

import django
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.dashboard_schema import (
    DashboardSummarySchema,
    TimeSeriesSchema,
)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
except RuntimeError:
    pass

from django.utils import timezone
from ticktask.models import Task, TimeEntry

dashboard_router = Router()

_BUCKETS = ("day", "week", "month")


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


@dashboard_router.get(
    "/user/get-summary/",
    response=DashboardSummarySchema,
    tags=["Dashboard"],
    auth=JWTAuth(),
)
def get_summary(request, include_deleted: bool = False):
    """
    Returns the headline hours for the stat cards: time tracked today, this
    week, this month and overall, plus the number of tasks worked on this
    week. Windows are relative to the current UTC instant and entries are
    attributed by their ``clock_in``.
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    today = week = month = total = timedelta()
    entries_qs = TimeEntry.objects.filter(  # pylint: disable=no-member
        subtask__task__user=request.auth, clock_out__isnull=False
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
        subtask__task__user=request.auth, clock_in__gte=week_start
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


@dashboard_router.get(
    "/user/get-time-series/",
    response=TimeSeriesSchema,
    tags=["Dashboard"],
    auth=JWTAuth(),
)
def get_time_series(
    request,
    start: datetime,
    end: datetime,
    bucket: str = "day",
    include_deleted: bool = False,
):
    """
    Returns the tracked hours within ``[start, end]`` grouped into contiguous
    ``bucket`` (``day``/``week``/``month``) buckets (zero-filled), together
    with the per-task and per-subtask totals for the same range. Soft-deleted
    tasks/subtasks are excluded unless ``include_deleted`` is set, in which case
    they are returned flagged with ``deleted: true``.
    """
    if bucket not in _BUCKETS:
        raise HttpError(422, f"bucket must be one of {', '.join(_BUCKETS)}.")
    if end < start:
        raise HttpError(422, "end cannot be before start.")

    entries = (
        _filter_deleted(
            TimeEntry.objects.select_related("subtask__task").filter(  # pylint: disable=no-member
                subtask__task__user=request.auth,
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
    idle_tasks = Task.objects.filter(user=request.auth)  # pylint: disable=no-member
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
