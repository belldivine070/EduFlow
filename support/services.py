"""
Support services.

Handles ticket generation, threaded replies, and status transitions.
"""
from django.db import transaction
from django.utils import timezone
from support.models import (
    SupportTicket,
    TicketMessage,
    TICKET_STATUS_OPEN,
    TICKET_STATUS_RESOLVED,
    TICKET_STATUS_CLOSED,
)


def generate_ticket_number(school) -> str:
    """
    Generate unique support ticket number for school tenant.
    Format: {SCHOOL_CODE}-TIC-{YEAR}-{SEQ:04d}
    """
    year = str(timezone.now().year)
    prefix = f"{school.code}-TIC-{year}-"
    latest = (
        SupportTicket.objects.filter(school=school, ticket_number__startswith=prefix)
        .order_by("-ticket_number")
        .first()
    )
    if latest:
        try:
            last_seq = int(latest.ticket_number.split("-")[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1
    return f"{prefix}{new_seq:04d}"


@transaction.atomic
def create_support_ticket(
    *,
    school,
    user,
    subject: str,
    description: str,
    category: str,
    priority: str = "medium",
) -> SupportTicket:
    """
    Submit a new support ticket.
    """
    ticket_num = generate_ticket_number(school)
    ticket = SupportTicket.objects.create(
        school=school,
        ticket_number=ticket_num,
        user=user,
        subject=subject.strip(),
        description=description.strip(),
        category=category,
        priority=priority,
        status=TICKET_STATUS_OPEN,
    )
    return ticket


@transaction.atomic
def add_ticket_reply(
    *,
    ticket: SupportTicket,
    sender,
    message: str,
    is_internal_note: bool = False,
) -> TicketMessage:
    """
    Add a reply message or internal staff note to a ticket.
    """
    reply = TicketMessage.objects.create(
        ticket=ticket,
        sender=sender,
        message=message.strip(),
        is_internal_note=is_internal_note,
        created_at=timezone.now(),
    )

    # Reopen ticket if user replies to a resolved ticket
    if not is_internal_note and ticket.status in [TICKET_STATUS_RESOLVED, TICKET_STATUS_CLOSED] and sender == ticket.user:
        ticket.status = TICKET_STATUS_OPEN
        ticket.resolved_at = None
        ticket.save(update_fields=["status", "resolved_at", "updated_at"])

    return reply
