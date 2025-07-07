"""
Definition of the endpoints that are used to obtain
tasks and subtasks information.
"""

import os

import django
from ninja import Router
from ninja_jwt.authentication import JWTAuth

from ticktask.server.schemas.tasks_schema import TaskSchema

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "utiv360.settings")
    django.setup()
except RuntimeError:
    pass

from ticktask.models import Task

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
