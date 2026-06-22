"""
Smoke tests for the Django admin registration.
"""

import pytest
from django.contrib import admin

from ticktask.models import (
    UserLoginRecord,
    Task,
    SubTask,
    TimeEntry,
    CalendarEvent,
)


@pytest.mark.parametrize(
    "model",
    [Task, SubTask, TimeEntry, CalendarEvent, UserLoginRecord],
)
def test_model_is_registered_in_admin(model):
    """Each managed model is editable from the Django admin."""
    assert model in admin.site._registry


def test_admin_configuration_has_no_errors():
    """The registered ModelAdmins pass Django's admin system checks."""
    errors = admin.site.check(None)
    assert not errors, errors
