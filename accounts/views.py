"""
Accounts and authentication views.
"""
from django.shortcuts import render, redirect
from django.views.generic import FormView, View, TemplateView
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from accounts.forms import LoginForm
from accounts.models import SchoolMembership
from academics.models import SchoolClass


class UserLoginView(FormView):
    """
    Unified multi-identifier login view.
    Accepts staff random ID, student ID with prefix, username, email, or phone number.
    Automatically detects user role & school tenant, routing to the appropriate dashboard.
    """

    form_class = LoginForm

    def get_template_names(self):
        from schools.services import resolve_school_template
        school = getattr(self.request, "school", None)
        return [resolve_school_template(school, "accounts/login.html")]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_success_url(self):
        user = self.request.user

        # 1. Platform Developer / Superuser -> Platform Dashboard
        if user.is_platform_developer or user.is_superuser:
            return reverse_lazy("platform:dashboard")

        # 2. School tenant user -> detect school and set active session
        memberships = (
            SchoolMembership.objects
            .filter(user=user, status="active", school__is_active=True)
            .select_related("school")
        )

        active_school = None
        current_school = getattr(self.request, "school", None)

        if current_school and memberships.filter(school=current_school).exists():
            active_school = current_school
        elif memberships.exists():
            active_school = memberships.first().school

        if active_school:
            self.request.session["active_school_id"] = str(active_school.id)
            messages.success(
                self.request,
                f"Welcome back, {user.first_name}! Signed in to {active_school.name}."
            )
        else:
            messages.info(self.request, f"Welcome back, {user.first_name}!")

        # Support safe 'next' parameter
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return next_url

        return reverse_lazy("accounts:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_platform_developer or request.user.is_superuser:
                return redirect("platform:dashboard")
            # If school user's school is deactivated, log out immediately
            school = getattr(request, "school", None)
            if school and not school.is_active:
                logout(request)
                messages.error(
                    request,
                    "This school portal has been deactivated. Please contact support or your school administrator."
                )
                return super().dispatch(request, *args, **kwargs)
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)

        # Handle "remember me"
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)  # Browser session close

        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = getattr(self.request, "school", None)
        ctx["current_school"] = school
        ctx["school_code"] = school.code if school else "GS"
        ctx["school_is_deactivated"] = bool(school and not school.is_active)
        return ctx


class SwitchSchoolView(LoginRequiredMixin, View):
    """
    Switch active school context for multi-school staff/students or platform developers.
    """

    def post(self, request, school_id, *args, **kwargs):
        from schools.models import School
        user = request.user

        if user.is_platform_developer or user.is_superuser:
            school = School.objects.filter(id=school_id).first()
        else:
            membership = (
                SchoolMembership.objects
                .filter(user=user, school_id=school_id, status="active")
                .select_related("school")
                .first()
            )
            school = membership.school if membership else None

        if school and (school.is_active or user.is_platform_developer or user.is_superuser):
            request.session["active_school_id"] = str(school.id)
            messages.success(request, f"Switched to {school.name}.")
        elif school and not school.is_active:
            messages.error(request, "This school portal has been deactivated. Please contact support or your school administrator.")
        else:
            messages.error(request, "Selected school is not accessible.")

        redirect_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/dashboard/"
        return redirect(redirect_url)

    def get(self, request, school_id, *args, **kwargs):
        return self.post(request, school_id, *args, **kwargs)


class UserLogoutView(View):
    """Sign the user out and redirect to login."""

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been successfully signed out.")
        return redirect("accounts:login")

    def get(self, request, *args, **kwargs):
        # Support GET logout with safe fallback
        return self.post(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main responsive dashboard.
    Tailors statistics and view cards to the user's role and tenant context.
    """

    login_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(self.login_url)
        if request.user.is_platform_developer or request.user.is_superuser:
            return redirect("platform:dashboard")

        school = getattr(request, "school", None)
        if school and not school.is_active:
            logout(request)
            messages.error(
                request,
                "This school portal has been deactivated. Please contact support or your school administrator."
            )
            return redirect("accounts:login")

        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        from schools.services import resolve_school_template
        school = getattr(self.request, "school", None)
        return [resolve_school_template(school, "dashboard/index.html")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        school = getattr(self.request, "school", None)

        # Find user's active membership in current school
        membership = None
        if school:
            membership = SchoolMembership.objects.filter(user=user, school=school).first()

        # Multi-school switcher data
        all_memberships = SchoolMembership.objects.filter(user=user).select_related("school")

        ctx.update({
            "current_school": school,
            "membership": membership,
            "user_role": membership.role.upper() if membership else ("PLATFORM ADMIN" if user.is_platform_developer else "USER"),
            "user_memberships": all_memberships,
            "user_schools": [m.school for m in all_memberships],
            # Core tenant stats
            "total_classes": SchoolClass.objects.filter(school=school, is_active=True).count() if school else 0,
            "total_staff": SchoolMembership.objects.filter(school=school, role__in=["director", "principal", "vice_principal", "teaching_staff", "non_teaching_staff"]).count() if school else 0,
            "total_students": SchoolMembership.objects.filter(school=school, role="student").count() if school else 0,
        })
        return ctx
