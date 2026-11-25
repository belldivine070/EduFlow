"""
Admissions URL configuration.
"""
from django.urls import path
from admissions import views

app_name = "admissions"

urlpatterns = [
    # Public views
    path("apply/", views.PublicApplyView.as_view(), name="apply"),
    path("apply/success/", views.ApplySuccessView.as_view(), name="apply_success"),
    path("status/", views.ApplicationStatusLookupView.as_view(), name="status"),
    path("letter/<uuid:pk>/", views.AdmissionLetterView.as_view(), name="letter"),

    # School Staff views
    path("applications/", views.AdmissionApplicationListView.as_view(), name="admin_list"),
    path("applications/<uuid:pk>/", views.AdmissionApplicationDetailView.as_view(), name="admin_detail"),
    path("applications/<uuid:pk>/decision/", views.AdmissionApplicationDecisionView.as_view(), name="admin_decision"),
    path("applications/<uuid:pk>/convert/", views.AdmissionApplicationConvertView.as_view(), name="admin_convert"),
]
