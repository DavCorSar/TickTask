"""
Definition of the initialisation of the app.
"""

from ticktask.celery_app import app as celery_app

__all__ = ("celery_app",)
