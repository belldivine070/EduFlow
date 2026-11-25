"""
Support and Helpdesk views.
Handles ticketing lifecycle, conversation threads, and staff resolution workflows.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import Http404

from schools.services import resolve_school_template
from accounts.models import SchoolMembership
from core.constants import (
    MEMBERSHIP_ACTIVE,
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
)
from support.models import (
    SupportTicket,
    TicketMessage,
    TICKET_STATUS_OPEN,
    TICKET_STATUS_IN_PROGRESS,
    TICKET_STATUS_RESOLVED,
    TICKET_STATUS_CLOSED,
    TICKET_STATUS_CHOICES,
    TICKET_PRIORITY_CHOICES,
    TICKET_CATEGORY_CHOICES,
)
from support.services import (
    create_support_ticket,
    add_ticket_reply,
)


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

    def is_school_staff(self):
        if self.request.user.is_superuser:
            return True
        membership = self.get_membership()
        if not membership:
            return False
        return membership.role in {
            ROLE_DIRECTOR,
            ROLE_PRINCIPAL,
            ROLE_VICE_PRINCIPAL,
            ROLE_TEACHING_STAFF,
            ROLE_NON_TEACHING_STAFF,
        }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        school = self.get_school()
        if not school:
            messages.warning(request, "Please access support through a verified school domain.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class SupportTicketListView(SchoolRequiredMixin, View):
    """
    List support tickets.
    Staff members see all school tickets; parents/students see their own tickets.
    """
    def get(self, request):
        school = self.get_school()
        is_staff = self.is_school_staff()

        if is_staff:
            queryset = SupportTicket.objects.filter(school=school).select_related("user", "assigned_to")
        else:
            queryset = SupportTicket.objects.filter(school=school, user=request.user).select_related("user")

        # Filters
        status_filter = request.GET.get("status", "").strip()
        category_filter = request.GET.get("category", "").strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)

        template_name = resolve_school_template(school, "support/list.html")
        return render(
            request,
            template_name,
            {
                "school": school,
                "tickets": queryset[:100],
                "is_staff": is_staff,
                "status_filter": status_filter,
                "category_filter": category_filter,
                "status_choices": TICKET_STATUS_CHOICES,
                "category_choices": TICKET_CATEGORY_CHOICES,
            },
        )


class SupportTicketCreateView(SchoolRequiredMixin, View):
    """
    Submit a new support ticket.
    """
    def get(self, request):
        school = self.get_school()
        template_name = resolve_school_template(school, "support/create.html")
        return render(
            request,
            template_name,
            {
                "school": school,
                "category_choices": TICKET_CATEGORY_CHOICES,
                "priority_choices": TICKET_PRIORITY_CHOICES,
            },
        )

    def post(self, request):
        school = self.get_school()
        subject = request.POST.get("subject", "").strip()
        description = request.POST.get("description", "").strip()
        category = request.POST.get("category", "general").strip()
        priority = request.POST.get("priority", "medium").strip()

        if not subject or not description:
            messages.error(request, "Please enter both a subject and a description for your inquiry.")
            template_name = resolve_school_template(school, "support/create.html")
            return render(
                request,
                template_name,
                {
                    "school": school,
                    "category_choices": TICKET_CATEGORY_CHOICES,
                    "priority_choices": TICKET_PRIORITY_CHOICES,
                    "subject": subject,
                    "description": description,
                    "category": category,
                    "priority": priority,
                },
            )

        try:
            ticket = create_support_ticket(
                school=school,
                user=request.user,
                subject=subject,
                description=description,
                category=category,
                priority=priority,
            )
            messages.success(request, f"Support ticket #{ticket.ticket_number} created successfully.")
            return redirect("support:ticket_detail", pk=ticket.id)
        except Exception as exc:
            messages.error(request, f"Failed to submit ticket: {exc}")
            template_name = resolve_school_template(school, "support/create.html")
            return render(
                request,
                template_name,
                {
                    "school": school,
                    "category_choices": TICKET_CATEGORY_CHOICES,
                    "priority_choices": TICKET_PRIORITY_CHOICES,
                    "subject": subject,
                    "description": description,
                },
            )


class SupportTicketDetailView(SchoolRequiredMixin, View):
    """
    Detailed ticket thread view with threaded messages and status updates.
    """
    def get_ticket(self, pk):
        school = self.get_school()
        if self.is_school_staff():
            return get_object_or_404(SupportTicket, id=pk, school=school)
        return get_object_or_404(SupportTicket, id=pk, school=school, user=self.request.user)

    def get(self, request, pk):
        school = self.get_school()
        ticket = self.get_ticket(pk)
        is_staff = self.is_school_staff()

        messages_qs = ticket.messages.select_related("sender").order_by("created_at")
        if not is_staff:
            messages_qs = messages_qs.filter(is_internal_note=False)

        template_name = resolve_school_template(school, "support/detail.html")
        return render(
            request,
            template_name,
            {
                "school": school,
                "ticket": ticket,
                "ticket_messages": messages_qs,
                "is_staff": is_staff,
                "status_choices": TICKET_STATUS_CHOICES,
            },
        )

    def post(self, request, pk):
        school = self.get_school()
        ticket = self.get_ticket(pk)
        is_staff = self.is_school_staff()

        action = request.POST.get("action", "reply").strip()

        if action == "reply":
            msg_content = request.POST.get("message", "").strip()
            is_internal = request.POST.get("is_internal_note") == "true" and is_staff
            if msg_content:
                add_ticket_reply(
                    ticket=ticket,
                    sender=request.user,
                    message=msg_content,
                    is_internal_note=is_internal,
                )
                messages.success(request, "Reply added successfully.")
            else:
                messages.error(request, "Cannot submit an empty reply.")

        elif action == "update_status" and is_staff:
            new_status = request.POST.get("status", "").strip()
            if new_status in [TICKET_STATUS_OPEN, TICKET_STATUS_IN_PROGRESS, TICKET_STATUS_RESOLVED, TICKET_STATUS_CLOSED]:
                ticket.status = new_status
                if new_status in [TICKET_STATUS_RESOLVED, TICKET_STATUS_CLOSED]:
                    ticket.resolved_at = timezone.now()
                else:
                    ticket.resolved_at = None
                ticket.save(update_fields=["status", "resolved_at", "updated_at"])
                messages.success(request, f"Ticket status updated to {ticket.get_status_display()}.")

        return redirect("support:ticket_detail", pk=ticket.id)
