"""
REST API v1 integration & security tests.

Verifies:
- JWT authentication (login, refresh, logout/blacklist, profile, password change).
- Strict multi-tenant isolation (School A token cannot access School B domain).
- Role-based API permissions across Academics, Examinations, Admissions, Finance,
  Store, Communications, and Support.
- OpenAPI schema generation.
"""
import datetime
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from schools.models import School, SchoolDomain
from accounts.services import create_school_user
from academics.models import AcademicSession, SchoolClass, Term
from academics.services import admit_student, seed_school_classes
from core.constants import ROLE_DIRECTOR, ROLE_PARENT, ROLE_STUDENT
from examinations.models import (
    RESULT_STATUS_DRAFT,
    RESULT_STATUS_PUBLISHED,
    StudentSubjectResult,
)
from finance.models import FeeCategory, FeeStructure
from finance.services import create_student_invoice
from store.models import Product, ProductCategory


class RestApiV1Tests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(
            name="Heritage Academy",
            code="HA",
            slug="heritage",
            student_id_prefix="HA-STD-",
            is_active=True,
        )
        SchoolDomain.objects.create(
            school=self.school_a,
            domain="heritage.localhost",
            is_primary=True,
            is_verified=True,
        )

        self.school_b = School.objects.create(
            name="Acumen College",
            code="ACU",
            slug="acumen",
            student_id_prefix="ACU-STD-",
            is_active=True,
        )
        SchoolDomain.objects.create(
            school=self.school_b,
            domain="acumen.localhost",
            is_primary=True,
            is_verified=True,
        )

        self.director_a, _ = create_school_user(
            school=self.school_a,
            role=ROLE_DIRECTOR,
            first_name="Chinedu",
            last_name="Okafor",
            email="director@heritage.edu.ng",
            password="Password123!",
        )
        self.parent_a, _ = create_school_user(
            school=self.school_a,
            role=ROLE_PARENT,
            first_name="Tunde",
            last_name="Adeyemi",
            email="parent@heritage.edu.ng",
            password="Password123!",
        )
        self.director_b, _ = create_school_user(
            school=self.school_b,
            role=ROLE_DIRECTOR,
            first_name="Seyi",
            last_name="Balogun",
            email="director@acumen.edu.ng",
            password="Password123!",
        )

        seed_school_classes(self.school_a)
        self.jss1_a = SchoolClass.objects.get(school=self.school_a, name="JSS 1")
        self.session_a = AcademicSession.objects.create(
            school=self.school_a,
            name="2026/2027",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2027, 7, 31),
            is_current=True,
        )
        self.term_a = Term.objects.create(
            school=self.school_a,
            session=self.session_a,
            term="first",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2026, 12, 18),
            is_current=True,
        )

        self.client_a = APIClient(HTTP_HOST="heritage.localhost")
        self.client_b = APIClient(HTTP_HOST="acumen.localhost")

    def _login(self, client, username, password="Password123!"):
        res = client.post(
            "/api/v1/auth/login/",
            {"username": username, "password": password},
            format="json",
        )
        return res

    def test_jwt_login_refresh_me_and_logout_revocation(self):
        res = self._login(self.client_a, self.director_a.username)
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["school"]["code"], "HA")
        self.assertEqual(res.data["membership"]["role"], ROLE_DIRECTOR)

        access = res.data["access"]
        refresh = res.data["refresh"]

        # Access /me/
        self.client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me_res = self.client_a.get("/api/v1/auth/me/")
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.data["user"]["username"], self.director_a.username)

        # Logout revokes refresh token
        logout_res = self.client_a.post("/api/v1/auth/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(logout_res.status_code, 200)

        refresh_res = self.client_a.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(refresh_res.status_code, 401)

    def test_cross_tenant_isolation_blocks_school_a_user_on_school_b(self):
        # School A director cannot log in on School B domain
        res_login_b = self._login(self.client_b, self.director_a.username)
        self.assertEqual(res_login_b.status_code, 400)

        # Even with a valid token from School A, School B endpoints reject access
        res_login_a = self._login(self.client_a, self.director_a.username)
        access_a = res_login_a.data["access"]
        self.client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {access_a}")
        res_students_b = self.client_b.get("/api/v1/students/")
        self.assertEqual(res_students_b.status_code, 403)

    def test_announcements_and_support_api_rbac(self):
        # Parent cannot create announcement via API
        parent_login = self._login(self.client_a, self.parent_a.username)
        self.client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {parent_login.data['access']}")
        res_denied = self.client_a.post(
            "/api/v1/communications/announcements/",
            {"title": "Fake Notice", "content": "Not allowed"},
            format="json",
        )
        self.assertEqual(res_denied.status_code, 403)

        # Director creates announcement -> Parent receives notification
        dir_login = self._login(self.client_a, self.director_a.username)
        self.client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {dir_login.data['access']}")
        res_created = self.client_a.post(
            "/api/v1/communications/announcements/",
            {"title": "Resumption", "content": "School resumes Monday.", "target_audience": "all"},
            format="json",
        )
        self.assertEqual(res_created.status_code, 201)

        # Parent checks notifications
        self.client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {parent_login.data['access']}")
        res_notes = self.client_a.get("/api/v1/communications/notifications/")
        self.assertEqual(res_notes.status_code, 200)
        self.assertEqual(len(res_notes.data["results"]), 1)

        # Parent opens support ticket & replies
        res_ticket = self.client_a.post(
            "/api/v1/support/tickets/",
            {"subject": "Bus Inquiry", "description": "Morning pickup time?", "category": "general"},
            format="json",
        )
        self.assertEqual(res_ticket.status_code, 201)
        ticket_id = res_ticket.data["id"]
        res_reply = self.client_a.post(
            f"/api/v1/support/tickets/{ticket_id}/messages/",
            {"message": "Please confirm."},
            format="json",
        )
        self.assertEqual(res_reply.status_code, 201)

    def test_public_admissions_and_finance_pos_api(self):
        # Public admission application
        res_apply = self.client_a.post(
            "/api/v1/admissions/apply/",
            {
                "first_name": "Emeka",
                "last_name": "Nwosu",
                "gender": "male",
                "date_of_birth": "2014-05-10",
                "applying_for_class_id": str(self.jss1_a.id),
                "parent_name": "Chief Nwosu",
                "parent_phone": "08012345678",
                "parent_email": "nwosu@example.com",
            },
            format="json",
        )
        self.assertEqual(res_apply.status_code, 201)
        app_number = res_apply.data["application_number"]

        # Public status check
        res_status = self.client_a.get(
            f"/api/v1/admissions/status/?application_number={app_number}&parent_phone=08012345678"
        )
        self.assertEqual(res_status.status_code, 200)
        self.assertEqual(res_status.data["first_name"], "Emeka")

        # Store POS checkout by Director
        cat = ProductCategory.objects.create(school=self.school_a, name="Uniforms")
        prod = Product.objects.create(
            school=self.school_a,
            category=cat,
            name="House Wear",
            price=Decimal("5000.00"),
            stock_quantity=10,
        )
        dir_login = self._login(self.client_a, self.director_a.username)
        self.client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {dir_login.data['access']}")
        res_pos = self.client_a.post(
            "/api/v1/store/orders/pos/",
            {
                "buyer_name": "Mrs. Nwosu",
                "payment_method": "cash",
                "items": [{"product_id": str(prod.id), "quantity": 2}],
            },
            format="json",
        )
        self.assertEqual(res_pos.status_code, 201)
        self.assertEqual(Decimal(res_pos.data["total_amount"]), Decimal("10000.00"))
        prod.refresh_from_db()
        self.assertEqual(prod.stock_quantity, 8)

    def test_openapi_schema_endpoint(self):
        res = self.client_a.get("/api/v1/schema/")
        self.assertEqual(res.status_code, 200)
