"""
Schools URL routing.
"""
from django.urls import path
from schools import views

app_name = "schools"

urlpatterns = [
    path("school/", views.SchoolSettingsView.as_view(), name="school_settings"),
]
