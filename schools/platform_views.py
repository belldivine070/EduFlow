"""
Platform Developer Dashboard views.

Dedicated administrative control plane for EduFlow SaaS platform developers.
Allows oversight of all schools, onboarding new institutions, monitoring usage metrics,
and direct tenant portal access.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.db.models import Count, Q
from schools.models import School, SchoolDomain
from schools.services import register_school_with_director
from accounts.models import SchoolMembership, User
from core.constants import (
    ROLE_STUDENT,
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
)

STAFF_ROLES = [
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
]


class PlatformRequiredMixin(UserPassesTestMixin):
    """Ensure only platform developers or superusers can access this view."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_platform_developer or user.is_superuser)

    def handle_no_permission(self):
        messages.error(self.request, "Access restricted to EduFlow platform administrators.")
        return redirect("accounts:login")


class PlatformDashboardView(PlatformRequiredMixin, TemplateView):
    """
    Main overview dashboard for platform developers.
    """

    template_name = "platform/dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        schools_qs = (
            School.objects
            .annotate(
                student_count=Count("memberships", filter=Q(memberships__role=ROLE_STUDENT, memberships__status="active")),
                staff_count=Count("memberships", filter=Q(memberships__role__in=STAFF_ROLES, memberships__status="active")),
            )
            .order_by("-created_at")
        )

        total_schools = School.objects.count()
        active_schools = School.objects.filter(is_active=True).count()
        total_students = SchoolMembership.objects.filter(role=ROLE_STUDENT, status="active").count()
        total_staff = SchoolMembership.objects.filter(role__in=STAFF_ROLES, status="active").count()

        ctx.update({
            "total_schools": total_schools,
            "active_schools": active_schools,
            "total_students": total_students,
            "total_staff": total_staff,
            "schools": schools_qs,
        })
        return ctx


class PlatformCreateSchoolView(PlatformRequiredMixin, View):
    """
    Onboard a brand new school and seed its director, classes, and initial configuration.
    """

    def post(self, request, *args, **kwargs):
        school_name = request.POST.get("school_name", "").strip()
        school_code = request.POST.get("school_code", "").strip().upper()
        primary_domain = request.POST.get("primary_domain", "").strip().lower()
        student_id_prefix = request.POST.get("student_id_prefix", "").strip().upper()
        motto = request.POST.get("motto", "").strip()

        director_first = request.POST.get("director_first_name", "").strip()
        director_last = request.POST.get("director_last_name", "").strip()
        director_email = request.POST.get("director_email", "").strip().lower()
        director_phone = request.POST.get("director_phone", "").strip()
        director_password = request.POST.get("director_password", "").strip()

        if not (school_name and school_code and primary_domain and director_first and director_last and director_email and director_password):
            messages.error(request, "Please fill in all required fields to onboard the school.")
            return redirect("platform:dashboard")

        # Check school code uniqueness
        if School.objects.filter(code=school_code).exists():
            messages.error(request, f"School code '{school_code}' is already registered.")
            return redirect("platform:dashboard")

        # Check domain uniqueness
        if SchoolDomain.objects.filter(domain=primary_domain).exists():
            messages.error(request, f"Domain '{primary_domain}' is already assigned to another school.")
            return redirect("platform:dashboard")

        try:
            school, domain, director, membership = register_school_with_director(
                school_name=school_name,
                school_code=school_code,
                primary_domain=primary_domain,
                student_id_prefix=student_id_prefix,
                motto=motto,
                director_first_name=director_first,
                director_last_name=director_last,
                director_email=director_email,
                director_phone=director_phone,
                director_password=director_password,
            )

            messages.success(
                request,
                f"School '{school.name}' ({school.code}) onboarded successfully! "
                f"Director created with Staff ID: {director.username}."
            )
        except Exception as e:
            messages.error(request, f"Error onboarding school: {str(e)}")

        return redirect("platform:dashboard")


class PlatformToggleSchoolStatusView(PlatformRequiredMixin, View):
    """
    Toggle a school's active status.
    """

    def post(self, request, school_id, *args, **kwargs):
        school = get_object_or_404(School, id=school_id)
        school.is_active = not school.is_active
        school.save(update_fields=["is_active", "updated_at"])

        status_text = "activated" if school.is_active else "deactivated"
        messages.success(request, f"School '{school.name}' has been {status_text}.")
        return redirect("platform:dashboard")


