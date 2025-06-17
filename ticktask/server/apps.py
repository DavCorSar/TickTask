"""
Definition of the application
"""

from django.apps import AppConfig


class TickTaskAppConfig(AppConfig):
    """
    Definition of the configuration for Tick-Task
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "ticktask"
