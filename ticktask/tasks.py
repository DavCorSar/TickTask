"""
Definition of the tasks to be run by celery.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from ticktask import telegram
from ticktask.models import TimeEntry, CalendarEvent, SentReminder

logger = logging.getLogger(__name__)

MAX_DURATION = timedelta(hours=12)
# Only fire reminders whose instant passed within this window, so a restarted
# beat doesn't blast notifications for events whose moment was long ago.
REMINDER_CATCHUP = timedelta(minutes=60)


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


@shared_task
def send_due_event_reminders():
    """
    Sends Telegram reminders for calendar events of users who have it enabled
    and connected: one ``X`` minutes before the event and one at its start.
    Each reminder is sent at most once (tracked by ``SentReminder``).
    """
    now = timezone.now()
    catchup = now - REMINDER_CATCHUP
    events = CalendarEvent.objects.filter(  # pylint: disable=no-member
        user__telegram_settings__enabled=True,
        user__telegram_settings__chat_id__isnull=False,
        start__gte=catchup,
        start__lte=now + timedelta(hours=24),
    ).select_related("user__telegram_settings")

    sent = 0
    for event in events:
        config = event.user.telegram_settings
        instants = [("start", event.start)]
        if config.reminder_lead_minutes:
            instants.append(
                ("lead", event.start - timedelta(minutes=config.reminder_lead_minutes))
            )
        for kind, instant in instants:
            if catchup <= instant <= now and _send_reminder_once(event, config, kind):
                sent += 1
    return sent


def _send_reminder_once(event, config, kind) -> bool:
    """Sends a reminder of ``kind`` for ``event`` exactly once."""
    _, created = SentReminder.objects.get_or_create(event=event, kind=kind)  # pylint: disable=no-member
    if not created:
        return False
    try:
        telegram.send_message(config.chat_id, _reminder_text(event, config, kind))
        return True
    except Exception:  # pylint: disable=broad-except
        # Roll back the marker so the next run retries.
        SentReminder.objects.filter(event=event, kind=kind).delete()  # pylint: disable=no-member
        logger.exception("Failed to send reminder for event %s", event.id)
        return False


def _reminder_text(event, config, kind) -> str:
    """Builds the reminder message text."""
    if kind == "lead":
        minutes = config.reminder_lead_minutes
        unit = "minute" if minutes == 1 else "minutes"
        return f'⏰ Reminder: "{event.title}" starts in {minutes} {unit}.'
    return f'🔔 "{event.title}" is starting now.'
