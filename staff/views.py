"""
Staff views.

Covers:
- StaffListView: Staff directory with search, role filters, and statistics
- StaffCreateView: Onboard a new staff member with auto-generated numeric Staff ID
- StaffDetailView: View detailed staff employment profile
- StaffStatusToggleView: Activate or deactivate a staff member's school membership
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from accounts.models import User, SchoolMembership
from accounts.services import create_school_user, STAFF_ROLES
from staff.models import (
    StaffProfile,
    StaffDocument,
    StaffAttendance,
    GENDER_CHOICES,
    EMPLOYMENT_TYPE_CHOICES,
    STAFF_DOC_TYPE_CHOICES,
    STAFF_ATTENDANCE_CHOICES,
    STAFF_ATTENDANCE_PRESENT,
)
from academics.models import Subject
from staff.services import record_staff_attendance
from schools.services import resolve_school_template
from core.constants import (
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
    MEMBERSHIP_ACTIVE,
    MEMBERSHIP_INACTIVE,
)

STAFF_MANAGEMENT_ROLES = {ROLE_DIRECTOR, ROLE_PRINCIPAL}


class StaffListView(LoginRequiredMixin, View):
    """
    Staff directory for the active school tenant.
    Displays all staff members with search and filter capabilities.
    """

    def get(self, request):
        school = getattr(request, "school", None)
        if not school:
            messages.warning(request, "Please access the staff directory through a school portal.")
            return redirect("accounts:dashboard")

        # Base queryset of all staff memberships in this school
        memberships = (
            SchoolMembership.objects.filter(
                school=school,
                role__in=STAFF_ROLES,
            )
            .select_related("user")
            .order_by("user__last_name", "user__first_name")
        )

        # Search filter
        query = request.GET.get("q", "").strip()
        if query:
            memberships = memberships.filter(
                Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__username__icontains=query)
                | Q(user__email__icontains=query)
                | Q(user__phone_number__icontains=query)
            )

        # Role filter
        selected_role = request.GET.get("role", "").strip()
        if selected_role and selected_role in STAFF_ROLES:
            memberships = memberships.filter(role=selected_role)

        # Calculate counts
        total_staff = SchoolMembership.objects.filter(school=school, role__in=STAFF_ROLES).count()
        active_staff = SchoolMembership.objects.filter(
            school=school, role__in=STAFF_ROLES, status=MEMBERSHIP_ACTIVE
        ).count()
        teaching_staff = SchoolMembership.objects.filter(
            school=school, role=ROLE_TEACHING_STAFF
        ).count()
        non_teaching_staff = SchoolMembership.objects.filter(
            school=school, role=ROLE_NON_TEACHING_STAFF
        ).count()

        # Check if current user has management permissions (can add/edit staff)
        can_manage_staff = (
            getattr(request.user, "is_platform_developer", False)
            or request.user.is_superuser
            or request.user.memberships.filter(
                school=school, role__in=STAFF_MANAGEMENT_ROLES, status=MEMBERSHIP_ACTIVE
            ).exists()
        )

        template = resolve_school_template(school, "staff/list.html")
        return render(
            request,
            template,
            {
                "memberships": memberships,
                "current_school": school,
                "total_staff": total_staff,
                "active_staff": active_staff,
                "teaching_staff": teaching_staff,
                "non_teaching_staff": non_teaching_staff,
                "query": query,
                "selected_role": selected_role,
                "can_manage_staff": can_manage_staff,
                "staff_roles": [
                    (ROLE_DIRECTOR, "School Director"),
                    (ROLE_PRINCIPAL, "Principal"),
                    (ROLE_VICE_PRINCIPAL, "Vice Principal"),
                    (ROLE_TEACHING_STAFF, "Teaching Staff"),
                    (ROLE_NON_TEACHING_STAFF, "Non-Teaching Staff"),
                ],
            },
        )


class StaffCreateView(LoginRequiredMixin, View):
    """
    Onboard a new staff member to the active school tenant.
    Restricted to School Directors, Principals, and Platform Developers.
    """

    def check_permission(self, request, school):
        if getattr(request.user, "is_platform_developer", False) or request.user.is_superuser:
            return True
        return request.user.memberships.filter(
            school=school, role__in=STAFF_MANAGEMENT_ROLES, status=MEMBERSHIP_ACTIVE
        ).exists()

    def get(self, request):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        if not self.check_permission(request, school):
            messages.error(request, "Only school leadership can onboard new staff.")
            return redirect("staff:staff_list")

        template = resolve_school_template(school, "staff/create.html")
        subjects = Subject.objects.filter(school=school, is_active=True).order_by("name")
        return render(
            request,
            template,
            {
                "current_school": school,
                "gender_choices": GENDER_CHOICES,
                "employment_types": EMPLOYMENT_TYPE_CHOICES,
                "doc_types": STAFF_DOC_TYPE_CHOICES,
                "subjects": subjects,
                "staff_roles": [
                    (ROLE_TEACHING_STAFF, "Teaching Staff"),
                    (ROLE_NON_TEACHING_STAFF, "Non-Teaching Staff"),
                    (ROLE_VICE_PRINCIPAL, "Vice Principal"),
                    (ROLE_PRINCIPAL, "Principal"),
                    (ROLE_DIRECTOR, "School Director"),
                ],
            },
        )

    def post(self, request):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        if not self.check_permission(request, school):
            messages.error(request, "Only school leadership can onboard new staff.")
            return redirect("staff:staff_list")

        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        middle_name = request.POST.get("middle_name", "").strip()
        email = request.POST.get("email", "").strip().lower() or None
        phone_number = request.POST.get("phone_number", "").strip() or None
        role = request.POST.get("role", ROLE_TEACHING_STAFF).strip()

        title = request.POST.get("title", "").strip()
        gender = request.POST.get("gender", "").strip()
        qualification = request.POST.get("qualification", "").strip()
        specialization = request.POST.get("specialization", "").strip()
        designation = request.POST.get("designation", "").strip() or "Staff Member"
        employment_type = request.POST.get("employment_type", "full_time").strip()
        trcn_number = request.POST.get("trcn_number", "").strip()
        nin = request.POST.get("nin", "").strip()
        subject_ids = request.POST.getlist("assigned_subjects")
        date_employed = request.POST.get("date_employed") or None
        residential_address = request.POST.get("residential_address", "").strip()
        next_of_kin_name = request.POST.get("next_of_kin_name", "").strip()
        next_of_kin_phone = request.POST.get("next_of_kin_phone", "").strip()
        next_of_kin_relationship = request.POST.get("next_of_kin_relationship", "").strip()

        password = request.POST.get("password", "").strip() or "EduFlowStaff123!"

        if not first_name or not last_name:
            messages.error(request, "First name and last name are required.")
            return redirect("staff:staff_create")

        if role not in STAFF_ROLES:
            messages.error(request, "Please select a valid staff role.")
            return redirect("staff:staff_create")

        if email and User.objects.filter(email=email).exists():
            messages.error(request, f"A user with email '{email}' already exists.")
            return redirect("staff:staff_create")

        with transaction.atomic():
            # 1. Create user with unique random numeric staff ID
            user, membership = create_school_user(
                school=school,
                role=role,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                email=email,
                phone_number=phone_number,
                password=password,
            )

            # 2. Create detailed StaffProfile
            staff_profile = StaffProfile.objects.create(
                school=school,
                user=user,
                title=title,
                gender=gender,
                qualification=qualification,
                specialization=specialization,
                designation=designation,
                employment_type=employment_type,
                trcn_number=trcn_number,
                nin=nin,
                date_employed=date_employed,
                residential_address=residential_address,
                next_of_kin_name=next_of_kin_name,
                next_of_kin_phone=next_of_kin_phone,
                next_of_kin_relationship=next_of_kin_relationship,
            )

            # 3. Assign selected subjects
            if subject_ids:
                valid_subjects = Subject.objects.filter(school=school, id__in=subject_ids)
                staff_profile.assigned_subjects.set(valid_subjects)

            # 4. Save uploaded qualification / onboarding document(s)
            doc_file = request.FILES.get("qualification_doc")
            if doc_file:
                doc_type = request.POST.get("qualification_doc_type", "degree_certificate").strip()
                StaffDocument.objects.create(
                    school=school,
                    staff=staff_profile,
                    document_type=doc_type,
                    file=doc_file,
                    original_filename=doc_file.name,
                )

            extra_doc = request.FILES.get("secondary_doc")
            if extra_doc:
                extra_type = request.POST.get("secondary_doc_type", "trcn_certificate").strip()
                StaffDocument.objects.create(
                    school=school,
                    staff=staff_profile,
                    document_type=extra_type,
                    file=extra_doc,
                    original_filename=extra_doc.name,
                )

        messages.success(
            request,
            f"Staff member {user.get_full_name()} onboarded successfully! Staff ID: {user.username}",
        )
        return redirect("staff:staff_list")


class StaffDetailView(LoginRequiredMixin, View):
    """
    View complete staff member details.
    """

    def get(self, request, membership_id):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        membership = get_object_or_404(
            SchoolMembership.objects.select_related("user"),
            id=membership_id,
            school=school,
            role__in=STAFF_ROLES,
        )

        profile = StaffProfile.objects.filter(school=school, user=membership.user).first()

        can_manage_staff = (
            getattr(request.user, "is_platform_developer", False)
            or request.user.is_superuser
            or request.user.memberships.filter(
                school=school, role__in=STAFF_MANAGEMENT_ROLES, status=MEMBERSHIP_ACTIVE
            ).exists()
        )

        template = resolve_school_template(school, "staff/detail.html")
        return render(
            request,
            template,
            {
                "membership": membership,
                "staff_user": membership.user,
                "profile": profile,
                "current_school": school,
                "can_manage_staff": can_manage_staff,
            },
        )


class StaffStatusToggleView(LoginRequiredMixin, View):
    """
    Toggle a staff member's school membership between active and inactive.
    """

    def post(self, request, membership_id):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        membership = get_object_or_404(
            SchoolMembership.objects.select_related("user"),
            id=membership_id,
            school=school,
            role__in=STAFF_ROLES,
        )

        # Do not allow deactivating yourself
        if membership.user == request.user:
            messages.error(request, "You cannot deactivate your own membership.")
            return redirect("staff:staff_list")

        if membership.status == MEMBERSHIP_ACTIVE:
            membership.status = MEMBERSHIP_INACTIVE
            state_str = "deactivated"
        else:
            membership.status = MEMBERSHIP_ACTIVE
            state_str = "activated"

        membership.save(update_fields=["status", "updated_at"])
        messages.success(request, f"{membership.user.get_full_name()} has been {state_str}.")
        return redirect("staff:staff_list")


class StaffAttendanceRegisterView(LoginRequiredMixin, View):
    """
    Daily staff attendance register for Principal, Vice Principal, and Directors.
    """

    def get(self, request):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        date_str = request.GET.get("date")
        target_date = timezone.now().date()
        if date_str:
            try:
                target_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        # All active staff members in this school
        staff_memberships = (
            SchoolMembership.objects
            .filter(school=school, role__in=STAFF_ROLES, status=MEMBERSHIP_ACTIVE)
            .select_related("user")
            .order_by("user__last_name", "user__first_name")
        )

        # Get existing attendance records for this date
        staff_profiles = {
            sp.user_id: sp
            for sp in StaffProfile.objects.filter(school=school, user__in=[m.user for m in staff_memberships])
        }

        existing_records = {
            att.staff_id: att
            for att in StaffAttendance.objects.filter(school=school, date=target_date)
        }

        staff_roster = []
        for m in staff_memberships:
            sp = staff_profiles.get(m.user_id)
            if not sp:
                # Ensure staff profile exists
                sp, _ = StaffProfile.objects.get_or_create(school=school, user=m.user)

            att = existing_records.get(sp.id)
            staff_roster.append({
                "membership": m,
                "staff_profile": sp,
                "status": att.status if att else STAFF_ATTENDANCE_PRESENT,
                "time_in": att.time_in.strftime("%H:%M") if (att and att.time_in) else "",
                "time_out": att.time_out.strftime("%H:%M") if (att and att.time_out) else "",
                "remarks": att.remarks if att else "",
            })

        context = {
            "staff_roster": staff_roster,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "attendance_choices": STAFF_ATTENDANCE_CHOICES,
        }
        template = resolve_school_template(school, "staff/attendance/register.html")
        return render(request, template, context)

    def post(self, request):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        date_str = request.POST.get("date")
        try:
            target_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            target_date = timezone.now().date()

        staff_ids = request.POST.getlist("staff_ids")
        records = []
        for s_id in staff_ids:
            status = request.POST.get(f"status_{s_id}", STAFF_ATTENDANCE_PRESENT)
            time_in = request.POST.get(f"time_in_{s_id}", "").strip() or None
            time_out = request.POST.get(f"time_out_{s_id}", "").strip() or None
            remarks = request.POST.get(f"remarks_{s_id}", "").strip()

            records.append({
                "staff_id": s_id,
                "status": status,
                "time_in": time_in,
                "time_out": time_out,
                "remarks": remarks,
            })

        count = record_staff_attendance(
            school=school,
            date=target_date,
            marked_by=request.user,
            attendance_records=records,
        )

        messages.success(request, f"Staff attendance recorded successfully for {count} staff member(s) on {target_date}.")
        return redirect(f"/staff/attendance/register/?date={target_date}")
