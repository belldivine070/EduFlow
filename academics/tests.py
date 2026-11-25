"""
Tests for academics application:
- Automatic seeding of Nigerian classes (Primary 1-6, JSS 1-3, SSS 1-3)
- Class deactivation per school (e.g. Primary 6)
"""
from django.test import TestCase
from schools.models import School
from academics.models import Section, SchoolClass, ClassArm, AcademicSession, Term
from academics.services import seed_school_classes


class ClassSeedingTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(name="First Academy", code="FA", slug="first-academy")
        self.school_b = School.objects.create(name="Second College", code="SC", slug="second-college")

    def test_class_seeding_creates_all_12_nigerian_classes(self):
        classes = seed_school_classes(self.school_a)
        self.assertEqual(len(classes), 12)
        self.assertEqual(SchoolClass.objects.filter(school=self.school_a).count(), 12)

        # All classes default to active
        active_count = SchoolClass.objects.filter(school=self.school_a, is_active=True).count()
        self.assertEqual(active_count, 12)

        # Check sections were created
        sections = Section.objects.filter(school=self.school_a)
        self.assertEqual(sections.count(), 3)
        section_types = set(sections.values_list("section_type", flat=True))
        self.assertEqual(section_types, {"primary", "jss", "sss"})

    def test_class_seeding_is_idempotent(self):
        seed_school_classes(self.school_a)
        seed_school_classes(self.school_a)  # Second run
        self.assertEqual(SchoolClass.objects.filter(school=self.school_a).count(), 12)

    def test_school_can_deactivate_class_without_affecting_other_schools(self):
        seed_school_classes(self.school_a)
        seed_school_classes(self.school_b)

        # School A does not offer Primary 6, so they deactivate it
        p6_a = SchoolClass.objects.get(school=self.school_a, name="Primary 6")
        p6_a.is_active = False
        p6_a.save()

        # School A now has 11 active classes
        self.assertEqual(SchoolClass.objects.filter(school=self.school_a, is_active=True).count(), 11)

        # School B still has all 12 active classes, including Primary 6
        p6_b = SchoolClass.objects.get(school=self.school_b, name="Primary 6")
        self.assertTrue(p6_b.is_active)
        self.assertEqual(SchoolClass.objects.filter(school=self.school_b, is_active=True).count(), 12)


from accounts.models import User, SchoolMembership
from schools.models import SchoolDomain


class ClassViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Royal Crest Academy", code="RCA", slug="royal-crest")
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="royal.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        self.director = User.objects.create_user(
            username="RCA-DIR-0001",
            first_name="Folake",
            last_name="Adeyemi",
            email="folake@royalcrest.ng",
            password="SecurePassword123!",
        )
        self.membership = SchoolMembership.objects.create(
            user=self.director,
            school=self.school,
            role="director",
            id_number="RCA-DIR-0001",
        )
        seed_school_classes(self.school)

    def test_class_list_view_renders_classes_under_school_domain(self):
        self.client.force_login(self.director)
        response = self.client.get("/academics/classes/", HTTP_HOST="royal.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Classes &amp; Offerings")
        self.assertContains(response, "Primary 1")
        self.assertContains(response, "Primary 6")
        self.assertContains(response, "JSS 1")
        self.assertContains(response, "SSS 3")
        self.assertEqual(response.context["active_classes"], 12)

    def test_toggle_class_deactivation_via_post(self):
        self.client.force_login(self.director)
        p6 = SchoolClass.objects.get(school=self.school, name="Primary 6")
        self.assertTrue(p6.is_active)

        # Post to toggle Primary 6 off
        response = self.client.post("/academics/classes/", {"class_id": str(p6.id)}, HTTP_HOST="royal.localhost", follow=True)
        self.assertEqual(response.status_code, 200)

        p6.refresh_from_db()
        self.assertFalse(p6.is_active)
        self.assertContains(response, "Primary 6 has been deactivated")
        self.assertEqual(response.context["active_classes"], 11)
        self.assertEqual(response.context["inactive_classes"], 1)

        # Post to toggle Primary 6 back on
        response = self.client.post("/academics/classes/", {"class_id": str(p6.id)}, HTTP_HOST="royal.localhost", follow=True)
        self.assertEqual(response.status_code, 200)

        p6.refresh_from_db()
        self.assertTrue(p6.is_active)
        self.assertContains(response, "Primary 6 has been activated")
        self.assertEqual(response.context["active_classes"], 12)

    def test_create_class_arm(self):
        self.client.force_login(self.director)
        p1 = SchoolClass.objects.get(school=self.school, name="Primary 1")
        response = self.client.post(
            f"/academics/classes/{p1.id}/arms/create/",
            {"name": "Gold"},
            HTTP_HOST="royal.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gold")
        self.assertContains(response, "added to Primary 1")
        arm = ClassArm.objects.filter(school_class=p1, name="Gold").first()
        self.assertIsNotNone(arm)
        self.assertTrue(arm.is_active)

    def test_cannot_create_duplicate_class_arm(self):
        self.client.force_login(self.director)
        p1 = SchoolClass.objects.get(school=self.school, name="Primary 1")
        ClassArm.objects.create(school=self.school, school_class=p1, name="A")

        response = self.client.post(
            f"/academics/classes/{p1.id}/arms/create/",
            {"name": "A"},
            HTTP_HOST="royal.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists for Primary 1")

    def test_toggle_class_arm_activation(self):
        self.client.force_login(self.director)
        p1 = SchoolClass.objects.get(school=self.school, name="Primary 1")
        arm = ClassArm.objects.create(school=self.school, school_class=p1, name="Diamond", is_active=True)

        # Deactivate
        response = self.client.post(
            f"/academics/arms/{arm.id}/toggle/",
            HTTP_HOST="royal.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        arm.refresh_from_db()
        self.assertFalse(arm.is_active)
        self.assertContains(response, "has been deactivated")

        # Reactivate
        response = self.client.post(
            f"/academics/arms/{arm.id}/toggle/",
            HTTP_HOST="royal.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        arm.refresh_from_db()
        self.assertTrue(arm.is_active)
        self.assertContains(response, "has been activated")


class AcademicSessionAndTermTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Greenwood College", code="GWC", slug="greenwood")
        self.school_b = School.objects.create(name="Apex Academy", code="APX", slug="apex")
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="greenwood.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        self.user = User.objects.create_user(
            username="GWC-DIR-0001",
            first_name="Babajide",
            last_name="Sanwo",
            email="director@greenwood.ng",
            password="SecurePassword123!",
        )
        self.membership = SchoolMembership.objects.create(
            user=self.user,
            school=self.school,
            role="director",
            id_number="GWC-DIR-0001",
        )

    def test_only_one_session_can_be_current_per_school(self):
        s1 = AcademicSession.objects.create(
            school=self.school,
            name="2025/2026",
            is_current=True,
        )
        self.assertTrue(s1.is_current)

        # Create second session and set it to current
        s2 = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            is_current=True,
        )
        s1.refresh_from_db()
        self.assertFalse(s1.is_current)
        self.assertTrue(s2.is_current)

        # Another school's current session is unaffected
        s_b = AcademicSession.objects.create(
            school=self.school_b,
            name="2026/2027",
            is_current=True,
        )
        s2.refresh_from_db()
        self.assertTrue(s2.is_current)
        self.assertTrue(s_b.is_current)

    def test_only_one_term_can_be_current_per_school(self):
        session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            is_current=True,
        )
        t1 = Term.objects.create(
            school=self.school,
            session=session,
            term="first",
            is_current=True,
        )
        t2 = Term.objects.create(
            school=self.school,
            session=session,
            term="second",
            is_current=True,
        )
        t1.refresh_from_db()
        self.assertFalse(t1.is_current)
        self.assertTrue(t2.is_current)

    def test_session_list_view_renders(self):
        self.client.force_login(self.user)
        response = self.client.get("/academics/sessions/", HTTP_HOST="greenwood.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Academic Sessions")

    def test_session_create_view_post(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/academics/sessions/create/",
            {
                "name": "2026/2027",
                "start_date": "2026-09-01",
                "end_date": "2027-07-20",
                "is_current": "1",
            },
            HTTP_HOST="greenwood.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        session = AcademicSession.objects.filter(school=self.school, name="2026/2027").first()
        self.assertIsNotNone(session)
        self.assertTrue(session.is_current)

    def test_session_set_current_view(self):
        self.client.force_login(self.user)
        s1 = AcademicSession.objects.create(school=self.school, name="2025/2026", is_current=True)
        s2 = AcademicSession.objects.create(school=self.school, name="2026/2027", is_current=False)

        response = self.client.post(
            f"/academics/sessions/{s2.id}/set-current/",
            HTTP_HOST="greenwood.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        s1.refresh_from_db()
        s2.refresh_from_db()
        self.assertFalse(s1.is_current)
        self.assertTrue(s2.is_current)

    def test_term_create_and_set_current(self):
        self.client.force_login(self.user)
        session = AcademicSession.objects.create(school=self.school, name="2026/2027", is_current=True)

        # Create First Term
        response = self.client.post(
            f"/academics/sessions/{session.id}/terms/create/",
            {"term": "first", "start_date": "2026-09-01", "end_date": "2026-12-15"},
            HTTP_HOST="greenwood.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        term1 = Term.objects.get(session=session, term="first")
        self.assertFalse(term1.is_current)

        # Set as current
        response = self.client.post(
            f"/academics/terms/{term1.id}/set-current/",
            HTTP_HOST="greenwood.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        term1.refresh_from_db()
        self.assertTrue(term1.is_current)


class StudentManagementTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Apex Model Academy",
            code="AMA",
            slug="apex-model",
            student_id_prefix="AMA/2026/",
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="apex.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        self.director = User.objects.create_user(
            username="8822331",
            first_name="Director",
            last_name="Apex",
            email="dir@apex.ng",
            password="DirectorPassword123!",
        )
        self.membership = SchoolMembership.objects.create(
            user=self.director,
            school=self.school,
            role="director",
            id_number="8822331",
            status="active",
        )
        self.classes = seed_school_classes(self.school)
        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2025/2026",
            is_current=True,
        )

    def test_admit_student_service_creates_user_profile_and_enrollment(self):
        from academics.services import admit_student
        from academics.models import StudentProfile, StudentEnrollment

        primary_1 = self.classes[0]
        arm_a = ClassArm.objects.create(school=self.school, school_class=primary_1, name="Gold")

        student_profile, enrollment = admit_student(
            school=self.school,
            first_name="Tobi",
            last_name="Adeyemi",
            gender="male",
            school_class=primary_1,
            class_arm=arm_a,
            session=self.session,
            emergency_contact_name="Mr. Adeyemi",
            emergency_contact_phone="+2348012345678",
        )

        # Student ID format starts with custom prefix
        self.assertTrue(student_profile.admission_number.startswith("AMA/2026/"))
        self.assertEqual(student_profile.user.username, student_profile.admission_number)
        self.assertEqual(student_profile.user.first_name, "Tobi")
        self.assertEqual(student_profile.user.last_name, "Adeyemi")
        self.assertTrue(student_profile.is_active)

        # Enrolled properly
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.student, student_profile)
        self.assertEqual(enrollment.school_class, primary_1)
        self.assertEqual(enrollment.class_arm, arm_a)
        self.assertEqual(enrollment.session, self.session)
        self.assertEqual(enrollment.status, "active")

    def test_student_list_and_create_views(self):
        self.client.force_login(self.director)

        # GET Student list
        response = self.client.get("/academics/students/", HTTP_HOST="apex.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Directory")

        # GET Student admission page
        response = self.client.get("/academics/students/admit/", HTTP_HOST="apex.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Admission")

        # POST Admit Student
        primary_2 = self.classes[1]
        response = self.client.post(
            "/academics/students/admit/",
            {
                "first_name": "Amina",
                "last_name": "Bello",
                "gender": "female",
                "school_class": str(primary_2.id),
                "session": str(self.session.id),
                "state_of_origin": "Kaduna",
                "emergency_contact_name": "Alhaji Bello",
                "emergency_contact_phone": "+2348099887766",
            },
            HTTP_HOST="apex.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admitted successfully")
        self.assertContains(response, "Amina Bello")

    def test_student_detail_and_toggle_status(self):
        from academics.services import admit_student
        from academics.models import StudentProfile

        primary_1 = self.classes[0]
        student, _ = admit_student(
            school=self.school,
            first_name="Chukwudi",
            last_name="Nnamdi",
            gender="male",
            school_class=primary_1,
            session=self.session,
        )

        self.client.force_login(self.director)

        # View Detail
        response = self.client.get(f"/academics/students/{student.id}/", HTTP_HOST="apex.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chukwudi Nnamdi")
        self.assertContains(response, student.admission_number)

        # Toggle Status
        response = self.client.post(
            f"/academics/students/{student.id}/toggle-status/",
            HTTP_HOST="apex.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertFalse(student.is_active)
        self.assertFalse(student.user.is_active)


class SubjectManagementTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Grace Field Academy",
            code="GFA",
            slug="grace-field",
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="grace.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        self.director = User.objects.create_user(
            username="9911002",
            first_name="Grace",
            last_name="Field",
            email="dir@gracefield.ng",
            password="DirectorPassword123!",
        )
        self.membership = SchoolMembership.objects.create(
            user=self.director,
            school=self.school,
            role="director",
            id_number="9911002",
            status="active",
        )
        self.classes = seed_school_classes(self.school)

    def test_subject_list_and_create(self):
        from academics.models import Subject

        self.client.force_login(self.director)

        # GET Subject list
        response = self.client.get("/academics/subjects/", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Subjects &amp; Curriculum")

        # POST Create Subject
        response = self.client.post(
            "/academics/subjects/create/",
            {
                "name": "French Language",
                "code": "FRN",
                "is_elective": "on",
            },
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "created successfully")

        subject = Subject.objects.get(school=self.school, code="FRN")
        self.assertEqual(subject.name, "French Language")
        self.assertTrue(subject.is_elective)
        self.assertTrue(subject.is_active)

    def test_subject_toggle_status(self):
        from academics.models import Subject

        subject = Subject.objects.create(
            school=self.school,
            name="Music",
            code="MUS",
            is_active=True,
        )

        self.client.force_login(self.director)
        response = self.client.post(
            f"/academics/subjects/{subject.id}/toggle/",
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        subject.refresh_from_db()
        self.assertFalse(subject.is_active)


class TeachingAssignmentTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Grace Field Academy",
            code="GFA",
            slug="grace-field",
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="grace.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        self.director = User.objects.create_user(
            username="9911002",
            first_name="Grace",
            last_name="Field",
            email="dir@gracefield.ng",
            password="DirectorPassword123!",
        )
        self.membership = SchoolMembership.objects.create(
            user=self.director,
            school=self.school,
            role="director",
            id_number="9911002",
            status="active",
        )
        self.classes = seed_school_classes(self.school)
        self.p1 = self.classes[0]  # Primary 1
        
        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            start_date="2026-09-01",
            end_date="2027-07-20",
            is_current=True,
        )
        self.teacher = User.objects.create_user(
            username="8822001",
            first_name="Bayo",
            last_name="Ogundele",
            email="bayo@gracefield.ng",
            password="TeacherPassword123!",
        )
        self.teacher_membership = SchoolMembership.objects.create(
            user=self.teacher,
            school=self.school,
            role="teaching_staff",
            id_number="8822001",
            status="active",
        )
        from academics.models import Subject
        self.subject = Subject.objects.create(
            school=self.school,
            name="English Language",
            code="ENG",
            is_active=True,
        )

    def test_create_and_manage_teaching_assignment(self):
        from academics.models import TeachingAssignment

        self.client.force_login(self.director)

        # GET Assignments List
        response = self.client.get("/academics/assignments/", HTTP_HOST="grace.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teaching Assignments")

        # POST Create Assignment
        response = self.client.post(
            "/academics/assignments/create/",
            {
                "session": self.session.id,
                "teacher": self.teacher.id,
                "subject": self.subject.id,
                "school_class": self.p1.id,
            },
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned Bayo Ogundele to teach English Language")

        assignment = TeachingAssignment.objects.get(
            school=self.school,
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.p1,
        )
        self.assertTrue(assignment.is_active)

        # Toggle status
        response = self.client.post(
            f"/academics/assignments/{assignment.id}/toggle/",
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)

        # Delete assignment
        response = self.client.post(
            f"/academics/assignments/{assignment.id}/delete/",
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TeachingAssignment.objects.filter(id=assignment.id).exists())


class StudentAttendanceTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Grace Field Academy",
            code="GFA",
            slug="grace-field",
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="grace.localhost",
            is_primary=True,
            is_verified=True,
            is_active=True,
        )
        self.director = User.objects.create_user(
            username="9911002",
            first_name="Grace",
            last_name="Field",
            email="dir@gracefield.ng",
            password="DirectorPassword123!",
        )
        self.membership = SchoolMembership.objects.create(
            user=self.director,
            school=self.school,
            role="director",
            id_number="9911002",
            status="active",
        )
        self.classes = seed_school_classes(self.school)
        self.p1 = self.classes[0]

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            start_date="2026-09-01",
            end_date="2027-07-20",
            is_current=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            session=self.session,
            term="first",
            start_date="2026-09-01",
            end_date="2026-12-15",
            is_current=True,
        )

        from academics.services import admit_student
        self.student, _ = admit_student(
            school=self.school,
            first_name="Tunde",
            last_name="Bakare",
            school_class=self.p1,
            session=self.session,
        )

    def test_attendance_register_get_and_post(self):
        from academics.models import StudentAttendance

        self.client.force_login(self.director)

        # GET Register
        response = self.client.get(
            f"/academics/attendance/register/?class_id={self.p1.id}&date=2026-10-15",
            HTTP_HOST="grace.localhost",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Attendance Register")
        self.assertContains(response, "Tunde Bakare")

        # POST Mark Attendance
        response = self.client.post(
            "/academics/attendance/register/",
            {
                "class_id": str(self.p1.id),
                "date": "2026-10-15",
                "student_ids": [str(self.student.id)],
                f"status_{self.student.id}": "present",
                f"remarks_{self.student.id}": "Early arrival",
            },
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance marked successfully")

        # Verify in DB
        att = StudentAttendance.objects.get(
            school=self.school,
            student=self.student,
            date="2026-10-15",
        )
        self.assertEqual(att.status, "present")
        self.assertEqual(att.remarks, "Early arrival")

        # Test attendance statistics calculation
        from academics.services import get_student_attendance_stats
        stats = get_student_attendance_stats(self.student, session=self.session, term=self.term)
        self.assertEqual(stats["total_days"], 1)
        self.assertEqual(stats["present"], 1)
        self.assertEqual(stats["percentage"], 100.0)


class ParentRelationshipTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Grace Field Academy",
            code="GFA",
            slug="grace-field",
        )
        self.classes = seed_school_classes(self.school)
        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            start_date="2026-09-01",
            end_date="2027-07-20",
            is_current=True,
        )
        from academics.services import admit_student
        self.student, _ = admit_student(
            school=self.school,
            first_name="Emeka",
            last_name="Okafor",
            school_class=self.classes[0],
            session=self.session,
        )

    def test_link_parent_to_student(self):
        from accounts.services import link_parent_to_student
        from accounts.models import ParentStudentRelationship

        parent_user = User.objects.create_user(
            username="GFA-PAR-0001",
            first_name="Chinedu",
            last_name="Okafor",
            email="chinedu@okafor.ng",
        )

        rel = link_parent_to_student(
            school=self.school,
            parent=parent_user,
            student=self.student,
            relationship_type="father",
            is_primary_contact=True,
        )

        self.assertEqual(rel.relationship_type, "father")
        self.assertTrue(rel.is_primary_contact)
        self.assertEqual(ParentStudentRelationship.objects.filter(school=self.school).count(), 1)



