"""
Definition of the tasks to be run by celery.
"""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from ticktask.models import TimeEntry

MAX_DURATION = timedelta(hours=12)


@shared_task
def autoclose_old_entries():
    """
    Function to close time entries that exceeds the limit.
    """
    threshold = timezone.now() - MAX_DURATION
    updated = TimeEntry.objects.filter(  # pylint: disable=no-member
        clock_out__isnull=True, clock_in__lte=threshold
    ).update(clock_out=timezone.now())
    return updated