class PlatformSchoolEditView(PlatformRequiredMixin, View):
    """
    Platform developer view to inspect and edit full details of any school institution.
    Allows editing name, code, slug, motto, student ID prefix, active status,
    logo, primary domain, contact info, and assessment weights.
    """

    template_name = "platform/schools/edit.html"

    def get(self, request, school_id, *args, **kwargs):
        school = get_object_or_404(School, id=school_id)
        from schools.models import AppVariable, SchoolDomain

        variables = {
            v.var_name: v.var_value
            for v in AppVariable.objects.filter(school=school)
        }

        primary_domain = SchoolDomain.objects.filter(school=school, is_primary=True).first()
        all_domains = SchoolDomain.objects.filter(school=school).order_by("-is_primary", "domain")

        context = {
            "school": school,
            "primary_domain": primary_domain.domain if primary_domain else "",
            "all_domains": all_domains,
            "official_email": variables.get("OFFICIAL_EMAIL", ""),
            "official_phone": variables.get("OFFICIAL_PHONE", ""),
            "school_address": variables.get("SCHOOL_ADDRESS", ""),
            "contact_person": variables.get("CONTACT_PERSON", ""),
            "admission_email": variables.get("ADMISSION_EMAIL", ""),
            "tet_weight": variables.get("TET_WEIGHT", "30"),
            "exam_weight": variables.get("EXAM_WEIGHT", "70"),
        }
        return render(request, self.template_name, context)

    def post(self, request, school_id, *args, **kwargs):
        school = get_object_or_404(School, id=school_id)
        from schools.models import AppVariable, SchoolDomain
        from django.utils.text import slugify

        # 1. Read POST data
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip().upper()
        slug_raw = request.POST.get("slug", "").strip()
        motto = request.POST.get("motto", "").strip()
        student_id_prefix = request.POST.get("student_id_prefix", "").strip().upper()
        is_active = request.POST.get("is_active") == "on"
        primary_domain_str = request.POST.get("primary_domain", "").strip().lower()

        if not name or not code:
            messages.error(request, "School Name and School Code are mandatory.")
            return redirect("platform:edit_school", school_id=school.id)

        # Validate code uniqueness against other schools
        if School.objects.filter(code=code).exclude(id=school.id).exists():
            messages.error(request, f"School code '{code}' is already used by another school.")
            return redirect("platform:edit_school", school_id=school.id)

        # Validate slug
        slug = slugify(slug_raw) if slug_raw else slugify(name)
        if School.objects.filter(slug=slug).exclude(id=school.id).exists():
            messages.error(request, f"Slug '{slug}' is already in use by another school.")
            return redirect("platform:edit_school", school_id=school.id)

        # Update school model
        school.name = name
        school.code = code
        school.slug = slug
        school.motto = motto
        school.student_id_prefix = student_id_prefix or f"{code}-STD-"
        school.is_active = is_active

        if "logo" in request.FILES:
            school.logo = request.FILES["logo"]

        school.save()

        # 2. Update Primary Domain
        if primary_domain_str:
            existing_domain = SchoolDomain.objects.filter(domain=primary_domain_str).exclude(school=school).first()
            if existing_domain:
                messages.error(request, f"Domain '{primary_domain_str}' is already assigned to another school.")
                return redirect("platform:edit_school", school_id=school.id)

            # Reset old primaries for this school
            SchoolDomain.objects.filter(school=school, is_primary=True).update(is_primary=False)
            
            # Create or update domain
            domain_obj, _ = SchoolDomain.objects.update_or_create(
                school=school,
                domain=primary_domain_str,
                defaults={
                    "is_primary": True,
                    "is_verified": True,
                    "is_active": True,
                    "domain_type": SchoolDomain.DOMAIN_SUBDOMAIN if "." in primary_domain_str else SchoolDomain.DOMAIN_CUSTOM,
                },
            )

        # 3. Update AppVariables
        var_updates = {
            "OFFICIAL_EMAIL": request.POST.get("official_email", "").strip(),
            "OFFICIAL_PHONE": request.POST.get("official_phone", "").strip(),
            "SCHOOL_ADDRESS": request.POST.get("school_address", "").strip(),
            "CONTACT_PERSON": request.POST.get("contact_person", "").strip(),
            "ADMISSION_EMAIL": request.POST.get("admission_email", "").strip(),
        }

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
                    messages.warning(request, "Assessment weights must total 100%. Weights were not updated.")
            except ValueError:
                messages.warning(request, "Assessment weights must be integers.")

        for var_name, var_value in var_updates.items():
            AppVariable.objects.update_or_create(
                school=school,
                var_name=var_name,
                defaults={"var_value": var_value},
            )

        messages.success(request, f"Institution '{school.name}' has been successfully updated.")
        return redirect("platform:edit_school", school_id=school.id)
