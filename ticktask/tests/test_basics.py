"""
Here we will test that the basics initialization of the tests work.
"""

from datetime import timedelta
import pytest
from django.contrib.auth.models import User

from ticktask.tests import test_utils
from ticktask.models import Task, SubTask, TimeEntry


@pytest.fixture(scope="function", autouse=True)
def setup_static_data(django_db_setup, django_db_blocker):  # pylint: disable=unused-argument
    """
    Inserta los datos estáticos en la base de datos antes de cada test.
    Se ejecuta automáticamente en todos los tests.
    """
    with django_db_blocker.unblock():
        User.objects.create_user(username="testuser", password="testpass")


@pytest.mark.django_db
def test_complete_insertion():
    """
    Dummy test to ensure insertion in the database is well done.
    """
    test_utils.insert_dummy_subtasks()

    assert Task.objects.count() == 2  # pylint: disable=no-member
    assert SubTask.objects.count() == 1  # pylint: disable=no-member
    assert TimeEntry.objects.count() == 0  # pylint: disable=no-member


def test_time_dedicated_when_there_are_no_time_entries_is_zero():
    """
    This test checks that when there are no objects
    in the `TimeEntry` table, the time dedicated is zero.
    """
    test_utils.insert_dummy_subtasks()

    for subtask in SubTask.objects.all():  # pylint: disable=no-member
        assert subtask.get_time_dedicated() == timedelta()

    for task in Task.objects.all():  # pylint: disable=no-member
        assert task.get_time_dedicated() == timedelta()
