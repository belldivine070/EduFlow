"""
Accounts URL routing.
"""
from django.urls import path
from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("schools/switch/<uuid:school_id>/", views.SwitchSchoolView.as_view(), name="switch_school"),
    path("", views.DashboardView.as_view(), name="home"),
]
