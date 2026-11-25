"""
Tests for staff application:
- StaffProfile model creation and string representation
- StaffListView directory with search and role filters
- StaffCreateView onboarding with auto-generated numeric Staff ID
- Permissions enforcement (only Director/Principal can onboard or toggle staff)
- StaffDetailView profile viewing
- StaffStatusToggleView active/inactive switching
"""
from django.test import TestCase
from schools.models import School, SchoolDomain
from accounts.models import User, SchoolMembership
from staff.models import StaffProfile
from core.constants import (
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
    MEMBERSHIP_ACTIVE,
    MEMBERSHIP_INACTIVE,
)


class StaffAppTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Grace Baptist School",
            code="GBS",
            slug="grace-baptist",
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="grace.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )

        # Director
        self.director = User.objects.create_user(
            username="GBS-DIR-0001",
            first_name="Samuel",
            last_name="Ajayi",
            email="director@gracebaptist.ng",
            password="DirectorPassword123!",
        )
        self.director_membership = SchoolMembership.objects.create(
            user=self.director,
            school=self.school,
            role=ROLE_DIRECTOR,
            id_number="GBS-DIR-0001",
            status=MEMBERSHIP_ACTIVE,
        )

        # Existing Teacher
        self.teacher = User.objects.create_user(
            username="849201",
            first_name="Blessing",
            last_name="Okonkwo",
            email="blessing@gracebaptist.ng",
            phone_number="08031234567",
            password="TeacherPassword123!",
        )
        self.teacher_membership = SchoolMembership.objects.create(
            user=self.teacher,
            school=self.school,
            role=ROLE_TEACHING_STAFF,
            id_number="849201",
            status=MEMBERSHIP_ACTIVE,
        )
        self.teacher_profile = StaffProfile.objects.create(
            school=self.school,
            user=self.teacher,
            title="Mrs.",
            qualification="B.Sc (Ed) Mathematics",
            specialization="Mathematics",
            designation="Senior Mathematics Teacher",
        )

    def test_staff_profile_creation_and_str(self):
        self.assertIn("Mrs. Blessing Okonkwo", str(self.teacher_profile))
        self.assertIn("849201", str(self.teacher_profile))

    def test_staff_list_view_renders(self):
        self.client.force_login(self.director)
        response = self.client.get("/staff/", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff Directory")
        self.assertContains(response, "Blessing Okonkwo")
        self.assertContains(response, "849201")
        self.assertContains(response, "Senior Mathematics Teacher")

    def test_staff_list_search_by_name_and_id(self):
        self.client.force_login(self.director)

        # Search by name
        response = self.client.get("/staff/?q=Blessing", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blessing Okonkwo")

        # Search by Staff ID
        response = self.client.get("/staff/?q=849201", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blessing Okonkwo")

        # Search non-existent
        response = self.client.get("/staff/?q=NonExistentPerson", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Staff Members Found")

    def test_staff_list_filter_by_role(self):
        self.client.force_login(self.director)

        # Filter by teaching_staff
        response = self.client.get("/staff/?role=teaching_staff", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blessing Okonkwo")

        # Filter by non_teaching_staff (none yet)
        response = self.client.get("/staff/?role=non_teaching_staff", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Staff Members Found")

    def test_teacher_cannot_access_staff_onboarding_form(self):
        self.client.force_login(self.teacher)
        response = self.client.get("/staff/onboard/", HTTP_HOST="grace.localhost", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only school leadership can onboard new staff")

    def test_director_can_access_staff_onboarding_form(self):
        self.client.force_login(self.director)
        response = self.client.get("/staff/onboard/", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Onboard New Staff")

    def test_director_onboards_new_staff_member(self):
        self.client.force_login(self.director)
        response = self.client.post(
            "/staff/onboard/",
            {
                "first_name": "Tunde",
                "last_name": "Bakare",
                "middle_name": "Emmanuel",
                "email": "tunde.bakare@gracebaptist.ng",
                "phone_number": "08059876543",
                "role": ROLE_TEACHING_STAFF,
                "title": "Mr.",
                "gender": "male",
                "qualification": "B.Ed English",
                "specialization": "English Language",
                "designation": "English Teacher",
                "date_employed": "2026-09-01",
                "next_of_kin_name": "Mrs. Folashade Bakare",
                "next_of_kin_phone": "08031112233",
                "next_of_kin_relationship": "Spouse",
            },
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "onboarded successfully")

        # Verify user created with unique numeric Staff ID
        user = User.objects.get(email="tunde.bakare@gracebaptist.ng")
        self.assertTrue(user.username.isdigit())
        self.assertEqual(user.first_name, "Tunde")
        self.assertEqual(user.last_name, "Bakare")

        # Verify membership
        membership = SchoolMembership.objects.get(user=user, school=self.school)
        self.assertEqual(membership.role, ROLE_TEACHING_STAFF)
        self.assertEqual(membership.status, MEMBERSHIP_ACTIVE)

        # Verify StaffProfile
        profile = StaffProfile.objects.get(user=user, school=self.school)
        self.assertEqual(profile.specialization, "English Language")
        self.assertEqual(profile.title, "Mr.")

    def test_staff_detail_view(self):
        self.client.force_login(self.director)
        response = self.client.get(f"/staff/{self.teacher_membership.id}/", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blessing Okonkwo")
        self.assertContains(response, "849201")
        self.assertContains(response, "Senior Mathematics Teacher")
        self.assertContains(response, "B.Sc (Ed) Mathematics")

    def test_toggle_staff_status(self):
        self.client.force_login(self.director)

        # Deactivate teacher
        response = self.client.post(
            f"/staff/{self.teacher_membership.id}/toggle-status/",
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.teacher_membership.refresh_from_db()
        self.assertEqual(self.teacher_membership.status, MEMBERSHIP_INACTIVE)
        self.assertContains(response, "has been deactivated")

        # Reactivate teacher
        response = self.client.post(
            f"/staff/{self.teacher_membership.id}/toggle-status/",
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.teacher_membership.refresh_from_db()
        self.assertEqual(self.teacher_membership.status, MEMBERSHIP_ACTIVE)
        self.assertContains(response, "has been activated")

    def test_cannot_deactivate_own_membership(self):
        self.client.force_login(self.director)
        response = self.client.post(
            f"/staff/{self.director_membership.id}/toggle-status/",
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You cannot deactivate your own membership")
        self.director_membership.refresh_from_db()
        self.assertEqual(self.director_membership.status, MEMBERSHIP_ACTIVE)

    def test_staff_attendance_register_get_and_post(self):
        from staff.models import StaffAttendance

        self.client.force_login(self.director)

        # GET Register
        response = self.client.get(
            "/staff/attendance/register/?date=2026-10-15",
            HTTP_HOST="grace.localhost",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff Attendance Register")
        self.assertContains(response, "Blessing Okonkwo")

        # POST Mark Attendance
        staff_profile = StaffProfile.objects.get(school=self.school, user=self.teacher)
        response = self.client.post(
            "/staff/attendance/register/",
            {
                "date": "2026-10-15",
                "staff_ids": [str(staff_profile.id)],
                f"status_{staff_profile.id}": "present",
                f"time_in_{staff_profile.id}": "07:30",
                f"time_out_{staff_profile.id}": "16:00",
                f"remarks_{staff_profile.id}": "On time",
            },
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff attendance recorded successfully")

        # Verify DB
        att = StaffAttendance.objects.get(
            school=self.school,
            staff=staff_profile,
            date="2026-10-15",
        )
        self.assertEqual(att.status, "present")
        self.assertEqual(att.remarks, "On time")

