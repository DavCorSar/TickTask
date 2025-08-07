"""
Definiton of the schemas used in the tasks and subtasks definition
"""

from ninja import Schema

from ticktask.server.schemas.time_entry_schema import (
    TimeEntrySchema,
)


class SubTaskSchema(Schema):
    """
    Definition of the schema of each individual subtask.
    """

    id: int
    name: str
    description: str
    time_entries: list[TimeEntrySchema]


class SubTaskCreationSchema(Schema):
    """
    Basic info of the subtask to create a new instance in the database
    """

    task_id: int
    name: str
    description: str


class TaskSchema(Schema):
    """
    Definition of the schema of each individual task.
    """

    id: int
    name: str
    subtasks: list[SubTaskSchema]


class TaskCreationSchema(Schema):
    """
    Basic info of the task to create a new instance in the database
    """

    name: str
