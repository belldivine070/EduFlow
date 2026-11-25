"""
Template context processors.

These inject school branding, navigation context, and platform settings
into every template render automatically.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def app_settings_processor(request):
    """Inject platform-level settings into every template."""
    return {
        "PLATFORM_NAME": getattr(settings, "PLATFORM_NAME", "EduFlow"),
        "DEBUG": settings.DEBUG,
    }


def school(request):
    """
    Inject the current tenant school, template directory, and static asset paths.

    request.school is set by SubdomainTenantMiddleware.
    If a custom template directory exists for school.slug, it is selected;
    otherwise the default school theme ('default') is used.
    """
    current_school = getattr(request, "school", None)
    is_platform = getattr(request, "is_platform_request", True)

    school_theme = "default"
    school_static_dir = "schools/default"

    if current_school and getattr(current_school, "slug", None):
        slug = current_school.slug

        # 1. Check template directory
        custom_template_dir = settings.BASE_DIR / "templates" / "schools" / slug
        if custom_template_dir.exists():
            school_theme = slug

        # 2. Check static directory
        custom_static_dir = settings.BASE_DIR / "static" / "schools" / slug
        if custom_static_dir.exists():
            school_static_dir = f"schools/{slug}"
        elif school_theme != "default":
            school_static_dir = f"schools/{school_theme}"

    # Determine base and layout templates
    base_tpl = f"schools/{school_theme}/base.html"
    if not (settings.BASE_DIR / "templates" / base_tpl).exists():
        base_tpl = "schools/default/base.html"

    layout_tpl = f"schools/{school_theme}/layout.html"
    if not (settings.BASE_DIR / "templates" / layout_tpl).exists():
        layout_tpl = "schools/default/layout.html"

    # Static assets: use school static dir if file exists, else default
    tailwind_js = f"{school_static_dir}/js/tailwind.config.js"
    if not (settings.BASE_DIR / "static" / tailwind_js).exists():
        tailwind_js = "schools/default/js/tailwind.config.js"

    theme_css = f"{school_static_dir}/css/theme.css"
    if not (settings.BASE_DIR / "static" / theme_css).exists():
        theme_css = "schools/default/css/theme.css"

    main_js = f"{school_static_dir}/js/main.js"
    if not (settings.BASE_DIR / "static" / main_js).exists():
        main_js = "schools/default/js/main.js"

    # Resolve role-based navigation flags for the authenticated user in current_school
    user_role = None
    user_role_display = None
    nav_is_admin = False
    nav_is_teaching_staff = False
    nav_is_staff = False
    nav_is_parent = False
    nav_is_student = False

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        if user.is_superuser or getattr(user, "is_platform_developer", False):
            nav_is_admin = True
            nav_is_teaching_staff = True
            nav_is_staff = True
            user_role = "platform_dev"
            user_role_display = "Platform Dev"
        elif current_school:
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
            membership = user.memberships.filter(
                school=current_school,
                status=MEMBERSHIP_ACTIVE,
            ).first()
            if membership:
                user_role = membership.role
                user_role_display = membership.get_role_display()
                nav_is_admin = membership.role in {ROLE_DIRECTOR, ROLE_PRINCIPAL, ROLE_VICE_PRINCIPAL}
                nav_is_teaching_staff = nav_is_admin or membership.role == ROLE_TEACHING_STAFF
                nav_is_staff = nav_is_teaching_staff or membership.role == ROLE_NON_TEACHING_STAFF
                nav_is_parent = membership.role == ROLE_PARENT
                nav_is_student = membership.role == ROLE_STUDENT

    return {
        "current_school": current_school,
        "is_platform_request": is_platform,
        "school_theme": school_theme,
        "school_static_dir": school_static_dir,
        "school_template_dir": f"schools/{school_theme}",
        "school_base_template": base_tpl,
        "school_layout_template": layout_tpl,
        "school_tailwind_config_js": tailwind_js,
        "school_theme_css": theme_css,
        "school_main_js": main_js,
        "user_role": user_role,
        "user_role_display": user_role_display,
        "nav_is_admin": nav_is_admin,
        "nav_is_teaching_staff": nav_is_teaching_staff,
        "nav_is_staff": nav_is_staff,
        "nav_is_parent": nav_is_parent,
        "nav_is_student": nav_is_student,
    }


def academics_context(request):
    """
    Inject the current academic session and term into every template.

    Reads the school from request.school (set by tenant middleware).
    If no school is active (e.g. platform-level requests), returns empty dict.
    """
    school_obj = getattr(request, "school", None)
    if not school_obj:
        return {}

    # Lazy import to avoid circular dependencies
    from academics.models import AcademicSession, Term  # noqa: PLC0415

    current_session = AcademicSession.objects.filter(school=school_obj, is_current=True).first()
    current_term = Term.objects.filter(school=school_obj, is_current=True).first()

    return {
        "current_session": current_session,
        "current_term": current_term,
    }


def staff_navigation(request):
    """
    Inject staff navigation context.

    Returns an empty dict when the user is not authenticated or has no
    school membership. The actual navigation items will be built in Phase 5
    once the SchoolMembership model exists.
    """
    if not request.user.is_authenticated:
        return {"staff_nav_items": []}
    return {"staff_nav_items": []}
