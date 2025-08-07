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
