"""
REST API v1 URL Configuration (/api/v1/).
"""
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from api.v1.auth_views import (
    ChangePasswordAPIView,
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    RefreshAPIView,
)
from api.v1.schools_academics_views import (
    AcademicSessionViewSet,
    CurrentSchoolAPIView,
    SchoolClassViewSet,
    StudentAttendanceAPIView,
    StudentProfileViewSet,
    SubjectViewSet,
    TermViewSet,
)
from api.v1.assessments_exams_views import (
    AssessmentViewSet,
    ExamResultListAPIView,
    ReportCardListAPIView,
)
from api.v1.admissions_finance_store_views import (
    AdmissionApplicationViewSet,
    FeeStructureViewSet,
    ProductViewSet,
    PublicAdmissionApplyAPIView,
    PublicAdmissionStatusAPIView,
    StoreOrderViewSet,
    StudentInvoiceViewSet,
)
from api.v1.communications_support_views import (
    AnnouncementViewSet,
    NotificationViewSet,
    SupportTicketViewSet,
)

app_name = "api_v1"

router = DefaultRouter()
router.register(r"academics/sessions", AcademicSessionViewSet, basename="academic-sessions")
router.register(r"academics/terms", TermViewSet, basename="academic-terms")
router.register(r"academics/classes", SchoolClassViewSet, basename="academic-classes")
router.register(r"academics/subjects", SubjectViewSet, basename="academic-subjects")
router.register(r"students", StudentProfileViewSet, basename="students")
router.register(r"assessments", AssessmentViewSet, basename="assessments")
router.register(r"admissions/applications", AdmissionApplicationViewSet, basename="admission-applications")
router.register(r"finance/fee-structures", FeeStructureViewSet, basename="fee-structures")
router.register(r"finance/invoices", StudentInvoiceViewSet, basename="student-invoices")
router.register(r"store/products", ProductViewSet, basename="store-products")
router.register(r"store/orders", StoreOrderViewSet, basename="store-orders")
router.register(r"communications/announcements", AnnouncementViewSet, basename="announcements")
router.register(r"communications/notifications", NotificationViewSet, basename="notifications")
router.register(r"support/tickets", SupportTicketViewSet, basename="support-tickets")

urlpatterns = [
    # OpenAPI / Swagger Documentation
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_v1:schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="api_v1:schema"), name="redoc"),

    # Authentication & Profile
    path("auth/login/", LoginAPIView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshAPIView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutAPIView.as_view(), name="auth-logout"),
    path("auth/me/", MeAPIView.as_view(), name="auth-me"),
    path("auth/change-password/", ChangePasswordAPIView.as_view(), name="auth-change-password"),

    # School Info
    path("schools/current/", CurrentSchoolAPIView.as_view(), name="schools-current"),

    # Attendance
    path("attendance/students/", StudentAttendanceAPIView.as_view(), name="attendance-students"),

    # Examinations & Results
    path("examinations/results/", ExamResultListAPIView.as_view(), name="exam-results"),
    path("examinations/report-cards/", ReportCardListAPIView.as_view(), name="exam-report-cards"),

    # Public Admissions
    path("admissions/apply/", PublicAdmissionApplyAPIView.as_view(), name="admissions-public-apply"),
    path("admissions/status/", PublicAdmissionStatusAPIView.as_view(), name="admissions-public-status"),

    # Router ViewSets
    path("", include(router.urls)),
]
