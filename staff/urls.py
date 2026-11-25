"""
Staff URL routing.
"""
from django.urls import path
from staff import views

app_name = "staff"

urlpatterns = [
    path("", views.StaffListView.as_view(), name="staff_list"),
    path("onboard/", views.StaffCreateView.as_view(), name="staff_create"),
    path("attendance/register/", views.StaffAttendanceRegisterView.as_view(), name="attendance_register"),
    path("<uuid:membership_id>/", views.StaffDetailView.as_view(), name="staff_detail"),
    path("<uuid:membership_id>/toggle-status/", views.StaffStatusToggleView.as_view(), name="staff_toggle_status"),
]
