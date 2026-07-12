"""
Endpoints that aggregate the user's tracked time for the dashboard: a
headline summary for the stat cards and a bucketed time series (plus a
per-task / per-subtask breakdown) for the charts.

The aggregation itself lives in :mod:`ticktask.services` so the same
implementation backs both these routes and the Telegram report; these
handlers only scope the call to ``request.auth`` and translate a domain
:class:`~ticktask.services.ServiceError` into a Ninja ``HttpError``.
"""

import os
from datetime import datetime

import django
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.dashboard_schema import (
    DashboardSummarySchema,
    TimeSeriesSchema,
    WeeklyTaskHoursSchema,
)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
except RuntimeError:
    pass

from ticktask import services

dashboard_router = Router()


@dashboard_router.get(
    "/user/get-summary/",
    response=DashboardSummarySchema,
    tags=["Dashboard"],
    auth=JWTAuth(),
)
def get_summary(request, include_deleted: bool = False):
    """
    Returns the headline hours for the stat cards: time tracked today, this
    week, this month and overall, plus the number of tasks worked on this week.
    """
    return services.dashboard_summary(request.auth, include_deleted)


@dashboard_router.get(
    "/user/get-weekly-task-hours/",
    response=WeeklyTaskHoursSchema,
    tags=["Dashboard"],
    auth=JWTAuth(),
)
def get_weekly_task_hours(request, include_deleted: bool = False):
    """
    Returns the hours tracked per task over the trailing 7 days, with each
    task's share (``percent``) of the total tracked that week.
    """
    return services.weekly_task_hours(request.auth, include_deleted)


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
    ``bucket`` (``day``/``week``/``month``) buckets (zero-filled), together with
    the per-task and per-subtask totals for the same range.
    """
    try:
        return services.time_series(
            request.auth, start, end, bucket, include_deleted
        )
    except services.ServiceError as exc:
        raise HttpError(exc.status, exc.message)
