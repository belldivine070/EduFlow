"""
Assessments URL routing.
"""
from django.urls import path
from assessments import views

app_name = "assessments"

urlpatterns = [
    # ── Continuous Assessments / Tests ──────────────────────────────────────
    path("", views.AssessmentListView.as_view(), name="assessment_list"),
    path("create/", views.AssessmentCreateView.as_view(), name="assessment_create"),
    path("<uuid:assessment_id>/", views.AssessmentDetailView.as_view(), name="assessment_detail"),
    path("<uuid:assessment_id>/take/", views.AssessmentTakeView.as_view(), name="assessment_take"),
    path("submissions/<uuid:submission_id>/mark/", views.AssessmentMarkingQueueView.as_view(), name="marking_queue"),

    # ── Question Bank ────────────────────────────────────────────────────────
    path("questions/", views.QuestionBankListView.as_view(), name="question_list"),
    path("questions/create/", views.QuestionCreateView.as_view(), name="question_create"),
]
