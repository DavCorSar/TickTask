"""
This module contains the configuration to run the tests.
"""

import os
import django


def pytest_configure():
    """
    Configuration of the pytest settings
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticktask.settings")
    django.setup()
