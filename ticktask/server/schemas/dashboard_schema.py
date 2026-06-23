"""
Schemas for the dashboard aggregation endpoints (hours summary and the
time series used to draw the charts).
"""

from datetime import date, datetime

from ninja import Schema


class DashboardSummarySchema(Schema):
    """
    Headline figures for the dashboard stat cards. Hours are decimal hours
    (e.g. 1.5 == one hour and a half) and the windows are relative to the
    current UTC instant.
    """

    today_hours: float
    week_hours: float
    month_hours: float
    total_hours: float
    active_tasks: int


class TimeSeriesBucketSchema(Schema):
    """
    Total tracked hours within a single time bucket, keyed by the date the
    bucket starts on (the day, the Monday of the week, or the 1st of the
    month depending on the requested granularity).
    """

    period_start: date
    hours: float


class SubTaskHoursSchema(Schema):
    """Tracked hours for a single subtask over the requested range."""

    subtask_id: int
    subtask_name: str
    hours: float
    deleted: bool = False


class TaskHoursSchema(Schema):
    """
    Tracked hours for a task over the range: the total, the per-bucket series
    (aligned, in order, with the top-level ``buckets``) used to draw the task's
    line, and the per-subtask breakdown.
    """

    task_id: int
    task_name: str
    hours: float
    deleted: bool = False
    series: list[float]
    subtasks: list[SubTaskHoursSchema]


class TimeSeriesSchema(Schema):
    """
    The time series for a ``[start, end]`` range at a given bucket size,
    together with the per-task / per-subtask breakdown for the same range.
    """

    bucket: str
    start: datetime
    end: datetime
    buckets: list[TimeSeriesBucketSchema]
    by_task: list[TaskHoursSchema]


class WeeklyTaskShareSchema(Schema):
    """
    One task's tracked hours over the last week and its share (``percent``) of
    the total time tracked that week.
    """

    task_id: int
    task_name: str
    hours: float
    percent: float
    deleted: bool = False


class WeeklyTaskHoursSchema(Schema):
    """
    Per-task tracked hours over the trailing 7 days, each as a share of the
    week's total. Only tasks with time tracked in the window are included, so
    the shares add up to ~100% of what was actually tracked.
    """

    start: datetime
    end: datetime
    total_hours: float
    tasks: list[WeeklyTaskShareSchema]
