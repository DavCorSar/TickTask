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

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "utiv360.settings")
    django.setup()
except RuntimeError:
    pass

from ticktask.models import Task, SubTask

ticktask_router = Router()


@ticktask_router.get(
    "/user/get-tasks-and-subtasks/",
    response=list[TaskSchema],
    tags=["Ticktask"],
    auth=JWTAuth(),
)
def get_user_tasks(request):
    """
    Retorna los ScenarioDefinition favoritos asociados al usuario autenticado.
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
    Crea una nueva tarea para el usuario autenticado.
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
    Crea una nueva subtarea asociada a una tarea.
    """
    if not request.auth:
        return {"error": "No autorizado"}, 401

    try:
        task = Task.objects.get(id=data.task_id, user=request.auth)  # pylint: disable=no-member
    except:
        return {"error": "Tarea no encontrada"}, 404

    subtask = SubTask.objects.create(  # pylint: disable=no-member
        name=data.name.strip(),
        description=data.description.strip(),
        task=task,
    )

    return subtask
