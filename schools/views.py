"""
Schools views.

Includes:
- SchoolSettingsView: allows school leadership (Director, Principal, or Platform Dev)
  to configure school details, contact info, student ID prefix, branding colors,
  and academic grading/assessment weights.
"""
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from schools.models import School, AppVariable
from schools.services import resolve_school_template
from core.constants import ROLE_DIRECTOR, ROLE_PRINCIPAL


class SchoolSettingsView(LoginRequiredMixin, View):
    """
    School administration settings.
    Allows Directors, Principals, and Platform Developers to customize school profile,
    contact info, student ID prefix, theme colors, and assessment weights.
    """

    def get_school_and_check_permission(self, request):
        school = getattr(request, "school", None)
        if not school:
            return None, False

        # Allow platform developers or superusers
        if getattr(request.user, "is_platform_developer", False) or request.user.is_superuser:
            return school, True

        membership = request.user.memberships.filter(
            school=school,
            role__in=[ROLE_DIRECTOR, ROLE_PRINCIPAL],
            status="active",
        ).first()

        if membership:
            return school, True

        return school, False

    def get(self, request):
        school, allowed = self.get_school_and_check_permission(request)
        if not school:
            messages.warning(request, "Please access school settings via your school portal.")
            return redirect("accounts:dashboard")
        if not allowed:
            messages.error(request, "You do not have permission to access school settings.")
            return redirect("accounts:dashboard")

        # Load all AppVariables for this school
        variables = {
            v.var_name: v.var_value
            for v in AppVariable.objects.filter(school=school)
        }

        context = {
            "current_school": school,
            "school_motto": school.motto,
            "student_id_prefix": school.student_id_prefix,
            "official_email": variables.get("OFFICIAL_EMAIL", ""),
            "official_phone": variables.get("OFFICIAL_PHONE", ""),
            "school_address": variables.get("SCHOOL_ADDRESS", ""),
            "contact_person": variables.get("CONTACT_PERSON", ""),
            "admission_email": variables.get("ADMISSION_EMAIL", ""),
            "tet_weight": variables.get("TET_WEIGHT", "30"),
            "exam_weight": variables.get("EXAM_WEIGHT", "70"),
        }

        template = resolve_school_template(school, "settings/school.html")
        return render(request, template, context)

    def post(self, request):
        school, allowed = self.get_school_and_check_permission(request)
        if not school or not allowed:
            messages.error(request, "Unauthorized access.")
            return redirect("accounts:dashboard")

        # 1. Update School model fields
        motto = request.POST.get("motto", "").strip()
        student_id_prefix = request.POST.get("student_id_prefix", "").strip().upper()

        school.motto = motto
        if student_id_prefix:
            school.student_id_prefix = student_id_prefix

        # Handle logo upload if provided
        if "logo" in request.FILES:
            school.logo = request.FILES["logo"]

        school.save()

        # 2. Update AppVariables (academic and contact settings)
        var_updates = {
            "OFFICIAL_EMAIL": request.POST.get("official_email", "").strip(),
            "OFFICIAL_PHONE": request.POST.get("official_phone", "").strip(),
            "SCHOOL_ADDRESS": request.POST.get("school_address", "").strip(),
            "CONTACT_PERSON": request.POST.get("contact_person", "").strip(),
            "ADMISSION_EMAIL": request.POST.get("admission_email", "").strip(),
        }

        # Validate assessment weights
        tet_weight_raw = request.POST.get("tet_weight", "").strip()
        exam_weight_raw = request.POST.get("exam_weight", "").strip()
        if tet_weight_raw and exam_weight_raw:
            try:
                tet_val = int(tet_weight_raw)
                exam_val = int(exam_weight_raw)
                if tet_val + exam_val == 100 and tet_val >= 0 and exam_val >= 0:
                    var_updates["TET_WEIGHT"] = str(tet_val)
                    var_updates["EXAM_WEIGHT"] = str(exam_val)
                else:
                    messages.warning(request, "TET and Exam weights must total 100%. Weights were not updated.")
            except ValueError:
                messages.warning(request, "Assessment weights must be valid numbers.")

        for name, val in var_updates.items():
            AppVariable.objects.update_or_create(
                school=school,
                var_name=name,
                defaults={"var_value": val},
            )

        messages.success(request, "School settings have been updated successfully.")
        return redirect("schools:school_settings")
