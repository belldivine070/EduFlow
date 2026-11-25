"""
Tests for schools application:
- Atomic school onboarding with Director and seeded classes
- Domain verification and uniqueness
- AppVariable configuration and fallback resolution
- Platform developer control plane views
"""
from django.test import TestCase
from schools.models import School, SchoolDomain, AppVariable, get_setting
from schools.services import register_school_with_director
from academics.models import SchoolClass
from accounts.models import User, SchoolMembership


class SchoolRegistrationTests(TestCase):
    def test_register_school_with_director(self):
        school, domain, director, membership = register_school_with_director(
            school_name="Crown Heights Academy",
            school_code="CHA",
            primary_domain="crown.eduflow.ng",
            student_id_prefix="CHA/2026/",
            director_first_name="Babajide",
            director_last_name="Sanwo",
            director_email="director@crownheights.ng",
            director_password="StrongPassword123!",
            motto="Excellence in Leadership",
        )

        # 1. School created
        self.assertEqual(school.code, "CHA")
        self.assertEqual(school.slug, "crown-heights-academy")
        self.assertEqual(school.student_id_prefix, "CHA/2026/")
        self.assertTrue(school.is_active)

        # 2. Domain created and verified
        self.assertEqual(domain.domain, "crown.eduflow.ng")
        self.assertTrue(domain.is_primary)
        self.assertTrue(domain.is_verified)

        # 3. Director created with unique numeric Staff ID
        self.assertTrue(director.username.isdigit())
        self.assertEqual(director.email, "director@crownheights.ng")
        self.assertTrue(director.check_password("StrongPassword123!"))

        # 4. Membership linked
        self.assertEqual(membership.user, director)
        self.assertEqual(membership.school, school)
        self.assertEqual(membership.role, "director")
        self.assertTrue(membership.is_active)

        # 5. All 12 classes seeded
        self.assertEqual(SchoolClass.objects.filter(school=school).count(), 12)

        # 6. Default AppVariables created
        self.assertEqual(get_setting("SCHOOL_NAME", school=school), "Crown Heights Academy")
        self.assertEqual(get_setting("TET_WEIGHT", school=school), "30")
        self.assertEqual(get_setting("EXAM_WEIGHT", school=school), "70")

    def test_appvariable_platform_fallback(self):
        school = School.objects.create(name="Apex College", code="AC", slug="apex-college")

        # Set a platform-wide setting (school=None)
        AppVariable.objects.create(school=None, var_name="PLATFORM_NAME", var_value="EduFlow SaaS")

        # School query without local override falls back to platform
        self.assertEqual(get_setting("PLATFORM_NAME", school=school), "EduFlow SaaS")

        # Setting local override
        AppVariable.objects.create(school=school, var_name="PLATFORM_NAME", var_value="Apex EduFlow")
        self.assertEqual(get_setting("PLATFORM_NAME", school=school), "Apex EduFlow")


