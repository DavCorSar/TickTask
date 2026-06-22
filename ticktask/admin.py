"""
Django admin registration. Editing/renaming tasks and subtasks and deleting
time entries are management operations, so they live here (superuser only)
rather than in the user-facing UI.
"""

from django.contrib import admin
from django.utils import timezone

from ticktask.models import (
    UserLoginRecord,
    Task,
    SubTask,
    TimeEntry,
    CalendarEvent,
    UserTelegramSettings,
)


@admin.action(description="Soft-delete selected (set deleted_at)")
def soft_delete(modeladmin, request, queryset):
    """Marks the selected rows as deleted, leaving the rows in place."""
    queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())


@admin.action(description="Restore selected (clear deleted_at)")
def restore(modeladmin, request, queryset):
    """Clears the soft-delete flag of the selected rows."""
    queryset.update(deleted_at=None)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Edit/rename tasks and manage their soft-delete state."""

    list_display = ("name", "user", "deleted_at")
    list_filter = (("deleted_at", admin.EmptyFieldListFilter), "user")
    search_fields = ("name", "user__username")
    ordering = ("user__username", "name")
    list_select_related = ("user",)
    autocomplete_fields = ("user",)
    actions = (soft_delete, restore)


@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    """Edit/rename subtasks and manage their soft-delete state."""

    list_display = ("name", "task", "owner", "deleted_at")
    list_filter = (("deleted_at", admin.EmptyFieldListFilter),)
    search_fields = ("name", "task__name", "task__user__username")
    ordering = ("task__name", "name")
    list_select_related = ("task", "task__user")
    autocomplete_fields = ("task",)
    actions = (soft_delete, restore)

    @admin.display(description="User", ordering="task__user__username")
    def owner(self, obj):
        """The user the subtask ultimately belongs to."""
        return obj.task.user


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    """Inspect and delete individual time entries."""

    list_display = ("id", "subtask", "owner", "clock_in", "clock_out", "duration")
    list_filter = (("clock_out", admin.EmptyFieldListFilter),)
    search_fields = (
        "subtask__name",
        "subtask__task__name",
        "subtask__task__user__username",
    )
    date_hierarchy = "clock_in"
    ordering = ("-clock_in",)
    list_select_related = ("subtask", "subtask__task", "subtask__task__user")
    autocomplete_fields = ("subtask",)

    @admin.display(description="User")
    def owner(self, obj):
        """The user the entry ultimately belongs to."""
        return obj.subtask.task.user

    @admin.display(description="Duration")
    def duration(self, obj):
        """Tracked duration, or '—' while the entry is still open."""
        return obj.get_time_dedicated() if obj.clock_out else "—"


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    """Manage scheduled calendar events."""

    list_display = ("title", "user", "start", "end", "all_day")
    list_filter = ("all_day", "user")
    search_fields = ("title", "user__username")
    date_hierarchy = "start"
    ordering = ("-start",)
    list_select_related = ("user",)
    autocomplete_fields = ("user",)


@admin.register(UserTelegramSettings)
class UserTelegramSettingsAdmin(admin.ModelAdmin):
    """Per-user Telegram reminder settings and link status."""

    list_display = ("user", "connected", "enabled", "reminder_lead_minutes")
    list_filter = ("enabled",)
    search_fields = ("user__username", "chat_id")
    list_select_related = ("user",)
    autocomplete_fields = ("user",)

    @admin.display(boolean=True, description="Connected")
    def connected(self, obj):
        """Whether a Telegram chat is linked."""
        return obj.connected


@admin.register(UserLoginRecord)
class UserLoginRecordAdmin(admin.ModelAdmin):
    """Read-only-ish view of user login history."""

    list_display = ("user", "login_time", "ip_address")
    list_filter = ("user",)
    search_fields = ("user__username", "ip_address")
    date_hierarchy = "login_time"
    ordering = ("-login_time",)
    list_select_related = ("user",)
