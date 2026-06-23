"""
This module contains the endpoints related with the authentication of the user.
"""

from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.routers.obtain import obtain_pair_router
from ninja_jwt.routers.verify import verify_router

from ticktask import telegram
from ticktask.models import UserLoginRecord, UserAccessRequest
from ticktask.server.schemas.auth import (
    LoginSchema,
    RegisterSchema,
    RegisterResultSchema,
    TokenSchema,
)

auth_router = Router()

auth_router.add_router("", tags=["Auth"], router=obtain_pair_router)
auth_router.add_router("", tags=["Auth"], router=verify_router)


def _issue_session(request, user) -> dict:
    """
    Records a login for ``user`` and returns a fresh access/refresh token pair.
    Shared by the login and register endpoints so a new account is signed in
    straight away.
    """
    refresh = RefreshToken.for_user(user)
    UserLoginRecord.objects.create(  # pylint: disable=no-member
        user=user,
        ip_address=request.META.get("REMOTE_ADDR", ""),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


@auth_router.post("/login", tags=["Auth"], response={200: TokenSchema, 401: dict})
def login(request, data: LoginSchema):
    """
    Authenticates a user. Active users get a token pair. A user whose account is
    still gated (correct password but not yet approved) gets a 403 explaining
    its status, so they learn the outcome without needing any notification.
    """
    user = authenticate(username=data.username, password=data.password)
    if user:
        return _issue_session(request, user)

    # Tell a correctly-authenticating but inactive user why they can't get in.
    pending = User.objects.filter(  # pylint: disable=no-member
        username=data.username, is_active=False
    ).first()
    if pending is not None and pending.check_password(data.password):
        access_request = UserAccessRequest.objects.filter(user=pending).first()  # pylint: disable=no-member
        if access_request is not None and (
            access_request.status == UserAccessRequest.REJECTED
        ):
            raise HttpError(403, "Tu solicitud de acceso fue rechazada.")
        raise HttpError(403, "Tu cuenta está pendiente de aprobación.")

    return 401, {"error": "Invalid credentials"}


@auth_router.post("/register", tags=["Auth"], response=RegisterResultSchema)
def register(request, data: RegisterSchema):
    """
    Registers a new account. The username must be unique and the password must
    satisfy ``AUTH_PASSWORD_VALIDATORS``. The account is created **inactive** and
    queued for admin approval (no token is issued); admins are notified over
    Telegram if any has it linked.
    """
    username = data.username.strip()
    if not username:
        raise HttpError(422, "El nombre de usuario no puede estar vacío.")
    if User.objects.filter(username=username).exists():  # pylint: disable=no-member
        raise HttpError(409, "Ese nombre de usuario ya está en uso.")

    try:
        validate_password(data.password)
    except DjangoValidationError as exc:
        raise HttpError(422, " ".join(exc.messages))

    user = User.objects.create_user(  # pylint: disable=no-member
        username=username, password=data.password, is_active=False
    )
    access_request = UserAccessRequest.objects.create(user=user)  # pylint: disable=no-member
    telegram.notify_admins_of_access_request(access_request)

    return {
        "status": "pending",
        "message": (
            "Tu solicitud se ha enviado. Podrás acceder cuando un administrador "
            "la apruebe."
        ),
    }
