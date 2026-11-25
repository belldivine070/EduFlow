"""
Communications views.
Handles targeted school announcements and personal in-app notifications.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse

from schools.services import resolve_school_template
from accounts.models import SchoolMembership
from core.constants import (
    MEMBERSHIP_ACTIVE,
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
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
    AUDIENCE_CHOICES,
    MESSAGE_TYPE_CHOICES,
    DELIVERY_CHANNEL_CHOICES,
)
from communications.services import publish_announcement, resolve_audience_recipients


class SchoolRequiredMixin(LoginRequiredMixin):
    """
    Ensures the request has an active school tenant attached.
    """
    def get_school(self):
        return getattr(self.request, "school", None)

    def get_membership(self):
        school = self.get_school()
        if not school or not self.request.user.is_authenticated:
            return None
        return SchoolMembership.objects.filter(
            school=school,
            user=self.request.user,
            status=MEMBERSHIP_ACTIVE,
        ).first()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        school = self.get_school()
        if not school:
            messages.warning(request, "Please access communications through a verified school domain.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class AnnouncementListView(SchoolRequiredMixin, View):
    """
    List announcements for the school based on the user's role.
    Staff members can view all announcements; students and parents view those targeted to them or 'all'.
    """
    def get(self, request):
        school = self.get_school()
        membership = self.get_membership()
        user_role = membership.role if membership else None

        staff_roles = {ROLE_DIRECTOR, ROLE_PRINCIPAL, ROLE_VICE_PRINCIPAL, ROLE_TEACHING_STAFF}
        is_staff = user_role in staff_roles or request.user.is_superuser

        queryset = Announcement.objects.filter(school=school, is_published=True).select_related("created_by")

        if not is_staff:
            allowed_audiences = [AUDIENCE_ALL]
            if user_role == ROLE_PARENT:
                allowed_audiences.append(AUDIENCE_PARENTS)
            elif user_role == ROLE_STUDENT:
                allowed_audiences.append(AUDIENCE_STUDENTS)
            queryset = queryset.filter(target_audience__in=allowed_audiences)

        # Filter by audience if requested
        audience_filter = request.GET.get("audience", "").strip()
        if audience_filter and is_staff:
            queryset = queryset.filter(target_audience=audience_filter)

        type_filter = request.GET.get("type", "").strip()
        if type_filter:
            queryset = queryset.filter(message_type=type_filter)

        template_name = resolve_school_template(school, "communications/announcements/list.html")
        return render(
            request,
            template_name,
            {
                "school": school,
                "announcements": queryset[:50],
                "is_staff": is_staff,
                "audience_filter": audience_filter,
                "type_filter": type_filter,
                "audience_choices": AUDIENCE_CHOICES,
                "message_type_choices": MESSAGE_TYPE_CHOICES,
            },
        )


class AnnouncementCreateView(SchoolRequiredMixin, View):
    """
    Create and broadcast an official announcement across the school.
    Restricted to School Directors, Principals, and Vice Principals.
    """
    def dispatch(self, request, *args, **kwargs):
        dispatch_result = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return dispatch_result
        membership = self.get_membership()
        allowed_roles = {ROLE_DIRECTOR, ROLE_PRINCIPAL, ROLE_VICE_PRINCIPAL}
        if not (request.user.is_superuser or (membership and membership.role in allowed_roles)):
            messages.error(request, "Only school administrators can create official announcements.")
            return redirect("communications:announcement_list")
        return dispatch_result

    def get(self, request):
        school = self.get_school()
        template_name = resolve_school_template(school, "communications/announcements/create.html")
        return render(
            request,
            template_name,
            {
                "school": school,
                "audience_choices": AUDIENCE_CHOICES,
                "message_type_choices": MESSAGE_TYPE_CHOICES,
                "channel_choices": DELIVERY_CHANNEL_CHOICES,
            },
        )

    def post(self, request):
        school = self.get_school()
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        target_audience = request.POST.get("target_audience", AUDIENCE_ALL).strip()
        message_type = request.POST.get("message_type", "announcement").strip()
        channel = request.POST.get("channel", "in_app").strip()

        if not title or not content:
            messages.error(request, "Please provide both a title and content for the announcement.")
            template_name = resolve_school_template(school, "communications/announcements/create.html")
            return render(
                request,
                template_name,
                {
                    "school": school,
                    "audience_choices": AUDIENCE_CHOICES,
                    "message_type_choices": MESSAGE_TYPE_CHOICES,
                    "channel_choices": DELIVERY_CHANNEL_CHOICES,
                    "title": title,
                    "content": content,
                    "target_audience": target_audience,
                    "message_type": message_type,
                    "channel": channel,
                },
            )

        try:
            announcement = publish_announcement(
                school=school,
                title=title,
                content=content,
                target_audience=target_audience,
                message_type=message_type,
                channel=channel,
                created_by=request.user,
            )
            messages.success(request, f"Announcement '{announcement.title}' published successfully.")
            return redirect("communications:announcement_list")
        except Exception as exc:
            messages.error(request, f"Failed to publish announcement: {exc}")
            template_name = resolve_school_template(school, "communications/announcements/create.html")
            return render(
                request,
                template_name,
                {
                    "school": school,
                    "audience_choices": AUDIENCE_CHOICES,
                    "message_type_choices": MESSAGE_TYPE_CHOICES,
                    "channel_choices": DELIVERY_CHANNEL_CHOICES,
                    "title": title,
                    "content": content,
                },
            )


class NotificationListView(SchoolRequiredMixin, View):
    """
    User's personal in-app notifications inbox.
    """
    def get(self, request):
        school = self.get_school()
        notifications = Notification.objects.filter(
            school=school,
            recipient=request.user,
        ).order_by("-created_at")[:100]

        unread_count = Notification.objects.filter(
            school=school,
            recipient=request.user,
            is_read=False,
        ).count()

        template_name = resolve_school_template(school, "communications/notifications.html")
        return render(
            request,
            template_name,
            {
                "school": school,
                "notifications": notifications,
                "unread_count": unread_count,
            },
        )


class NotificationMarkReadView(SchoolRequiredMixin, View):
    """
    Marks a single notification as read.
    """
    def post(self, request, pk):
        school = self.get_school()
        notification = get_object_or_404(Notification, id=pk, school=school, recipient=request.user)
        notification.mark_as_read()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "ok", "id": str(notification.id)})
        messages.success(request, "Notification marked as read.")
        return redirect("communications:notification_list")


class NotificationMarkAllReadView(SchoolRequiredMixin, View):
    """
    Marks all notifications for current user as read.
    """
    def post(self, request):
        school = self.get_school()
        Notification.objects.filter(
            school=school,
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "ok"})
        messages.success(request, "All notifications marked as read.")
        return redirect("communications:notification_list")
