"""
Tests for the gated authentication flow: self-service registration creates an
inactive account queued for approval (no auto-login), login distinguishes a
pending/rejected account from bad credentials, and approving a request via the
shared service activates the account so the user can log in.
"""

import json

import pytest
from django.test import Client
from django.contrib.auth.models import User

from ticktask import services
from ticktask.models import UserAccessRequest, UserLoginRecord

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"

# Passes the default Django validators (length, not all-numeric, not common).
GOOD_PASSWORD = "tr0ut-Ladder-92"


def post(path, payload):
    return Client().post(
        path, data=json.dumps(payload), content_type="application/json"
    )


@pytest.fixture(autouse=True)
def no_telegram(monkeypatch):
    """Registration notifies admins over Telegram; stub it out in tests."""
    monkeypatch.setattr(
        "ticktask.telegram.notify_admins_of_access_request", lambda req: None
    )


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_register_queues_inactive_account_without_tokens():
    """Registering creates an inactive, pending account and issues no token."""
    resp = post(REGISTER, {"username": "newbie", "password": GOOD_PASSWORD})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert "access" not in body and "refresh" not in body

    user = User.objects.get(username="newbie")  # pylint: disable=no-member
    assert user.is_active is False
    assert user.access_request.status == UserAccessRequest.PENDING
    # No login is recorded until the account is actually used.
    assert not UserLoginRecord.objects.filter(user=user).exists()  # pylint: disable=no-member


@pytest.mark.django_db
def test_register_trims_username():
    """Surrounding whitespace in the username is stripped."""
    post(REGISTER, {"username": "  spaced  ", "password": GOOD_PASSWORD})
    assert User.objects.filter(username="spaced").exists()  # pylint: disable=no-member


@pytest.mark.django_db
def test_register_rejects_duplicate_username():
    """An already-taken username is refused with 409."""
    User.objects.create_user(username="taken", password=GOOD_PASSWORD)

    resp = post(REGISTER, {"username": "taken", "password": GOOD_PASSWORD})
    assert resp.status_code == 409
    assert User.objects.filter(username="taken").count() == 1  # pylint: disable=no-member


@pytest.mark.django_db
def test_register_rejects_empty_username():
    """A blank username is refused with 422."""
    resp = post(REGISTER, {"username": "   ", "password": GOOD_PASSWORD})
    assert resp.status_code == 422
    assert User.objects.count() == 0  # pylint: disable=no-member


@pytest.mark.django_db
def test_register_rejects_weak_password():
    """A password failing the validators is refused with 422 and no user."""
    resp = post(REGISTER, {"username": "weakling", "password": "123"})
    assert resp.status_code == 422
    assert not User.objects.filter(username="weakling").exists()  # pylint: disable=no-member


# --------------------------------------------------------------------------- #
# Login gating
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_login_pending_account_is_told_to_wait():
    """A correct password on a pending account returns 403 (not a token)."""
    post(REGISTER, {"username": "carol", "password": GOOD_PASSWORD})

    resp = post(LOGIN, {"username": "carol", "password": GOOD_PASSWORD})
    assert resp.status_code == 403
    assert "pendiente" in resp.json()["detail"].lower()


@pytest.mark.django_db
def test_login_rejected_account_is_told_so():
    """A rejected account is informed of the rejection on login."""
    post(REGISTER, {"username": "dan", "password": GOOD_PASSWORD})
    services.reject_access(User.objects.get(username="dan").access_request)  # pylint: disable=no-member

    resp = post(LOGIN, {"username": "dan", "password": GOOD_PASSWORD})
    assert resp.status_code == 403
    assert "rechaz" in resp.json()["detail"].lower()


@pytest.mark.django_db
def test_login_wrong_password_stays_generic_401():
    """A wrong password never reveals the account's gating status."""
    post(REGISTER, {"username": "erin", "password": GOOD_PASSWORD})

    resp = post(LOGIN, {"username": "erin", "password": "wrong-password-1"})
    assert resp.status_code == 401


@pytest.mark.django_db
def test_approved_user_can_log_in():
    """After approval the account is active and login returns tokens."""
    post(REGISTER, {"username": "frank", "password": GOOD_PASSWORD})
    services.approve_access(User.objects.get(username="frank").access_request)  # pylint: disable=no-member

    resp = post(LOGIN, {"username": "frank", "password": GOOD_PASSWORD})
    assert resp.status_code == 200
    assert resp.json()["access"]


# --------------------------------------------------------------------------- #
# Approval services
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_approve_activates_account():
    """Approving flips the request to approved and activates the user."""
    post(REGISTER, {"username": "gina", "password": GOOD_PASSWORD})
    req = User.objects.get(username="gina").access_request  # pylint: disable=no-member

    services.approve_access(req)

    req.refresh_from_db()
    assert req.status == UserAccessRequest.APPROVED
    assert req.decided_at is not None
    assert User.objects.get(username="gina").is_active is True  # pylint: disable=no-member


@pytest.mark.django_db
def test_reject_keeps_account_inactive():
    """Rejecting flips the request to rejected and keeps the user inactive."""
    post(REGISTER, {"username": "huey", "password": GOOD_PASSWORD})
    req = User.objects.get(username="huey").access_request  # pylint: disable=no-member

    services.reject_access(req)

    req.refresh_from_db()
    assert req.status == UserAccessRequest.REJECTED
    assert User.objects.get(username="huey").is_active is False  # pylint: disable=no-member
