"""
Definition of the tasks to be run by celery.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from ticktask import telegram, services
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
    and connected: one ``X`` minutes before each occurrence and one at its
    start. Recurring events are reminded per occurrence; each (occurrence, kind)
    reminder is sent at most once (tracked by ``SentReminder``).
    """
    now = timezone.now()
    catchup = now - REMINDER_CATCHUP
    horizon = now + timedelta(hours=24)
    events = (
        CalendarEvent.objects.filter(  # pylint: disable=no-member
            user__telegram_settings__enabled=True,
            user__telegram_settings__chat_id__isnull=False,
            start__lte=horizon,
        )
        .filter(
            Q(recurrence="", start__gte=catchup)
            | (
                ~Q(recurrence="")
                & (
                    Q(recurrence_until__isnull=True)
                    | Q(recurrence_until__gte=catchup)
                )
            )
        )
        .select_related("user__telegram_settings")
    )

    sent = 0
    for event in events:
        config = event.user.telegram_settings
        lead = config.reminder_lead_minutes or 0
        # An occurrence can be due now via its start (occ in [catchup, now]) or
        # its lead instant (occ - lead in [catchup, now] → occ up to now + lead).
        for occurrence in services.occurrences_between(
            event.start,
            event.recurrence,
            event.recurrence_until,
            catchup,
            now + timedelta(minutes=lead),
        ):
            instants = [("start", occurrence)]
            if lead:
                instants.append(("lead", occurrence - timedelta(minutes=lead)))
            for kind, instant in instants:
                if catchup <= instant <= now and _send_reminder_once(
                    event, config, kind, occurrence
                ):
                    sent += 1
    return sent


def _send_reminder_once(event, config, kind, occurrence) -> bool:
    """Sends a reminder of ``kind`` for one ``occurrence`` exactly once."""
    _, created = SentReminder.objects.get_or_create(  # pylint: disable=no-member
        event=event, kind=kind, occurrence=occurrence
    )
    if not created:
        return False
    try:
        telegram.send_message(config.chat_id, _reminder_text(event, config, kind))
        return True
    except Exception:  # pylint: disable=broad-except
        # Roll back the marker so the next run retries.
        SentReminder.objects.filter(  # pylint: disable=no-member
            event=event, kind=kind, occurrence=occurrence
        ).delete()
        logger.exception("Failed to send reminder for event %s", event.id)
        return False


def _reminder_text(event, config, kind) -> str:
    """Builds the reminder message text."""
    if kind == "lead":
        minutes = config.reminder_lead_minutes
        unit = "minute" if minutes == 1 else "minutes"
        return f'⏰ Reminder: "{event.title}" starts in {minutes} {unit}.'
    return f'🔔 "{event.title}" is starting now.'


TOP_TASKS_SHOWN = 5


@shared_task
def send_weekly_summaries():
    """
    Sends a Telegram summary of the trailing 7 days' tracked time to every user
    who has notifications enabled and a linked chat, skipping anyone with
    nothing tracked in the window. Purely an aggregation over already-tracked
    entries (via ``services.weekly_task_hours``) — no LLM involved.
    """
    users = User.objects.filter(  # pylint: disable=no-member
        telegram_settings__enabled=True,
        telegram_settings__chat_id__isnull=False,
    ).select_related("telegram_settings")

    sent = 0
    for user in users:
        summary = services.weekly_task_hours(user)
        if not summary["tasks"]:
            continue
        try:
            telegram.send_message(
                user.telegram_settings.chat_id, _weekly_summary_text(user, summary)
            )
            sent += 1
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to send weekly summary for user %s", user.id)
    return sent


def _weekly_summary_text(user, summary: dict) -> str:
    """Builds the weekly summary message text."""
    zone = telegram.user_zone(user)
    start = summary["start"].astimezone(zone).strftime("%b %d")
    end = summary["end"].astimezone(zone).strftime("%b %d")

    lines = [
        f"📈 Weekly summary — {start} to {end}",
        f"⏱ Total tracked: {_format_hours(summary['total_hours'])}",
        "",
        "Top tasks:",
    ]
    top = summary["tasks"][:TOP_TASKS_SHOWN]
    for i, task in enumerate(top, 1):
        lines.append(
            f"{i}. {task['task_name']} — {_format_hours(task['hours'])} "
            f"({task['percent']:.0f}%)"
        )
    remaining = len(summary["tasks"]) - len(top)
    if remaining > 0:
        lines.append(f"…and {remaining} more.")
    return "\n".join(lines)


def _format_hours(hours: float) -> str:
    """Formats decimal hours as a compact ``Xh Ym`` label."""
    minutes = round((hours or 0) * 60)
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    return f"{h}h" if h else f"{m}m"
