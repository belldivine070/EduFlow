"""
Academics URL configuration.

All routes are prefixed with /academics/ from config/urls.py.
"""
from django.urls import path
from academics import views

app_name = "academics"

urlpatterns = [
    # ── Classes & Arms ──────────────────────────────────────────────────────
    path("classes/", views.ClassListView.as_view(), name="class_list"),
    path("classes/<uuid:class_id>/arms/create/", views.ClassArmCreateView.as_view(), name="arm_create"),
    path("arms/<uuid:arm_id>/toggle/", views.ClassArmToggleView.as_view(), name="arm_toggle"),

    # ── Academic Sessions ────────────────────────────────────────────────────
    path("sessions/", views.SessionListView.as_view(), name="session_list"),
    path("sessions/create/", views.SessionCreateView.as_view(), name="session_create"),
    path("sessions/<uuid:session_id>/set-current/", views.SessionSetCurrentView.as_view(), name="session_set_current"),

    # ── Terms ────────────────────────────────────────────────────────────────
    path("sessions/<uuid:session_id>/terms/create/", views.TermCreateView.as_view(), name="term_create"),
    path("terms/<uuid:term_id>/set-current/", views.TermSetCurrentView.as_view(), name="term_set_current"),

    # ── Students ─────────────────────────────────────────────────────────────
    path("students/", views.StudentListView.as_view(), name="student_list"),
    path("students/admit/", views.StudentCreateView.as_view(), name="student_create"),
    path("students/<uuid:student_id>/", views.StudentDetailView.as_view(), name="student_detail"),
    path("students/<uuid:student_id>/toggle-status/", views.StudentToggleStatusView.as_view(), name="student_toggle_status"),

    # ── Subjects ─────────────────────────────────────────────────────────────
    path("subjects/", views.SubjectListView.as_view(), name="subject_list"),
    path("subjects/create/", views.SubjectCreateView.as_view(), name="subject_create"),
    path("subjects/<uuid:subject_id>/toggle/", views.SubjectToggleStatusView.as_view(), name="subject_toggle"),

    # ── Teaching Assignments ─────────────────────────────────────────────────
    path("assignments/", views.TeachingAssignmentListView.as_view(), name="assignment_list"),
    path("assignments/create/", views.TeachingAssignmentCreateView.as_view(), name="assignment_create"),
    path("assignments/<uuid:assignment_id>/toggle/", views.TeachingAssignmentToggleView.as_view(), name="assignment_toggle"),
    path("assignments/<uuid:assignment_id>/delete/", views.TeachingAssignmentDeleteView.as_view(), name="assignment_delete"),

    # ── Attendance Management ────────────────────────────────────────────────
    path("attendance/register/", views.StudentAttendanceRegisterView.as_view(), name="attendance_register"),
]
