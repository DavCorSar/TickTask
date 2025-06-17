"""
Definition of the database tables that will be used in our application.
"""

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
