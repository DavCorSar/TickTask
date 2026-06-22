"""
Definition of the api object
"""

from ninja import NinjaAPI
from ticktask.server.routes.auth import auth_router

from ticktask.server.routes.tasks import ticktask_router
from ticktask.server.routes.calendar import calendar_router
from ticktask.server.routes.dashboard import dashboard_router
from ticktask.server.routes.telegram import telegram_router

api = NinjaAPI()

api.add_router("/auth/", auth_router)
api.add_router("/ticktask/", ticktask_router)
api.add_router("/calendar/", calendar_router)
api.add_router("/dashboard/", dashboard_router)
api.add_router("/telegram/", telegram_router)