class PlatformDashboardTests(TestCase):
    def setUp(self):
        self.platform_dev = User.objects.create_user(
            username="super_dev",
            first_name="Platform",
            last_name="Architect",
            email="dev@eduflow.ng",
            is_platform_developer=True,
            password="DevPassword123!",
        )

        self.regular_user = User.objects.create_user(
            username="regular_user",
            first_name="Regular",
            last_name="User",
            email="user@school.ng",
            password="UserPassword123!",
        )

    def test_unauthenticated_redirected_from_platform_dashboard(self):
        response = self.client.get("/platform/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_regular_user_cannot_access_platform_dashboard(self):
        self.client.force_login(self.regular_user)
        response = self.client.get("/platform/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_platform_dev_can_access_platform_dashboard(self):
        self.client.force_login(self.platform_dev)
        response = self.client.get("/platform/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DEVELOPER CONTROL PLANE")
        self.assertContains(response, "Multi-Tenant School Registry")
        self.assertContains(response, "Onboard New School")


class SchoolSettingsViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Divine Grace High School",
            code="DGHS",
            slug="divine-grace",
            motto="Faith and Diligence",
            student_id_prefix="DGHS/2026/",
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="divine.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        self.director = User.objects.create_user(
            username="DGHS-DIR-0001",
            first_name="Grace",
            last_name="Oladipo",
            email="grace@divinegrace.ng",
            password="DirectorPassword123!",
        )
        self.membership = SchoolMembership.objects.create(
            user=self.director,
            school=self.school,
            role="director",
            id_number="DGHS-DIR-0001",
        )
        self.teacher = User.objects.create_user(
            username="DGHS-TCH-0001",
            first_name="Paul",
            last_name="Ojo",
            email="paul@divinegrace.ng",
            password="TeacherPassword123!",
        )
        self.teacher_membership = SchoolMembership.objects.create(
            user=self.teacher,
            school=self.school,
            role="teaching_staff",
            id_number="DGHS-TCH-0001",
        )

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get("/settings/school/", HTTP_HOST="divine.localhost")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_non_director_cannot_access_school_settings(self):
        self.client.force_login(self.teacher)
        response = self.client.get("/settings/school/", HTTP_HOST="divine.localhost", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You do not have permission to access school settings")

    def test_director_can_view_school_settings(self):
        self.client.force_login(self.director)
        response = self.client.get("/settings/school/", HTTP_HOST="divine.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "School Settings")
        self.assertContains(response, "Divine Grace High School")
        self.assertContains(response, "Faith and Diligence")
        self.assertContains(response, "DGHS/2026/")

    def test_director_can_update_school_settings(self):
        self.client.force_login(self.director)
        response = self.client.post(
            "/settings/school/",
            {
                "motto": "Knowledge is Power",
                "student_id_prefix": "DGHS-STD-",
                "official_email": "principal@divinegrace.ng",
                "official_phone": "+2348011223344",
                "school_address": "12 Faith Avenue, Ikeja, Lagos",
                "contact_person": "Mrs. Grace Oladipo",
                "admission_email": "admissions@divinegrace.ng",
                "tet_weight": "40",
                "exam_weight": "60",
            },
            HTTP_HOST="divine.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "School settings have been updated successfully")

        self.school.refresh_from_db()
        self.assertEqual(self.school.motto, "Knowledge is Power")
        self.assertEqual(self.school.student_id_prefix, "DGHS-STD-")

        self.assertEqual(get_setting("OFFICIAL_EMAIL", school=self.school), "principal@divinegrace.ng")
        self.assertEqual(get_setting("TET_WEIGHT", school=self.school), "40")
        self.assertEqual(get_setting("EXAM_WEIGHT", school=self.school), "60")


class PlatformSchoolEditViewTests(TestCase):
    def setUp(self):
        self.platform_dev = User.objects.create_user(
            username="platform_admin",
            first_name="Admin",
            last_name="Dev",
            email="admin@eduflow.ng",
            is_platform_developer=True,
            password="DevPassword123!",
        )
        self.regular_user = User.objects.create_user(
            username="regular_user2",
            first_name="Staff",
            last_name="Member",
            email="staff@school.ng",
            password="StaffPassword123!",
        )
        self.school = School.objects.create(
            name="Horizon Model School",
            code="HMS",
            slug="horizon-model-school",
            motto="Lead and Excel",
            student_id_prefix="HMS/2026/",
            is_active=True,
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="horizon.eduflow.ng",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )

    def test_unauthenticated_cannot_access_edit_school(self):
        response = self.client.get(f"/platform/schools/{self.school.id}/edit/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_regular_user_cannot_access_edit_school(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(f"/platform/schools/{self.school.id}/edit/")
        self.assertEqual(response.status_code, 302)

    def test_platform_dev_can_view_edit_school_page(self):
        self.client.force_login(self.platform_dev)
        response = self.client.get(f"/platform/schools/{self.school.id}/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Horizon Model School")
        self.assertContains(response, "HMS")
        self.assertContains(response, "horizon.eduflow.ng")

    def test_platform_dev_can_update_school_details(self):
        self.client.force_login(self.platform_dev)
        response = self.client.post(
            f"/platform/schools/{self.school.id}/edit/",
            {
                "name": "Horizon Premier Academy",
                "code": "HPA",
                "slug": "horizon-premier-academy",
                "motto": "Knowledge, Character, and Excellence",
                "student_id_prefix": "HPA-STD-",
                "is_active": "on",
                "primary_domain": "premier.eduflow.ng",
                "official_email": "admin@horizonpremier.ng",
                "official_phone": "+2348099887766",
                "school_address": "45 Victoria Island, Lagos",
                "contact_person": "Dr. Adewale",
                "admission_email": "admissions@horizonpremier.ng",
                "tet_weight": "35",
                "exam_weight": "65",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "successfully updated")

        self.school.refresh_from_db()
        self.assertEqual(self.school.name, "Horizon Premier Academy")
        self.assertEqual(self.school.code, "HPA")
        self.assertEqual(self.school.slug, "horizon-premier-academy")
        self.assertEqual(self.school.motto, "Knowledge, Character, and Excellence")
        self.assertEqual(self.school.student_id_prefix, "HPA-STD-")
        self.assertTrue(self.school.is_active)

        # Check domain updated
        new_primary = SchoolDomain.objects.get(school=self.school, is_primary=True)
        self.assertEqual(new_primary.domain, "premier.eduflow.ng")

        # Check AppVariables updated
        self.assertEqual(get_setting("OFFICIAL_EMAIL", school=self.school), "admin@horizonpremier.ng")
        self.assertEqual(get_setting("TET_WEIGHT", school=self.school), "35")
        self.assertEqual(get_setting("EXAM_WEIGHT", school=self.school), "65")


class DeactivatedSchoolLoginProtectionTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Deactivated High School",
            code="DHS",
            slug="deactivated-high",
            is_active=False,
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="deactivated.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        self.director = User.objects.create_user(
            username="9911223",
            first_name="John",
            last_name="Doe",
            email="johndoe@deactivated.ng",
            password="DirectorPassword123!",
        )
        self.membership = SchoolMembership.objects.create(
            user=self.director,
            school=self.school,
            role="director",
            id_number="9911223",
            status="active",
        )

    def test_login_to_deactivated_school_is_blocked_with_error(self):
        response = self.client.post(
            "/login/",
            {
                "identifier": "9911223",
                "password": "DirectorPassword123!",
            },
            HTTP_HOST="deactivated.localhost",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "This school portal has been deactivated. Please contact support or your school administrator."
        )

    def test_global_login_for_user_in_deactivated_school_is_blocked(self):
        response = self.client.post(
            "/login/",
            {
                "identifier": "johndoe@deactivated.ng",
                "password": "DirectorPassword123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "This school portal has been deactivated. Please contact support or your school administrator."
        )

    def test_deactivated_school_login_page_renders_alert(self):
        response = self.client.get("/login/", HTTP_HOST="deactivated.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "School Portal Deactivated")
        self.assertContains(
            response,
            "This school portal has been deactivated. Please contact support or your school administrator."
        )

