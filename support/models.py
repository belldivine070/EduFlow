"""
Support and Helpdesk data models.

Supports:
- Ticket tracking with category, priority, and resolution statuses.
- Threaded ticket messages and internal administrative notes.
- Secure tenant-scoped authorization.
"""
import uuid
from django.db import models
from django.utils import timezone
from core.models import TimestampedModel

TICKET_STATUS_OPEN = "open"
TICKET_STATUS_IN_PROGRESS = "in_progress"
TICKET_STATUS_RESOLVED = "resolved"
TICKET_STATUS_CLOSED = "closed"

TICKET_STATUS_CHOICES = [
    (TICKET_STATUS_OPEN, "Open"),
    (TICKET_STATUS_IN_PROGRESS, "In Progress"),
    (TICKET_STATUS_RESOLVED, "Resolved"),
    (TICKET_STATUS_CLOSED, "Closed"),
]

TICKET_PRIORITY_LOW = "low"
TICKET_PRIORITY_MEDIUM = "medium"
TICKET_PRIORITY_HIGH = "high"
TICKET_PRIORITY_URGENT = "urgent"

TICKET_PRIORITY_CHOICES = [
    (TICKET_PRIORITY_LOW, "Low"),
    (TICKET_PRIORITY_MEDIUM, "Medium"),
    (TICKET_PRIORITY_HIGH, "High"),
    (TICKET_PRIORITY_URGENT, "Urgent"),
]

TICKET_CATEGORY_ACADEMIC = "academic"
TICKET_CATEGORY_BILLING = "billing"
TICKET_CATEGORY_TECHNICAL = "technical"
TICKET_CATEGORY_ADMISSIONS = "admissions"
TICKET_CATEGORY_GENERAL = "general"

TICKET_CATEGORY_CHOICES = [
    (TICKET_CATEGORY_ACADEMIC, "Academic / Results / Classes"),
    (TICKET_CATEGORY_BILLING, "Fees / Invoices / Payments"),
    (TICKET_CATEGORY_TECHNICAL, "Portal Login / Technical Support"),
    (TICKET_CATEGORY_ADMISSIONS, "Admissions & Onboarding"),
    (TICKET_CATEGORY_GENERAL, "General Inquiries"),
]


class SupportTicket(TimestampedModel):
    """
    Helpdesk support ticket submitted by parent, student, or staff.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    ticket_number = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Format: {SCHOOL_CODE}-TIC-{YEAR}-{SEQ:04d}",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    category = models.CharField(
        max_length=30,
        choices=TICKET_CATEGORY_CHOICES,
        default=TICKET_CATEGORY_GENERAL,
    )
    priority = models.CharField(
        max_length=20,
        choices=TICKET_PRIORITY_CHOICES,
        default=TICKET_PRIORITY_MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=TICKET_STATUS_CHOICES,
        default=TICKET_STATUS_OPEN,
        db_index=True,
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Support Ticket"
        verbose_name_plural = "Support Tickets"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["school", "ticket_number"], name="unique_school_support_ticket")
        ]

    def __str__(self):
        return f"{self.ticket_number} - {self.subject} ({self.get_status_display()})"


class TicketMessage(models.Model):
    """
    Threaded message reply in a SupportTicket.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="sent_ticket_messages",
    )
    message = models.TextField()
    is_internal_note = models.BooleanField(
        default=False,
        help_text="Visible only to school administrative staff.",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Ticket Message"
        verbose_name_plural = "Ticket Messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply from {self.sender.username} on {self.ticket.ticket_number}"
