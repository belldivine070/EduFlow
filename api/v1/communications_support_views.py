"""
Communications & Support API v1 views and serializers.
"""
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.permissions import (
    IsTenantAdmin,
    IsTenantMember,
    STAFF_ROLES,
    get_active_membership,
)
from communications.models import (
    AUDIENCE_ALL,
    AUDIENCE_PARENTS,
    AUDIENCE_STUDENTS,
    Announcement,
    Notification,
)
from communications.services import publish_announcement
from core.constants import ROLE_PARENT, ROLE_STUDENT
from support.models import (
    SupportTicket,
    TICKET_STATUS_CLOSED,
    TICKET_STATUS_IN_PROGRESS,
    TICKET_STATUS_OPEN,
    TICKET_STATUS_RESOLVED,
    TicketMessage,
)
from support.services import add_ticket_reply, create_support_ticket


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "content",
            "target_audience",
            "message_type",
            "channel",
            "is_published",
            "published_at",
            "created_by_name",
        ]
        read_only_fields = ["id", "is_published", "published_at", "created_by_name"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "link", "is_read", "read_at", "created_at"]


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)

    class Meta:
        model = TicketMessage
        fields = ["id", "sender", "sender_name", "message", "is_internal_note", "created_at"]


class SupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_number",
            "user",
            "user_name",
            "category",
            "priority",
            "status",
            "subject",
            "description",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "ticket_number", "user", "user_name", "status", "resolved_at", "created_at", "updated_at"]


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsTenantMember()]
        return [IsTenantAdmin()]

    def get_queryset(self):
        school = self.request.school
        qs = Announcement.objects.filter(school=school, is_published=True).select_related("created_by")
        membership = get_active_membership(self.request)
        if not self.request.user.is_superuser and membership and membership.role not in STAFF_ROLES:
            allowed = [AUDIENCE_ALL]
            if membership.role == ROLE_PARENT:
                allowed.append(AUDIENCE_PARENTS)
            elif membership.role == ROLE_STUDENT:
                allowed.append(AUDIENCE_STUDENTS)
            qs = qs.filter(target_audience__in=allowed)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        announcement = publish_announcement(
            school=request.school,
            title=serializer.validated_data["title"],
            content=serializer.validated_data["content"],
            target_audience=serializer.validated_data.get("target_audience", AUDIENCE_ALL),
            message_type=serializer.validated_data.get("message_type", "announcement"),
            channel=serializer.validated_data.get("channel", "in_app"),
            created_by=request.user,
        )
        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Notification.objects.filter(school=self.request.school, recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        note = self.get_object()
        note.mark_as_read()
        return Response(NotificationSerializer(note).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"marked_read": updated})


class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsTenantMember]

    def _is_staff(self):
        if self.request.user.is_superuser:
            return True
        m = get_active_membership(self.request)
        return bool(m and m.role in STAFF_ROLES)

    def get_queryset(self):
        school = self.request.school
        qs = SupportTicket.objects.filter(school=school).select_related("user")
        if self._is_staff():
            return qs
        return qs.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = create_support_ticket(
            school=request.school,
            user=request.user,
            subject=serializer.validated_data["subject"],
            description=serializer.validated_data["description"],
            category=serializer.validated_data.get("category", "general"),
            priority=serializer.validated_data.get("priority", "medium"),
        )
        return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        ticket = self.get_object()
        is_staff = self._is_staff()
        if request.method == "GET":
            qs = ticket.messages.select_related("sender").order_by("created_at")
            if not is_staff:
                qs = qs.filter(is_internal_note=False)
            return Response(TicketMessageSerializer(qs, many=True).data)

        msg = request.data.get("message", "").strip()
        if not msg:
            return Response({"detail": "Message cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        is_internal = bool(request.data.get("is_internal_note", False)) and is_staff
        reply = add_ticket_reply(
            ticket=ticket,
            sender=request.user,
            message=msg,
            is_internal_note=is_internal,
        )
        return Response(TicketMessageSerializer(reply).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        if not self._is_staff():
            return Response({"detail": "Staff privileges required."}, status=status.HTTP_403_FORBIDDEN)
        ticket = self.get_object()
        new_status = request.data.get("status")
        if new_status not in {TICKET_STATUS_OPEN, TICKET_STATUS_IN_PROGRESS, TICKET_STATUS_RESOLVED, TICKET_STATUS_CLOSED}:
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = new_status
        ticket.resolved_at = timezone.now() if new_status in {TICKET_STATUS_RESOLVED, TICKET_STATUS_CLOSED} else None
        ticket.save(update_fields=["status", "resolved_at", "updated_at"])
        return Response(SupportTicketSerializer(ticket).data)
