"""
Tests for examinations application:
- Default grading scale seeding
- Score entry validation (CA <= 30%, Exam <= 70%)
- Termly report compilation and class ranking
- Principal review and approval
- Result publication workflow
"""
from decimal import Decimal
from django.test import TestCase
from schools.models import School, SchoolDomain
from accounts.models import User, SchoolMembership
from academics.models import Subject, SchoolClass, AcademicSession, Term, StudentProfile
from academics.services import seed_school_classes, admit_student
from examinations.models import (
    GradingScale,
    StudentSubjectResult,
    StudentTermReport,
    RESULT_STATUS_DRAFT,
    RESULT_STATUS_APPROVED,
    RESULT_STATUS_PUBLISHED,
)
from examinations.services import (
    seed_default_grading_scale,
    record_student_subject_score,
    compute_term_reports_for_class,
    approve_term_results,
    publish_term_results,
)


class ExaminationTests(TestCase):
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

        self.principal = User.objects.create_user(
            username="9911001",
            first_name="Folake",
            last_name="Adeyemi",
            email="principal@gracefield.ng",
            password="PrincipalPassword123!",
        )
        self.principal_membership = SchoolMembership.objects.create(
            user=self.principal,
            school=self.school,
            role="principal",
            id_number="9911001",
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

        self.math = Subject.objects.create(school=self.school, name="Mathematics", code="MTH")
        self.eng = Subject.objects.create(school=self.school, name="English Language", code="ENG")

        # 2 Students
        self.student_1, _ = admit_student(
            school=self.school,
            first_name="Amaka",
            last_name="Eze",
            school_class=self.p1,
            session=self.session,
        )
        self.student_2, _ = admit_student(
            school=self.school,
            first_name="Bola",
            last_name="Tinubu",
            school_class=self.p1,
            session=self.session,
        )

        seed_default_grading_scale(self.school)

    def test_score_entry_and_validation(self):
        # 1. Valid scores
        res1 = record_student_subject_score(
            school=self.school,
            student=self.student_1,
            session=self.session,
            term=self.term,
            subject=self.math,
            school_class=self.p1,
            ca_score=26.0,
            exam_score=58.0,
        )
        self.assertEqual(res1.total_score, Decimal("84.0"))
        self.assertEqual(res1.grade, "A")

        # 2. Invalid CA score (> 30)
        with self.assertRaises(ValueError):
            record_student_subject_score(
                school=self.school,
                student=self.student_1,
                session=self.session,
                term=self.term,
                subject=self.math,
                school_class=self.p1,
                ca_score=35.0,  # Invalid
                exam_score=50.0,
            )

        # 3. Invalid Exam score (> 70)
        with self.assertRaises(ValueError):
            record_student_subject_score(
                school=self.school,
                student=self.student_1,
                session=self.session,
                term=self.term,
                subject=self.math,
                school_class=self.p1,
                ca_score=20.0,
                exam_score=75.0,  # Invalid
            )

    def test_term_report_compilation_and_ranking(self):
        # Student 1 scores (Avg: 85%)
        record_student_subject_score(
            school=self.school,
            student=self.student_1,
            session=self.session,
            term=self.term,
            subject=self.math,
            school_class=self.p1,
            ca_score=25.0,
            exam_score=65.0,
        )
        record_student_subject_score(
            school=self.school,
            student=self.student_1,
            session=self.session,
            term=self.term,
            subject=self.eng,
            school_class=self.p1,
            ca_score=26.0,
            exam_score=54.0,
        )

        # Student 2 scores (Avg: 65%)
        record_student_subject_score(
            school=self.school,
            student=self.student_2,
            session=self.session,
            term=self.term,
            subject=self.math,
            school_class=self.p1,
            ca_score=18.0,
            exam_score=42.0,
        )
        record_student_subject_score(
            school=self.school,
            student=self.student_2,
            session=self.session,
            term=self.term,
            subject=self.eng,
            school_class=self.p1,
            ca_score=20.0,
            exam_score=50.0,
        )

        reports = compute_term_reports_for_class(
            school=self.school,
            session=self.session,
            term=self.term,
            school_class=self.p1,
        )

        self.assertEqual(len(reports), 2)
        r1 = StudentTermReport.objects.get(student=self.student_1)
        r2 = StudentTermReport.objects.get(student=self.student_2)

        # Student 1 should be 1st position, Student 2 should be 2nd
        self.assertEqual(r1.class_rank, 1)
        self.assertEqual(r2.class_rank, 2)
        self.assertEqual(r1.average_score, Decimal("85.0"))
        self.assertEqual(r2.average_score, Decimal("65.0"))

    def test_approval_and_publication_workflow(self):
        record_student_subject_score(
            school=self.school,
            student=self.student_1,
            session=self.session,
            term=self.term,
            subject=self.math,
            school_class=self.p1,
            ca_score=25.0,
            exam_score=60.0,
        )

        # 1. Initially draft
        res = StudentSubjectResult.objects.get(student=self.student_1, subject=self.math)
        self.assertEqual(res.status, RESULT_STATUS_DRAFT)

        # 2. Principal approves
        count = approve_term_results(
            school=self.school,
            session=self.session,
            term=self.term,
            school_class=self.p1,
            approved_by=self.principal,
        )
        self.assertEqual(count, 1)
        res.refresh_from_db()
        self.assertEqual(res.status, RESULT_STATUS_APPROVED)
        self.assertEqual(res.approved_by, self.principal)

        # 3. Publish to portal
        pub_count = publish_term_results(
            school=self.school,
            session=self.session,
            term=self.term,
            school_class=self.p1,
        )
        self.assertEqual(pub_count, 1)
        res.refresh_from_db()
        self.assertEqual(res.status, RESULT_STATUS_PUBLISHED)
