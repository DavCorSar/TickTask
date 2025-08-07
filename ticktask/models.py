"""
Definition of the database tables that will be used in our application.
"""

from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User


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

    class Meta:
        """
        Include the unique constraint of task name per user.
        """

        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_task_per_user"
            )
        ]

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

    class Meta:
        """
        Include the unique constraint of subtask name per task.
        """

        constraints = [
            models.UniqueConstraint(
                fields=["task", "name"], name="unique_subtask_per_task"
            )
        ]

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
    clock_in = models.DateTimeField(auto_now_add=True)
    clock_out = models.DateTimeField(null=True, blank=True)

    def get_time_dedicated(self) -> timedelta:
        """
        This function will return the amount of time
        dedicated to this individual time entry.
        """
        if self.clock_out:
            return self.clock_out - self.clock_in
        return timedelta()
