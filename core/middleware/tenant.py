"""
Tenant resolution middleware.

Reads the request hostname, finds the matching verified+active SchoolDomain,
and attaches the resolved School to request.school.

For platform-level requests (e.g. the admin panel, platform dashboard),
request.school is set to None and request.is_platform_request is True.

Security notes:
- Only verified and active domains are matched.
- The school is derived from the hostname, never from a client-supplied parameter.
- Requests for unknown or inactive domains receive a 404 response.
"""
import logging
import os
from django.http import Http404
from django.conf import settings

logger = logging.getLogger(__name__)

PLATFORM_DOMAIN = os.getenv("PLATFORM_DOMAIN", "localhost")
PLATFORM_DOMAIN_ALIASES = {d.strip() for d in os.getenv("PLATFORM_DOMAIN_ALIASES", "").split(",") if d.strip()}

# Hostnames that are always treated as platform-level (never resolved to a tenant).
_ALWAYS_PLATFORM = {"localhost", "127.0.0.1", "testserver"}


class SubdomainTenantMiddleware:
    """
    Attach request.school (School instance or None) to every request.

    request.school = None          → platform-level request
    request.school = <School>      → school-tenant request
    request.is_platform_request    → bool shortcut
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._resolve_tenant(request)
        response = self.get_response(request)
        return response

    def _resolve_tenant(self, request):
        hostname = self._get_hostname(request)

        # Platform-specific paths are always platform-level requests
        if request.path.startswith("/platform/") or request.path.startswith("/admin/"):
            request.school = None
            request.is_platform_request = True
            return

        # Check if the hostname is a platform host or development environment
        is_platform_host = (
            hostname in _ALWAYS_PLATFORM
            or hostname == PLATFORM_DOMAIN
            or hostname in PLATFORM_DOMAIN_ALIASES
        )

        if is_platform_host:
            # First check if user is authenticated and attached to a school
            user = getattr(request, "user", None)
            session = getattr(request, "session", None)

            # Platform developers without specific school view stay at platform level
            if user and user.is_authenticated and (user.is_platform_developer or user.is_superuser):
                active_school_id = session.get("active_school_id") if session else None
                if active_school_id:
                    from schools.models import School
                    school = School.objects.filter(id=active_school_id, is_active=True).first()
                    if school:
                        request.school = school
                        request.is_platform_request = False
                        return
                request.school = None
                request.is_platform_request = True
                return

            # School users (authenticated)
            if user and user.is_authenticated:
                active_school_id = session.get("active_school_id") if session else None
                from schools.models import School
                if active_school_id:
                    school = School.objects.filter(id=active_school_id).first()
                    if school:
                        request.school = school
                        request.is_platform_request = False
                        return

                # Auto-detect from user's primary membership
                from accounts.models import SchoolMembership
                membership = (
                    SchoolMembership.objects
                    .filter(user=user)
                    .select_related("school")
                    .first()
                )
                if membership:
                    request.school = membership.school
                    if session:
                        session["active_school_id"] = str(membership.school.id)
                    request.is_platform_request = False
                    return

            # Unauthenticated session with previously selected active school
            if session:
                active_school_id = session.get("active_school_id")
                if active_school_id:
                    from schools.models import School
                    school = School.objects.filter(id=active_school_id).first()
                    if school:
                        request.school = school
                        request.is_platform_request = False
                        return

            request.school = None
            request.is_platform_request = True
            return

        # Attempt to resolve a school tenant by domain.
        try:
            from schools.models import SchoolDomain
            try:
                domain_record = (
                    SchoolDomain.objects
                    .select_related("school")
                    .get(domain=hostname, is_verified=True, is_active=True)
                )
                school = domain_record.school
                request.school = school
                request.is_platform_request = False
                if getattr(request, "session", None):
                    request.session["active_school_id"] = str(school.id)
            except SchoolDomain.DoesNotExist:
                logger.warning("No verified active domain found for hostname: %s", hostname)
                raise Http404("School not found for this domain.")
        except (ImportError, Exception) as exc:
            # If models aren't ready yet or database table doesn't exist during initial migrations
            logger.debug("Tenant resolution skipped during bootstrap (%s); treating %s as platform request.", exc, hostname)
            request.school = None
            request.is_platform_request = True

    @staticmethod
    def _get_hostname(request) -> str:
        """
        Extract the bare hostname from the HTTP_HOST header.
        Strips port numbers and normalises to lowercase.
        """
        host = request.META.get("HTTP_HOST", "")
        # Strip port
        if ":" in host:
            host = host.rsplit(":", 1)[0]
        return host.strip().lower()
