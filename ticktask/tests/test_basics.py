"""
Here we will test that the basics initialization of the tests work.
"""

import pytest


# @pytest.fixture(scope="function", autouse=True)
# def setup_static_data(
#     django_db_setup, django_db_blocker
# ):  # pylint: disable=unused-argument
#     """
#     Inserta los datos estáticos en la base de datos antes de cada test.
#     Se ejecuta automáticamente en todos los tests.
#     """
#     with django_db_blocker.unblock():
#         insert_static_data()


@pytest.mark.django_db
def test_dummy():
    """
    Dummy test to execute a simple function
    """
    a = 1 + 1
    assert a == 2
