"""
Definition of the tasks to be run by celery.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from ticktask import telegram, services, google_calendar
from ticktask.models import (
    TimeEntry,
    CalendarEvent,
    SentReminder,
    GoogleCalendarAccount,
    GoogleCalendarPendingDeletion,
)

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


@shared_task
def sync_google_calendar():
    """
    Syncs every connected user's calendar with Google, both ways:
    pushes local non-recurring event changes, applies pending deletions, and
    pulls remote changes back. Recurring events (either side) aren't synced —
    see ``ticktask/google_calendar.py`` for the API client and scope notes.
    """
    accounts = GoogleCalendarAccount.objects.exclude(refresh_token="")  # pylint: disable=no-member
    synced = 0
    for account in accounts:
        try:
            _sync_account(account)
            synced += 1
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "Google Calendar sync failed for user %s", account.user_id
            )
    return synced


def _sync_account(account: GoogleCalendarAccount) -> None:
    """Runs one full push+delete+pull sync pass for a single connected account."""
    _push_local_changes(account)
    _apply_pending_deletions(account)
    _pull_remote_changes(account)
    account.last_synced_at = timezone.now()
    account.save(update_fields=["last_synced_at"])


def _push_local_changes(account: GoogleCalendarAccount) -> None:
    """Pushes non-recurring events created/edited locally since the last sync."""
    changed = CalendarEvent.objects.filter(  # pylint: disable=no-member
        user_id=account.user_id, recurrence=CalendarEvent.NONE
    )
    if account.last_synced_at:
        changed = changed.filter(
            Q(google_event_id="") | Q(updated_at__gt=account.last_synced_at)
        )
    for event in changed:
        try:
            google_id = google_calendar.push_event(account, event)
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "Failed to push calendar event %s to Google Calendar", event.id
            )
            continue
        if event.google_event_id != google_id:
            CalendarEvent.objects.filter(id=event.id).update(  # pylint: disable=no-member
                google_event_id=google_id
            )


def _apply_pending_deletions(account: GoogleCalendarAccount) -> None:
    """Deletes on Google the events whose TickTask row is already gone."""
    for tombstone in GoogleCalendarPendingDeletion.objects.filter(  # pylint: disable=no-member
        account=account
    ):
        try:
            google_calendar.delete_event(account, tombstone.google_event_id)
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "Failed to delete Google Calendar event %s",
                tombstone.google_event_id,
            )
            continue
        tombstone.delete()


def _pull_remote_changes(account: GoogleCalendarAccount, retried: bool = False) -> None:
    """Applies remote changes locally and stores the new incremental sync token."""
    events, next_sync_token = google_calendar.list_changes(account)
    if next_sync_token is None and not retried:
        if account.sync_token:
            # Google's syncToken expired (HTTP 410) — drop it and do one full
            # resync from now instead of failing the whole pass.
            account.sync_token = ""
            return _pull_remote_changes(account, retried=True)
        return
    for g_event in events:
        _apply_google_event(account, g_event)
    account.sync_token = next_sync_token or ""


def _apply_google_event(account: GoogleCalendarAccount, g_event: dict) -> None:
    """Creates, updates or deletes the local counterpart of one Google event."""
    google_id = g_event["id"]

    if g_event.get("status") == "cancelled":
        CalendarEvent.objects.filter(  # pylint: disable=no-member
            user_id=account.user_id, google_event_id=google_id
        ).delete()
        return

    # Recurring series (and their expanded instances) aren't mapped yet —
    # skip rather than import something TickTask can't edit as a series.
    if g_event.get("recurrence") or g_event.get("recurringEventId"):
        return

    start = google_calendar.parse_google_datetime(g_event.get("start"))
    if start is None:
        return
    end = google_calendar.parse_google_datetime(g_event.get("end"))
    all_day = "date" in (g_event.get("start") or {})

    event = CalendarEvent.objects.filter(  # pylint: disable=no-member
        user_id=account.user_id, google_event_id=google_id
    ).first()
    if event is None:
        # Could be the echo of an event TickTask itself just pushed — attach
        # to it instead of creating a duplicate.
        ticktask_id = (
            g_event.get("extendedProperties", {})
            .get("private", {})
            .get("ticktask_event_id")
        )
        if ticktask_id:
            event = CalendarEvent.objects.filter(  # pylint: disable=no-member
                id=ticktask_id, user_id=account.user_id
            ).first()
    if event is None:
        event = CalendarEvent(user_id=account.user_id)

    event.google_event_id = google_id
    event.title = (g_event.get("summary") or "(untitled)")[:200]
    event.description = (g_event.get("description") or "")[:600]
    event.start = start
    event.end = end
    event.all_day = all_day
    event.save()


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
