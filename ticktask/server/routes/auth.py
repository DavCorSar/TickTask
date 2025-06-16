"""
This module contains the endpoints related with the authentication of the user.
"""

from ninja import Router
from django.contrib.auth import authenticate
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.routers.obtain import obtain_pair_router
from ninja_jwt.routers.verify import verify_router

from ticktask.models import UserLoginRecord
from ticktask.server.schemas.auth import LoginSchema, TokenSchema

auth_router = Router()

auth_router.add_router("", tags=["Auth"], router=obtain_pair_router)
auth_router.add_router("", tags=["Auth"], router=verify_router)


@auth_router.post("/login", tags=["Auth"], response={200: TokenSchema, 401: dict})
def login(request, data: LoginSchema):
    """
    This endpoint checks and performs the login access into the app
    """
    print(f"User: {data.username} and password: {data.password}")
    user = authenticate(username=data.username, password=data.password)
    if user:
        refresh = RefreshToken.for_user(user)

        # Save login log
        user_ip = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        print(
            f"User {user.username} logged in from IP: {user_ip}, User-Agent: {user_agent}"
        )

        UserLoginRecord.objects.create(  # pylint: disable=no-member
            user=user, ip_address=user_ip, user_agent=user_agent
        )

        return {"access": str(refresh.access_token), "refresh": str(refresh)}
    return 401, {"error": "Invalid credentials"}
