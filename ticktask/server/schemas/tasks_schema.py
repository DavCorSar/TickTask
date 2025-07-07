"""
Definiton of the schemas used in the tasks and subtasks definition
"""

from datetime import datetime

from ninja import Schema


class TimeEntrySchema(Schema):
    """
    Definition of the schema of each one of the
    time entries of each subtask.
    """

    clock_in: datetime
    clock_out: datetime


class SubTaskSchema(Schema):
    """
    Definition of the schema of each individual subtask.
    """

    name: str
    description: str
    time_entries: list[TimeEntrySchema]


class TaskSchema(Schema):
    """
    Definition of the schema of each individual task.
    """

    id: int
    name: str
    subtasks: list[SubTaskSchema]
