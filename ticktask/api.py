"""
Definition of the api object
"""

from ninja import NinjaAPI
from ticktask.server.routes.auth import auth_router

api = NinjaAPI()

api.add_router("/auth/", auth_router)
