"""
Multi-tenant API permissions.

Enforces:
- Active school tenant derived strictly from request hostname (never client-supplied school_id).
- Active SchoolMembership in that tenant.
- Role-based access control (Director, Principal, Staff, Parent, Student).
"""
from rest_framework import permissions
from accounts.models import SchoolMembership
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

ADMIN_ROLES = {ROLE_DIRECTOR, ROLE_PRINCIPAL, ROLE_VICE_PRINCIPAL}
TEACHING_ROLES = {ROLE_DIRECTOR, ROLE_PRINCIPAL, ROLE_VICE_PRINCIPAL, ROLE_TEACHING_STAFF}
STAFF_ROLES = TEACHING_ROLES | {ROLE_NON_TEACHING_STAFF}


def get_active_membership(request):
    """
    Resolve and cache active SchoolMembership for (request.school, request.user).
    """
    school = getattr(request, "school", None)
    if not school or not request.user or not request.user.is_authenticated:
        return None
    cached = getattr(request, "_cached_api_membership", None)
    if cached is not None:
        return cached
    membership = SchoolMembership.objects.filter(
        school=school,
        user=request.user,
        status=MEMBERSHIP_ACTIVE,
    ).first()
    request._cached_api_membership = membership
    return membership


class IsActiveTenant(permissions.BasePermission):
    """
    Allows public access only when request resolves to an active school tenant.
    """
    message = "A valid active school domain is required."

    def has_permission(self, request, view):
        school = getattr(request, "school", None)
        return bool(school and school.is_active)


class IsTenantMember(permissions.BasePermission):
    """
    Requires authenticated user with an active membership in request.school.
    """
    message = "Active school membership is required for this resource."

    def has_permission(self, request, view):
        school = getattr(request, "school", None)
        if not school or not school.is_active:
            return False
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return get_active_membership(request) is not None


class IsTenantAdmin(IsTenantMember):
    """
    Requires Director, Principal, or Vice Principal role in request.school.
    """
    message = "School administrator privileges required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.user.is_superuser:
            return True
        membership = get_active_membership(request)
        return bool(membership and membership.role in ADMIN_ROLES)


class IsTenantTeachingStaff(IsTenantMember):
    """
    Requires Teaching Staff or Admin role in request.school.
    """
    message = "Teaching staff or administrator privileges required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.user.is_superuser:
            return True
        membership = get_active_membership(request)
        return bool(membership and membership.role in TEACHING_ROLES)


class IsTenantStaff(IsTenantMember):
    """
    Requires any Staff role in request.school.
    """
    message = "School staff privileges required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.user.is_superuser:
            return True
        membership = get_active_membership(request)
        return bool(membership and membership.role in STAFF_ROLES)
