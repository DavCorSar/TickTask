"""
Definition of the endpoints that are used to obtain
tasks and subtasks information.
"""

import os

import django
from ninja import Router
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.tasks_schema import (
    TaskSchema,
    TaskCreationSchema,
    SubTaskSchema,
    SubTaskCreationSchema,
)
from ticktask.server.schemas.time_entry_schema import (
    ClockInSchema,
    ClockOutSchema,
    TimeEntrySchema,
)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
except RuntimeError:
    pass

from ticktask.models import Task, SubTask, TimeEntry
from django.utils import timezone

ticktask_router = Router()


@ticktask_router.get(
    "/user/get-tasks-and-subtasks/",
    response=list[TaskSchema],
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def get_user_tasks(request):
    """
    Returns the tasks and subtasks associated to each user.
    """
    if not request.auth:
        return {"error": "No autorizado"}, 401
    tasks = Task.objects.filter(user=request.auth).order_by("name")  # pylint: disable=no-member
    return tasks


@ticktask_router.post(
    "/user/create-task/",
    response=TaskSchema,
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def create_task(request, data: TaskCreationSchema):
    """
    Creates a new task for the authenticated user.
    """
    if not request.auth:
        return {"error": "No autorizado"}, 401

    task = Task.objects.create(  # pylint: disable=no-member
        user=request.auth,
        name=data.name.strip(),
    )
    return task


@ticktask_router.post(
    "/user/create-subtask/",
    response=SubTaskSchema,
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def create_subtask(request, data: SubTaskCreationSchema):
    """
    Creates a new subtask for the authenticated user.
    """
    if not request.auth:
        return {"error": "No autorizado"}, 401

    try:
        task = Task.objects.get(id=data.task_id, user=request.auth)  # pylint: disable=no-member
    except Task.DoesNotExist:  # pylint: disable=no-member
        return {"error": "Tarea no encontrada"}, 404

    subtask = SubTask.objects.create(  # pylint: disable=no-member
        name=data.name.strip(),
        description=data.description.strip(),
        task=task,
    )

    return subtask


@ticktask_router.post(
    "/user/clock-in/",
    response=TimeEntrySchema,
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def clock_in(request, data: ClockInSchema):
    """
    Registers a new time entry to the corresponding subtask.
    """
    if not request.auth:
        return {"error": "No autorizado"}, 401

    try:
        subtask = SubTask.objects.select_related("task").get(id=data.subtask_id)  # pylint: disable=no-member
    except SubTask.DoesNotExist:  # pylint: disable=no-member
        return {"error": "Subtarea no encontrada"}, 404

    if subtask.task.user != request.auth:
        return {"error": "No autorizado para esta subtarea"}, 403
    entry = TimeEntry.objects.create(subtask=subtask)  # pylint: disable=no-member

    return entry


@ticktask_router.post(
    "/user/clock-out/",
    response=TimeEntrySchema,
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def clock_out(request, data: ClockOutSchema):
    """
    Updates the given TimeEntry with clock_out.
    """
    print("Clocking out")
    if not request.auth:
        return {"error": "No autorizado"}, 401

    try:
        entry = TimeEntry.objects.select_related("subtask__task").get(  # pylint: disable=no-member
            id=data.entity_id, clock_out__isnull=True
        )
    except TimeEntry.DoesNotExist:  # pylint: disable=no-member
        return {"error": "Entrada no encontrada o ya cerrada"}, 404

    if entry.subtask.task.user != request.auth:
        return {"error": "No autorizado para esta entrada de tiempo"}, 403

    entry.clock_out = timezone.now()
    entry.save()
    return entry
