"""
Definition of the database tables that will be used in our application.
"""

from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserLoginRecord(models.Model):
    """
    Stores the login records of users.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="login_records"
    )
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, null=True, blank=True)

    class Meta:
        ordering = ["-login_time"]
        verbose_name_plural = "User Login Records"


class Task(models.Model):
    """
    Definition of the general tasks per user
    """

    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    # Soft delete: ``None`` means active. A deleted task keeps its row (and so
    # keeps reserving its name) and stays visible on the dashboard/calendar.
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        """
        Include the unique constraint of task name per user. Deleted rows keep
        their name, so it stays reserved until the task is restored.
        """

        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_task_per_user"
            )
        ]

    @property
    def is_deleted(self) -> bool:
        """Whether the task has been soft-deleted."""
        return self.deleted_at is not None

    def get_time_dedicated(self) -> timedelta:
        """
        This function will return the amount of time
        dedicated to this individual task.
        """
        total_time = timedelta()
        for time_entry in self.subtasks.all():  # pylint: disable=no-member
            total_time += time_entry.get_time_dedicated()
        return total_time


class SubTask(models.Model):
    """
    Definition of each one of the subtasks
    that are associated with a specific task.
    """

    name = models.CharField(max_length=200)
    description = models.CharField(max_length=600)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="subtasks")
    # Soft delete: ``None`` means active. See ``Task.deleted_at``.
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        """
        Include the unique constraint of subtask name per task. Deleted rows
        keep their name, so it stays reserved until the subtask is restored.
        """

        constraints = [
            models.UniqueConstraint(
                fields=["task", "name"], name="unique_subtask_per_task"
            )
        ]

    @property
    def is_deleted(self) -> bool:
        """Whether the subtask has been soft-deleted."""
        return self.deleted_at is not None

    def get_time_dedicated(self) -> timedelta:
        """
        This function will return the amount of time
        dedicated to this individual subtask.
        """
        total_time = timedelta()
        for time_entry in self.time_entries.all():  # pylint: disable=no-member
            total_time += time_entry.get_time_dedicated()
        return total_time


class TimeEntry(models.Model):
    """
    Definition of each one of the clocked events
    that are associated with a specific subtask.
    """

    subtask = models.ForeignKey(
        SubTask, on_delete=models.CASCADE, related_name="time_entries"
    )
    # Defaults to "now" for live clock-in, but is editable so entries can be
    # created or corrected manually with explicit times.
    clock_in = models.DateTimeField(default=timezone.now)
    clock_out = models.DateTimeField(null=True, blank=True)

    def get_time_dedicated(self) -> timedelta:
        """
        This function will return the amount of time
        dedicated to this individual time entry.
        """
        if self.clock_out:
            return self.clock_out - self.clock_in
        return timedelta()


class CalendarEvent(models.Model):
    """
    A user-scheduled event in the agenda/calendar (e.g. a meeting or a
    planned activity), independent from the tracked time entries.
    """

    NONE = ""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    RECURRENCE_CHOICES = [
        (NONE, "Does not repeat"),
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
        (YEARLY, "Yearly"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="calendar_events"
    )
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=600, blank=True, default="")
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    color = models.CharField(max_length=20, blank=True, default="")
    # Recurrence: an empty string means a one-off event. ``start``/``end`` define
    # the first occurrence; later ones are derived (see ``services``). Occurrences
    # are never stored as rows — they are expanded on read.
    recurrence = models.CharField(
        max_length=10, blank=True, default=NONE, choices=RECURRENCE_CHOICES
    )
    # Optional inclusive cut-off: no occurrence starts after this. None = forever.
    recurrence_until = models.DateTimeField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start"]


class UserTelegramSettings(models.Model):
    """
    Per-user Telegram configuration for event reminders. The bot itself is a
    single app-wide credential; this stores who to message (``chat_id``) and
    how the user wants to be reminded.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="telegram_settings"
    )
    # The user's private chat with the bot, captured on linking. None = unlinked.
    chat_id = models.CharField(max_length=64, null=True, blank=True, default=None)
    enabled = models.BooleanField(default=True)
    # How many minutes before an event to send the "heads-up" reminder.
    reminder_lead_minutes = models.PositiveIntegerField(default=15)
    # One-time token used to link a Telegram chat to this account.
    link_token = models.CharField(max_length=64, null=True, blank=True, default=None)
    link_token_created_at = models.DateTimeField(null=True, blank=True, default=None)
    connected_at = models.DateTimeField(null=True, blank=True, default=None)

    @property
    def connected(self) -> bool:
        """Whether a Telegram chat is linked to this account."""
        return bool(self.chat_id)


class UserAccessRequest(models.Model):
    """
    Gate for self-service signup: each new account starts here as ``pending``
    and stays inactive until an admin approves it. The user learns the outcome
    when they try to log in (no push needed); admins decide from the Django
    admin or the Telegram approve/reject buttons.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="access_request"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_pending(self) -> bool:
        """Whether the request is still awaiting a decision."""
        return self.status == self.PENDING


class SentReminder(models.Model):
    """
    Records that a reminder of a given ``kind`` ("lead" / "start") was already
    sent for one ``occurrence`` of an event, so the scheduler never sends it
    twice. For a one-off event the occurrence is just its ``start``; for a
    recurring event each occurrence is tracked separately. Cleared when the
    event is edited (and cascaded away when it is deleted).
    """

    event = models.ForeignKey(
        CalendarEvent, on_delete=models.CASCADE, related_name="sent_reminders"
    )
    kind = models.CharField(max_length=10)
    # The specific occurrence (its start) this reminder was sent for. Always set
    # explicitly by the scheduler; the default only exists so the field can be
    # added to existing rows.
    occurrence = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "kind", "occurrence"],
                name="unique_reminder_per_event_kind_occurrence",
            )
        ]
