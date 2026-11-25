"""
Communications services.

Handles audience resolution based on tenant membership roles,
announcement publication, and fan-out of in-app notifications.
"""
from django.db import transaction
from django.utils import timezone
from accounts.models import SchoolMembership, User
from core.constants import (
    MEMBERSHIP_ACTIVE,
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
    ROLE_PARENT,
    ROLE_STUDENT,
)
from communications.models import (
    Announcement,
    Notification,
    AUDIENCE_ALL,
    AUDIENCE_ALL_STAFF,
    AUDIENCE_TEACHING_STAFF,
    AUDIENCE_NON_TEACHING_STAFF,
    AUDIENCE_PARENTS,
    AUDIENCE_STUDENTS,
    MESSAGE_TYPE_ANNOUNCEMENT,
    DELIVERY_CHANNEL_IN_APP,
)

STAFF_ROLES_SET = {
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
}


def resolve_audience_recipients(school, audience: str) -> list[User]:
    """
    Safely resolves recipient users within the school tenant based on membership role.
    Prevents bypassing audience permissions or arbitrary user injections.
    """
    base_qs = SchoolMembership.objects.filter(school=school, status=MEMBERSHIP_ACTIVE).select_related("user")

    if audience == AUDIENCE_ALL:
        memberships = base_qs
    elif audience == AUDIENCE_ALL_STAFF:
        memberships = base_qs.filter(role__in=STAFF_ROLES_SET)
    elif audience == AUDIENCE_TEACHING_STAFF:
        memberships = base_qs.filter(role=ROLE_TEACHING_STAFF)
    elif audience == AUDIENCE_NON_TEACHING_STAFF:
        memberships = base_qs.filter(role=ROLE_NON_TEACHING_STAFF)
    elif audience == AUDIENCE_PARENTS:
        memberships = base_qs.filter(role=ROLE_PARENT)
    elif audience == AUDIENCE_STUDENTS:
        memberships = base_qs.filter(role=ROLE_STUDENT)
    else:
        memberships = base_qs

    users = [m.user for m in memberships]
    return list({u.id: u for u in users}.values())


@transaction.atomic
def publish_announcement(
    *,
    school,
    title: str,
    content: str,
    target_audience: str = AUDIENCE_ALL,
    message_type: str = MESSAGE_TYPE_ANNOUNCEMENT,
    channel: str = DELIVERY_CHANNEL_IN_APP,
    created_by=None,
) -> Announcement:
    """
    Publish an official announcement and fan out in-app notifications to all target recipients.
    """
    announcement = Announcement.objects.create(
        school=school,
        title=title.strip(),
        content=content.strip(),
        target_audience=target_audience,
        message_type=message_type,
        channel=channel,
        is_published=True,
        published_at=timezone.now(),
        created_by=created_by,
    )

    recipients = resolve_audience_recipients(school, target_audience)

    # Bulk create in-app notifications
    notifications_to_create = [
        Notification(
            school=school,
            recipient=recipient,
            announcement=announcement,
            title=announcement.title,
            message=announcement.content[:200],
            link="/communications/announcements/",
            is_read=False,
            delivery_status="delivered",
            created_at=timezone.now(),
        )
        for recipient in recipients
    ]

    if notifications_to_create:
        Notification.objects.bulk_create(notifications_to_create)

    return announcement
