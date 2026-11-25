"""
Tests for accounts application:
- Custom User model
- Staff unique numeric ID generation
- Student prefix ID generation
- Multi-identifier authentication (Username / Staff ID / Student ID / Email / Phone)
- Tenant auto-detection and role-based login redirection
- Multi-school membership and school switcher
"""
from django.test import TestCase
from accounts.models import User, SchoolMembership
from schools.models import School, SchoolDomain
from accounts.services import (
    generate_staff_id,
    generate_student_id,
    create_school_user,
    validate_username_format,
)
from core.exceptions import InvalidUsernameFormatError
from core.constants import ROLE_TEACHING_STAFF, ROLE_STUDENT, ROLE_DIRECTOR


class UserModelTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(
            name="Green School",
            code="GS",
            slug="green-school",
            student_id_prefix="GS/2026/",
        )
        self.school_b = School.objects.create(
            name="Blue School",
            code="BS",
            slug="blue-school",
            student_id_prefix="BS-STD-",
        )

    def test_create_user(self):
        user = User.objects.create_user(
            username="849201",
            first_name="Amina",
            last_name="Bello",
            email="amina@greenschool.ng",
            password="SecurePassword123!",
        )
        self.assertEqual(user.username, "849201")
        self.assertTrue(user.check_password("SecurePassword123!"))
        self.assertEqual(user.get_full_name(), "Amina Bello")

    def test_generate_staff_id_unique_random_number(self):
        """Staff ID must be a unique numeric string."""
        s1 = generate_staff_id()
        self.assertTrue(s1.isdigit())
        self.assertGreaterEqual(len(s1), 6)

        User.objects.create_user(username=s1, first_name="Staff", last_name="One")
        s2 = generate_staff_id()
        self.assertNotEqual(s1, s2)
        self.assertTrue(s2.isdigit())

    def test_generate_student_id_with_school_prefix(self):
        """Student ID must use the school's configured prefix and sequence number."""
        sid1 = generate_student_id(self.school_a)
        self.assertEqual(sid1, "GS/2026/0001")

        User.objects.create_user(username=sid1, first_name="Student", last_name="One")
        sid2 = generate_student_id(self.school_a)
        self.assertEqual(sid2, "GS/2026/0002")

        # Different school with different prefix
        sid_b = generate_student_id(self.school_b)
        self.assertEqual(sid_b, "BS-STD-0001")

    def test_create_school_user_staff_vs_student(self):
        # Staff user gets random numeric ID
        staff_user, staff_mem = create_school_user(
            school=self.school_a,
            role=ROLE_TEACHING_STAFF,
            first_name="John",
            last_name="Doe",
            password="Password123!",
        )
        self.assertTrue(staff_user.username.isdigit())
        self.assertEqual(staff_mem.role, ROLE_TEACHING_STAFF)

        # Student user gets prefix ID
        student_user, student_mem = create_school_user(
            school=self.school_a,
            role=ROLE_STUDENT,
            first_name="Jane",
            last_name="Doe",
            password="Password123!",
        )
        self.assertTrue(student_user.username.startswith("GS/2026/"))
        self.assertEqual(student_mem.role, ROLE_STUDENT)

    def test_username_format_validation(self):
        validate_username_format("849201")
        validate_username_format("GS/2026/0001")
        validate_username_format("BS-STD-0001")
        validate_username_format("platform_admin")

        with self.assertRaises(InvalidUsernameFormatError):
            validate_username_format("invalid username with spaces")

    def test_multi_school_membership(self):
        """
        Verify that a single user can belong to two schools independently.
        """
        user = User.objects.create_user(
            username="749201",
            first_name="Emeka",
            last_name="Okonkwo",
            email="emeka@education.ng",
        )

        m1 = SchoolMembership.objects.create(
            user=user,
            school=self.school_a,
            role=ROLE_TEACHING_STAFF,
            id_number="749201",
        )

        m2 = SchoolMembership.objects.create(
            user=user,
            school=self.school_b,
            role=ROLE_TEACHING_STAFF,
            id_number="749201",
        )

        self.assertEqual(user.memberships.count(), 2)
        self.assertEqual(m1.school.code, "GS")
        self.assertEqual(m2.school.code, "BS")


class AuthViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Green School",
            code="GS",
            slug="green-school",
            student_id_prefix="GS/2026/",
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="green.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        # Staff user
        self.staff_user = User.objects.create_user(
            username="884920",
            first_name="Amina",
            last_name="Bello",
            email="amina@greenschool.ng",
            phone_number="08031234567",
            password="SecurePassword123!",
        )
        self.staff_membership = SchoolMembership.objects.create(
            user=self.staff_user,
            school=self.school,
            role=ROLE_DIRECTOR,
            id_number="884920",
        )

        # Platform developer user
        self.platform_dev = User.objects.create_user(
            username="dev_admin",
            first_name="Dev",
            last_name="Platform",
            email="admin@eduflow.ng",
            is_platform_developer=True,
            password="DevPassword123!",
        )

    def test_login_page_renders_cleanly_without_role_selector(self):
        response = self.client.get("/login/", HTTP_HOST="green.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email, Mobile Number or Username")
        # Ensure role selector tabs are NOT present
        self.assertNotContains(response, "SIGN IN AS")
        self.assertContains(response, "Stay signed in")

    def test_successful_login_with_numeric_staff_id(self):
        response = self.client.post("/login/", {
            "identifier": "884920",
            "password": "SecurePassword123!",
            "remember_me": True,
        }, HTTP_HOST="green.localhost", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)

    def test_successful_login_with_email(self):
        response = self.client.post("/login/", {
            "identifier": "amina@greenschool.ng",
            "password": "SecurePassword123!",
            "remember_me": True,
        }, HTTP_HOST="green.localhost", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)

    def test_successful_login_with_phone_number_formats(self):
        # 1. Login with local 080... format
        response = self.client.post("/login/", {
            "identifier": "08031234567",
            "password": "SecurePassword123!",
        }, HTTP_HOST="green.localhost", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)
        self.client.logout()

        # 2. Login with international +234 format
        response2 = self.client.post("/login/", {
            "identifier": "+2348031234567",
            "password": "SecurePassword123!",
        }, HTTP_HOST="green.localhost", follow=True)
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(response2.context["user"].is_authenticated)

    def test_platform_developer_redirected_to_platform_dashboard(self):
        response = self.client.post("/login/", {
            "identifier": "dev_admin",
            "password": "DevPassword123!",
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/platform/dashboard/", response.url)

    def test_invalid_login_shows_error(self):
        response = self.client.post("/login/", {
            "identifier": "884920",
            "password": "WrongPassword!",
        }, HTTP_HOST="green.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid credentials")

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/", HTTP_HOST="green.localhost")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_authenticated_user_accesses_dashboard(self):
        self.client.force_login(self.staff_user)
        # On local or domain
        session = self.client.session
        session["active_school_id"] = str(self.school.id)
        session.save()

        response = self.client.get("/dashboard/", HTTP_HOST="green.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Good day, Amina!")
        self.assertContains(response, "Quick Operations")
