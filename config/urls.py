"""
Root URL configuration for EduFlow.

Hostname-based tenant resolution is handled by the SubdomainTenantMiddleware.
The same URL paths serve different schools because the middleware attaches
request.school before any view runs.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "EduFlow Administration"
admin.site.site_title = "EduFlow Admin"
admin.site.index_title = "Platform Management"

urlpatterns = [
    # Django admin — URL is configurable via DJANGO_ADMIN_URL env var
    path(settings.ADMIN_URL, admin.site.urls),

    # ── REST API v1 ─────────────────────────────────────────────────────────
    path("api/v1/", include("api.v1.urls", namespace="api_v1")),

    # ── Platform Developer Control Plane ────────────────────────────────────
    path("platform/", include("schools.platform_urls", namespace="platform")),

    # ── Accounts & Auth & Tenant Dashboard ──────────────────────────────────
    path("", include("accounts.urls", namespace="accounts")),
    path("academics/", include("academics.urls", namespace="academics")),
    path("staff/", include("staff.urls", namespace="staff")),
    path("assessments/", include("assessments.urls", namespace="assessments")),
    path("examinations/", include("examinations.urls", namespace="examinations")),
    path("admissions/", include("admissions.urls", namespace="admissions")),
    path("finance/", include("finance.urls", namespace="finance")),
    path("store/", include("store.urls", namespace="store")),
    path("communications/", include("communications.urls", namespace="communications")),
    path("support/", include("support.urls", namespace="support")),
    path("settings/", include("schools.urls", namespace="schools")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
