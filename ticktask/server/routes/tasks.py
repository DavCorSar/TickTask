"""
Definition of the endpoints that are used to obtain
tasks and subtasks information.
"""

import os
from datetime import datetime, timedelta

import django
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.tasks_schema import (
    TaskSchema,
    TaskCreationSchema,
    SubTaskSchema,
    SubTaskCreationSchema,
    TaskIdSchema,
    SubTaskIdSchema,
)
from ticktask.server.schemas.time_entry_schema import (
    ClockInSchema,
    ClockOutSchema,
    TimeEntrySchema,
    TimeEntryHistoryRequestSchema,
    HistoryEntrySchema,
)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
except RuntimeError:
    pass

from ticktask.models import Task, SubTask, TimeEntry
from django.db.models import Prefetch
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
    active_subtasks = SubTask.objects.filter(deleted_at__isnull=True)  # pylint: disable=no-member
    tasks = (
        Task.objects.filter(user=request.auth, deleted_at__isnull=True)  # pylint: disable=no-member
        .prefetch_related(Prefetch("subtasks", queryset=active_subtasks))
        .order_by("name")
    )
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
    name = data.name.strip()
    if not name:
        raise HttpError(422, "El nombre de la tarea no puede estar vacío.")

    existing = Task.objects.filter(  # pylint: disable=no-member
        user=request.auth, name=name
    ).first()
    if existing is not None:
        if existing.is_deleted:
            raise HttpError(
                409,
                "Ya existe una tarea eliminada con ese nombre. "
                "Restáurala en lugar de crear una nueva.",
            )
        raise HttpError(409, "Ya existe una tarea con ese nombre.")

    task = Task.objects.create(  # pylint: disable=no-member
        user=request.auth,
        name=name,
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
    try:
        task = Task.objects.get(id=data.task_id, user=request.auth)  # pylint: disable=no-member
    except Task.DoesNotExist:  # pylint: disable=no-member
        return {"error": "Tarea no encontrada"}, 404

    name = data.name.strip()
    if not name:
        raise HttpError(422, "El nombre de la subtarea no puede estar vacío.")

    existing = SubTask.objects.filter(task=task, name=name).first()  # pylint: disable=no-member
    if existing is not None:
        if existing.is_deleted:
            raise HttpError(
                409,
                "Ya existe una subtarea eliminada con ese nombre en esta tarea. "
                "Restáurala en lugar de crear una nueva.",
            )
        raise HttpError(409, "Ya existe una subtarea con ese nombre en esta tarea.")

    subtask = SubTask.objects.create(  # pylint: disable=no-member
        name=name,
        description=data.description.strip(),
        task=task,
    )

    return subtask


@ticktask_router.post(
    "/user/delete-task/",
    response={200: dict},
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def delete_task(request, data: TaskIdSchema):
    """
    Soft-deletes one of the user's tasks: it disappears from time tracking but
    its tracked time is kept (and still visible on the dashboard/calendar).
    Any open time entry under it is closed.
    """
    try:
        task = Task.objects.get(id=data.task_id, user=request.auth)  # pylint: disable=no-member
    except Task.DoesNotExist:  # pylint: disable=no-member
        raise HttpError(404, "Tarea no encontrada.")

    if not task.is_deleted:
        now = timezone.now()
        TimeEntry.objects.filter(  # pylint: disable=no-member
            subtask__task=task, clock_out__isnull=True
        ).update(clock_out=now)
        task.deleted_at = now
        task.save(update_fields=["deleted_at"])

    return {"success": True}


@ticktask_router.post(
    "/user/restore-task/",
    response=TaskSchema,
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def restore_task(request, data: TaskIdSchema):
    """
    Restores a previously soft-deleted task so it shows up again in time
    tracking. The unique name guarantees there is never a conflicting active
    task, so this cannot create a duplicate.
    """
    try:
        task = Task.objects.get(id=data.task_id, user=request.auth)  # pylint: disable=no-member
    except Task.DoesNotExist:  # pylint: disable=no-member
        raise HttpError(404, "Tarea no encontrada.")

    if task.is_deleted:
        task.deleted_at = None
        task.save(update_fields=["deleted_at"])

    return task


@ticktask_router.post(
    "/user/delete-subtask/",
    response={200: dict},
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def delete_subtask(request, data: SubTaskIdSchema):
    """
    Soft-deletes one of the user's subtasks (closing any open time entry on it).
    """
    try:
        subtask = SubTask.objects.select_related("task").get(  # pylint: disable=no-member
            id=data.subtask_id, task__user=request.auth
        )
    except SubTask.DoesNotExist:  # pylint: disable=no-member
        raise HttpError(404, "Subtarea no encontrada.")

    if not subtask.is_deleted:
        now = timezone.now()
        TimeEntry.objects.filter(  # pylint: disable=no-member
            subtask=subtask, clock_out__isnull=True
        ).update(clock_out=now)
        subtask.deleted_at = now
        subtask.save(update_fields=["deleted_at"])

    return {"success": True}


@ticktask_router.post(
    "/user/restore-subtask/",
    response=SubTaskSchema,
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def restore_subtask(request, data: SubTaskIdSchema):
    """
    Restores a previously soft-deleted subtask.
    """
    try:
        subtask = SubTask.objects.select_related("task").get(  # pylint: disable=no-member
            id=data.subtask_id, task__user=request.auth
        )
    except SubTask.DoesNotExist:  # pylint: disable=no-member
        raise HttpError(404, "Subtarea no encontrada.")

    if subtask.is_deleted:
        subtask.deleted_at = None
        subtask.save(update_fields=["deleted_at"])

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
    try:
        subtask = SubTask.objects.select_related("task").get(id=data.subtask_id)  # pylint: disable=no-member
    except SubTask.DoesNotExist:  # pylint: disable=no-member
        return {"error": "Subtarea no encontrada"}, 404

    if subtask.task.user != request.auth:
        return {"error": "No autorizado para esta subtarea"}, 403
    if subtask.is_deleted or subtask.task.is_deleted:
        raise HttpError(409, "No se puede fichar en una subtarea eliminada.")
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


@ticktask_router.get(
    "/user/get-clocked-in-time-entry/",
    response=TaskSchema | None,
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def get_user_clocked_in_activity(request):
    """
    Returns the `Task` where the user is clocked in if exists.
    """
    time_entry = (
        TimeEntry.objects.select_related("subtask__task")  # pylint: disable=no-member
        .filter(
            clock_out__isnull=True,
            subtask__task__user=request.auth,
            subtask__deleted_at__isnull=True,
            subtask__task__deleted_at__isnull=True,
        )
        .first()
    )

    if not time_entry:
        return None

    subtask = time_entry.subtask
    task = subtask.task

    return {
        "id": task.id,
        "name": task.name,
        "subtasks": [
            {
                "id": subtask.id,
                "name": subtask.name,
                "description": subtask.description,
                "time_entries": [
                    {
                        "id": time_entry.id,
                        "clock_in": time_entry.clock_in,
                        "clock_out": time_entry.clock_out,
                    }
                ],
            }
        ],
    }


@ticktask_router.post(
    "/user/get-time-entries/",
    response=list[TimeEntrySchema],
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def get_history_time_entries(request, data: TimeEntryHistoryRequestSchema):
    """
    Returns the `TimeEntry`s associated with a specific subtask.
    """
    cutoff = timezone.now() - timedelta(hours=data.last_hours)
    time_entries = TimeEntry.objects.filter(  # pylint: disable=no-member
        subtask_id=data.subtask_id, clock_in__gte=cutoff
    ).order_by("-clock_in")
    return time_entries


@ticktask_router.get(
    "/user/get-time-history/",
    response=list[HistoryEntrySchema],
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def get_time_history(
    request, start: datetime, end: datetime, include_deleted: bool = False
):
    """
    Returns the user's time entries whose ``clock_in`` falls within
    ``[start, end]``, flattened with their subtask and task names and ordered
    newest first. Entries of soft-deleted subtasks/tasks are excluded unless
    ``include_deleted`` is set, in which case they are flagged with
    ``deleted: true``.
    """
    entries = (
        TimeEntry.objects.select_related("subtask__task")  # pylint: disable=no-member
        .filter(
            subtask__task__user=request.auth,
            clock_in__gte=start,
            clock_in__lte=end,
        )
        .order_by("-clock_in")
    )
    if not include_deleted:
        entries = entries.filter(
            subtask__deleted_at__isnull=True, subtask__task__deleted_at__isnull=True
        )

    return [
        {
            "id": entry.id,
            "clock_in": entry.clock_in,
            "clock_out": entry.clock_out,
            "subtask_id": entry.subtask_id,
            "subtask_name": entry.subtask.name,
            "task_id": entry.subtask.task_id,
            "task_name": entry.subtask.task.name,
            "deleted": entry.subtask.is_deleted or entry.subtask.task.is_deleted,
        }
        for entry in entries
    ]
