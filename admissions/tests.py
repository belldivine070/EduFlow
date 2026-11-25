"""
Tests for admissions module.
Covers application number generation, public application submission,
status tracking, admission letter rendering, staff review, and atomic student onboarding.
"""
import datetime
from django.test import TestCase, Client
from django.utils import timezone
from django.core.exceptions import ValidationError

from schools.models import School, SchoolDomain
from academics.models import AcademicSession, SchoolClass, ClassArm, StudentProfile, StudentEnrollment
from academics.services import seed_school_classes
from accounts.models import User, SchoolMembership, ParentStudentRelationship
from core.constants import ROLE_DIRECTOR, ROLE_STUDENT, ROLE_PARENT
from admissions.models import (
    AdmissionApplication,
    APPLICATION_STATUS_PENDING,
    APPLICATION_STATUS_UNDER_REVIEW,
    APPLICATION_STATUS_INTERVIEW_SCHEDULED,
    APPLICATION_STATUS_ADMITTED,
    APPLICATION_STATUS_ENROLLED,
)
from admissions.services import (
    generate_application_number,
    submit_admission_application,
    convert_applicant_to_student,
)


class AdmissionsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Heritage Academy",
            code="HA",
            slug="heritage-academy",
            student_id_prefix="HA-STD-",
            is_active=True,
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="heritage.localhost",
            is_primary=True,
            is_verified=True,
        )

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2027, 7, 31),
            is_current=True,
        )

        seed_school_classes(self.school)
        self.school_class = SchoolClass.objects.get(school=self.school, name="JSS 1")

        self.class_arm = ClassArm.objects.create(
            school=self.school,
            school_class=self.school_class,
            name="Gold",
            is_active=True,
        )

        # Create Director Staff User
        self.staff_user = User.objects.create_user(
            username="HA-DIR-0001",
            first_name="Folashade",
            last_name="Tinubu",
            email="director@heritage.ng",
            password="DirectorPassword123!",
        )
        SchoolMembership.objects.create(
            user=self.staff_user,
            school=self.school,
            role=ROLE_DIRECTOR,
            id_number="HA-DIR-0001",
            status="active",
        )

    def test_generate_application_number(self):
        """Application number must follow {school.code}-ADM-{year}-{seq:04d} format."""
        num1 = generate_application_number(self.school, self.session)
        self.assertEqual(num1, "HA-ADM-2026-0001")

        # Create an application with this number
        AdmissionApplication.objects.create(
            school=self.school,
            session=self.session,
            application_number=num1,
            first_name="Chidi",
            last_name="Okafor",
            date_of_birth=datetime.date(2014, 5, 12),
            applying_for_class=self.school_class,
            parent_name="Emeka Okafor",
            parent_phone="+2348011223344",
        )

        num2 = generate_application_number(self.school, self.session)
        self.assertEqual(num2, "HA-ADM-2026-0002")

    def test_submit_admission_application_service(self):
        """submit_admission_application should create a complete pending application."""
        app = submit_admission_application(
            school=self.school,
            session=self.session,
            first_name="Amina",
            last_name="Bello",
            middle_name="Zainab",
            gender="female",
            date_of_birth=datetime.date(2013, 8, 20),
            applying_for_class=self.school_class,
            state_of_origin="Kano",
            lga="Nassarawa",
            residential_address="14 Crescent Road, Kano",
            parent_name="Alhaji Bello",
            parent_email="bello@example.com",
            parent_phone="+2348099887766",
            parent_relationship="Father",
        )

        self.assertEqual(app.application_number, "HA-ADM-2026-0001")
        self.assertEqual(app.status, APPLICATION_STATUS_PENDING)
        self.assertEqual(app.full_name, "Amina Zainab Bello")
        self.assertIsNone(app.enrolled_student)

    def test_convert_applicant_to_student_service(self):
        """Converting an admitted applicant must create student user, profile, enrollment, and link parent."""
        app = submit_admission_application(
            school=self.school,
            session=self.session,
            first_name="Tunde",
            last_name="Bakare",
            gender="male",
            date_of_birth=datetime.date(2012, 3, 15),
            applying_for_class=self.school_class,
            parent_name="Mrs. Funke Bakare",
            parent_email="funke.bakare@example.com",
            parent_phone="+2348033445566",
            parent_relationship="Mother",
        )

        student_profile, enrollment, parent_rel = convert_applicant_to_student(
            app,
            class_arm=self.class_arm,
            admitted_by=self.staff_user,
        )

        # Verify Student
        self.assertIsNotNone(student_profile)
        self.assertTrue(student_profile.admission_number.startswith("HA-STD-"))
        self.assertEqual(student_profile.user.first_name, "Tunde")
        self.assertEqual(student_profile.user.last_name, "Bakare")

        # Verify Enrollment
        self.assertEqual(enrollment.student, student_profile)
        self.assertEqual(enrollment.school_class, self.school_class)
        self.assertEqual(enrollment.class_arm, self.class_arm)
        self.assertEqual(enrollment.session, self.session)

        # Verify Parent Account and Relationship
        self.assertIsNotNone(parent_rel)
        self.assertEqual(parent_rel.parent.email, "funke.bakare@example.com")
        self.assertEqual(parent_rel.student, student_profile)
        self.assertTrue(parent_rel.is_primary_contact)

        # Verify Application State
        app.refresh_from_db()
        self.assertEqual(app.status, APPLICATION_STATUS_ENROLLED)
        self.assertEqual(app.enrolled_student, student_profile)
        self.assertEqual(app.reviewed_by, self.staff_user)

        # Converting again must raise ValidationError
        with self.assertRaises(ValidationError):
            convert_applicant_to_student(app)

    def test_public_apply_view_flow(self):
        """Prospective parents can view and submit the public admission form via tenant domain."""
        # 1. GET application form
        response = self.client.get("/admissions/apply/", HTTP_HOST="heritage.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Heritage Academy")
        self.assertContains(response, "JSS 1")

        # 2. POST application form
        post_data = {
            "session_id": str(self.session.id),
            "class_id": str(self.school_class.id),
            "first_name": "Segun",
            "last_name": "Obasanjo",
            "middle_name": "Aremu",
            "gender": "male",
            "date_of_birth": "2013-11-05",
            "state_of_origin": "Ogun",
            "lga": "Abeokuta North",
            "residential_address": "Hilltop Estate, Abeokuta",
            "parent_name": "Chief Obasanjo",
            "parent_email": "chief@example.com",
            "parent_phone": "+2348022334455",
            "parent_relationship": "Father",
        }
        post_response = self.client.post("/admissions/apply/", post_data, HTTP_HOST="heritage.localhost")
        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, "/admissions/apply/success/")

        # Verify application created
        app = AdmissionApplication.objects.get(school=self.school, first_name="Segun")
        self.assertEqual(app.application_number, "HA-ADM-2026-0001")

        # 3. GET success view
        success_response = self.client.get("/admissions/apply/success/", HTTP_HOST="heritage.localhost")
        self.assertEqual(success_response.status_code, 200)
        self.assertContains(success_response, "Application Submitted!")
        self.assertContains(success_response, "HA-ADM-2026-0001")

    def test_application_status_lookup_view(self):
        """Applicants can track application status using application number and parent phone."""
        app = submit_admission_application(
            school=self.school,
            session=self.session,
            first_name="Chioma",
            last_name="Eze",
            gender="female",
            date_of_birth=datetime.date(2014, 7, 19),
            applying_for_class=self.school_class,
            parent_name="Ngozi Eze",
            parent_phone="+2348055667788",
        )

        # GET status page
        get_res = self.client.get("/admissions/status/", HTTP_HOST="heritage.localhost")
        self.assertEqual(get_res.status_code, 200)

        # POST lookup with matching credentials
        lookup_res = self.client.post(
            "/admissions/status/",
            {"application_number": app.application_number, "phone_or_email": "+2348055667788"},
            HTTP_HOST="heritage.localhost",
        )
        self.assertEqual(lookup_res.status_code, 200)
        self.assertContains(lookup_res, "Chioma Eze")
        self.assertContains(lookup_res, "Pending")

    def test_admission_letter_view(self):
        """Admitted applicant can view official printable admission letter."""
        app = submit_admission_application(
            school=self.school,
            session=self.session,
            first_name="Kelechi",
            last_name="Nwosu",
            gender="male",
            date_of_birth=datetime.date(2012, 1, 10),
            applying_for_class=self.school_class,
            parent_name="Dr. Nwosu",
            parent_phone="+2348077889900",
        )
        app.status = APPLICATION_STATUS_ADMITTED
        app.save()

        # Staff can view
        self.client.force_login(self.staff_user)
        response = self.client.get(f"/admissions/letter/{app.id}/", HTTP_HOST="heritage.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Offer of Provisional Admission")
        self.assertContains(response, "Kelechi Nwosu")
        self.assertContains(response, "Heritage Academy")

    def test_staff_admin_management_and_conversion_flow(self):
        """Staff can list, review, make decisions, and convert applicants to students."""
        app = submit_admission_application(
            school=self.school,
            session=self.session,
            first_name="Damilola",
            last_name="Adegoke",
            gender="female",
            date_of_birth=datetime.date(2013, 4, 18),
            applying_for_class=self.school_class,
            parent_name="Mr. Adegoke",
            parent_phone="+2348044556677",
        )

        self.client.force_login(self.staff_user)

        # 1. Staff List View
        list_res = self.client.get("/admissions/applications/", HTTP_HOST="heritage.localhost")
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "Damilola Adegoke")

        # 2. Staff Detail View
        detail_res = self.client.get(f"/admissions/applications/{app.id}/", HTTP_HOST="heritage.localhost")
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "Applicant Information")

        # 3. Decision POST (Set to Admitted)
        decision_res = self.client.post(
            f"/admissions/applications/{app.id}/decision/",
            {"status": "admitted", "decision_notes": "Passed entrance interview with excellence."},
            HTTP_HOST="heritage.localhost",
        )
        self.assertEqual(decision_res.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, APPLICATION_STATUS_ADMITTED)

        # 4. Convert POST
        convert_res = self.client.post(
            f"/admissions/applications/{app.id}/convert/",
            {"class_arm_id": str(self.class_arm.id)},
            HTTP_HOST="heritage.localhost",
        )
        self.assertEqual(convert_res.status_code, 302)

        app.refresh_from_db()
        self.assertEqual(app.status, APPLICATION_STATUS_ENROLLED)
        self.assertIsNotNone(app.enrolled_student)
        self.assertEqual(app.enrolled_student.admission_number, "HA-STD-0001")
