"""
Examinations URL routing.
"""
from django.urls import path
from examinations import views

app_name = "examinations"

urlpatterns = [
    # ── Score Entry (CA & Exam) ──────────────────────────────────────────────
    path("scores/", views.ScoreEntryView.as_view(), name="score_entry"),

    # ── Approvals & Publishing ───────────────────────────────────────────────
    path("approvals/", views.ResultApprovalView.as_view(), name="result_approval"),
    path("publish/", views.ResultPublicationView.as_view(), name="result_publish"),

    # ── Report Cards ─────────────────────────────────────────────────────────
    path("reports/<uuid:report_id>/", views.ReportCardDetailView.as_view(), name="report_card_detail"),
]
