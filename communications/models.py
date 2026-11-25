"""
Communications and Notifications data models.

Supports:
- Targeted school announcements by audience (all school, teaching staff, non-teaching staff, parents, students).
- In-app notification delivery ledger with read/unread tracking.
- Secure tenant-scoped recipient resolution preventing unauthorized messaging.
"""
import uuid
from django.db import models
from django.utils import timezone
from core.models import TimestampedModel

AUDIENCE_ALL = "all"
AUDIENCE_ALL_STAFF = "all_staff"
AUDIENCE_TEACHING_STAFF = "teaching_staff"
AUDIENCE_NON_TEACHING_STAFF = "non_teaching_staff"
AUDIENCE_PARENTS = "parents"
AUDIENCE_STUDENTS = "students"

AUDIENCE_CHOICES = [
    (AUDIENCE_ALL, "All School Members"),
    (AUDIENCE_ALL_STAFF, "All Staff Members"),
    (AUDIENCE_TEACHING_STAFF, "Teaching Staff Only"),
    (AUDIENCE_NON_TEACHING_STAFF, "Non-Teaching Staff Only"),
    (AUDIENCE_PARENTS, "Parents / Guardians"),
    (AUDIENCE_STUDENTS, "Students Only"),
]

MESSAGE_TYPE_ANNOUNCEMENT = "announcement"
MESSAGE_TYPE_REMINDER = "reminder"
MESSAGE_TYPE_ALERT = "alert"
MESSAGE_TYPE_EVENT = "event"

MESSAGE_TYPE_CHOICES = [
    (MESSAGE_TYPE_ANNOUNCEMENT, "Official Announcement"),
    (MESSAGE_TYPE_REMINDER, "Reminder"),
    (MESSAGE_TYPE_ALERT, "Urgent Notice / Alert"),
    (MESSAGE_TYPE_EVENT, "School Event"),
]

DELIVERY_CHANNEL_IN_APP = "in_app"
DELIVERY_CHANNEL_EMAIL = "email"
DELIVERY_CHANNEL_SMS = "sms"
DELIVERY_CHANNEL_ALL = "all"

DELIVERY_CHANNEL_CHOICES = [
    (DELIVERY_CHANNEL_IN_APP, "In-App Notification"),
    (DELIVERY_CHANNEL_EMAIL, "Email"),
    (DELIVERY_CHANNEL_SMS, "SMS"),
    (DELIVERY_CHANNEL_ALL, "Multi-Channel (In-App & Email)"),
]


class Announcement(TimestampedModel):
    """
    Administrative announcement issued by the School Director or Principal.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_audience = models.CharField(
        max_length=30,
        choices=AUDIENCE_CHOICES,
        default=AUDIENCE_ALL,
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default=MESSAGE_TYPE_ANNOUNCEMENT,
    )
    channel = models.CharField(
        max_length=20,
        choices=DELIVERY_CHANNEL_CHOICES,
        default=DELIVERY_CHANNEL_IN_APP,
    )
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_announcements",
    )

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        ordering = ["-published_at"]

    def __str__(self):
        return f"{self.title} ({self.get_target_audience_display()}) - {self.school.code}"


class Notification(models.Model):
    """
    Personalized in-app notification delivered to a tenant member.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="delivered_notifications",
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, default="")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(
        max_length=20,
        choices=[("delivered", "Delivered"), ("failed", "Failed")],
        default="delivered",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        read_badge = "Read" if self.is_read else "Unread"
        return f"[{read_badge}] {self.title} -> {self.recipient.username}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
