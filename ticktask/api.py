from ninja import NinjaAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from utiv360.server.routes.auth import auth_router
from utiv360.server.routes.private import private_router
from utiv360.server.routes.public import public_router

api = NinjaAPI()

api.add_router("/auth/", auth_router)
api.add_router("/private/", private_router)
api.add_router("/public/", public_router)
