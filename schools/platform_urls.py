"""
Platform Developer URL routing.
"""
from django.urls import path
from schools import platform_views

app_name = "platform"

urlpatterns = [
    path("dashboard/", platform_views.PlatformDashboardView.as_view(), name="dashboard"),
    path("schools/create/", platform_views.PlatformCreateSchoolView.as_view(), name="create_school"),
    path("schools/<uuid:school_id>/edit/", platform_views.PlatformSchoolEditView.as_view(), name="edit_school"),
    path("schools/<uuid:school_id>/toggle-status/", platform_views.PlatformToggleSchoolStatusView.as_view(), name="toggle_school_status"),
]
