"""
Here we will implement the helper functions for our tests.
"""

from django.contrib.auth.models import User

from ticktask.models import Task, SubTask, TimeEntry
from ticktask.server.schemas.tasks_schema import TaskSchema, SubTaskSchema


def insert_dummy_tasks(
    tasks_names: list[str] | None = None, username: str = "testuser"
):
    """
    Inserts a list of tasks into the database.
    """
    if not tasks_names:
        tasks_names = ["Example1", "Example2"]
    user = User.objects.get(username=username)

    for task_name in tasks_names:
        Task.objects.create(name=task_name, user=user)  # pylint: disable=no-member


def insert_dummy_subtasks(
    tasks_and_subtasks: list[TaskSchema] | None = None,
    username: str = "testuser",
):
    """
    Inserts a list of subtasks into the database.
    """
    if not tasks_and_subtasks:
        tasks_and_subtasks = [
            TaskSchema(
                name="Example1",
                subtasks=[
                    SubTaskSchema(
                        name="Subtask-1-1",
                        description="First subtask of the first task",
                        time_entries=[],
                    )
                ],
            ),
            TaskSchema(name="Example2", subtasks=[]),
        ]
    user = User.objects.get(username=username)  # pylint: disable=no-member

    insert_dummy_tasks(
        tasks_names=[t.name for t in tasks_and_subtasks], username=username
    )

    for task in tasks_and_subtasks:
        actual_task = Task.objects.get(name=task.name, user=user)  # pylint: disable=no-member
        for subtask in task.subtasks:
            actual_subtask = SubTask.objects.create(  # pylint: disable=no-member
                name=subtask.name,
                description=subtask.description,
                task=actual_task,
            )
            for time_entry in subtask.time_entries:
                TimeEntry.objects.create(  # pylint: disable=no-member
                    subtask=actual_subtask,
                    clock_in=time_entry.clock_in,
                    clock_out=time_entry.clock_out,
                )
