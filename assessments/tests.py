"""
Tests for assessments application:
- Question creation (Multiple Choice, True/False, Essay)
- Assessment creation and attaching questions
- Student taking CBT test and auto-marking
- Teacher marking queue for essay questions
"""
from decimal import Decimal
from django.test import TestCase
from schools.models import School, SchoolDomain
from accounts.models import User, SchoolMembership
from academics.models import Subject, SchoolClass, AcademicSession, Term, StudentProfile
from academics.services import seed_school_classes, admit_student
from assessments.models import (
    Question,
    QuestionOption,
    Assessment,
    AssessmentQuestion,
    StudentAssessmentSubmission,
    StudentAssessmentAnswer,
    QUESTION_TYPE_MULTIPLE_CHOICE,
    QUESTION_TYPE_TRUE_FALSE,
    QUESTION_TYPE_ESSAY,
    SUBMISSION_STATUS_SUBMITTED,
    SUBMISSION_STATUS_MARKED,
)
from assessments.services import (
    create_question,
    submit_student_assessment,
    mark_essay_answer,
)


class AssessmentTests(TestCase):
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

        self.teacher = User.objects.create_user(
            username="9911002",
            first_name="Grace",
            last_name="Field",
            email="teacher@gracefield.ng",
            password="TeacherPassword123!",
        )
        self.teacher_membership = SchoolMembership.objects.create(
            user=self.teacher,
            school=self.school,
            role="teaching_staff",
            id_number="9911002",
            status="active",
        )

        self.classes = seed_school_classes(self.school)
        self.jss1 = self.classes[6]  # JSS 1

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

        self.subject = Subject.objects.create(
            school=self.school,
            name="Mathematics",
            code="MTH",
            is_active=True,
        )

        self.student, _ = admit_student(
            school=self.school,
            first_name="Emeka",
            last_name="Okafor",
            school_class=self.jss1,
            session=self.session,
        )

    def test_create_questions_and_options(self):
        # 1. Multiple Choice Question
        mcq = create_question(
            school=self.school,
            subject=self.subject,
            prompt="What is the square root of 64?",
            question_type=QUESTION_TYPE_MULTIPLE_CHOICE,
            default_marks=2.0,
            options=[
                {"text": "6", "is_correct": False},
                {"text": "8", "is_correct": True},
                {"text": "10", "is_correct": False},
                {"text": "12", "is_correct": False},
            ],
            created_by=self.teacher,
        )
        self.assertEqual(mcq.options.count(), 4)
        self.assertEqual(mcq.options.filter(is_correct=True).first().option_text, "8")

        # 2. True / False Question
        tf = create_question(
            school=self.school,
            subject=self.subject,
            prompt="A prime number has only two factors.",
            question_type=QUESTION_TYPE_TRUE_FALSE,
            default_marks=1.0,
            options=[
                {"text": "True", "is_correct": True},
                {"text": "False", "is_correct": False},
            ],
            created_by=self.teacher,
        )
        self.assertEqual(tf.options.count(), 2)

        # 3. Essay Question
        essay = create_question(
            school=self.school,
            subject=self.subject,
            prompt="State and explain the Pythagorean theorem.",
            question_type=QUESTION_TYPE_ESSAY,
            default_marks=5.0,
            created_by=self.teacher,
        )
        self.assertEqual(essay.options.count(), 0)

    def test_cbt_assessment_auto_marking_and_essay_grading(self):
        # 1. Create Assessment
        assessment = Assessment.objects.create(
            school=self.school,
            session=self.session,
            term=self.term,
            subject=self.subject,
            school_class=self.jss1,
            title="First Continuous Assessment (CA 1)",
            duration_minutes=30,
            total_marks=Decimal("10.0"),
            pass_mark=Decimal("5.0"),
            is_published=True,
            created_by=self.teacher,
        )

        # Add MCQ
        q1 = create_question(
            school=self.school,
            subject=self.subject,
            prompt="5 + 7 = ?",
            question_type=QUESTION_TYPE_MULTIPLE_CHOICE,
            default_marks=2.0,
            options=[
                {"text": "10", "is_correct": False},
                {"text": "12", "is_correct": True},
            ],
        )
        opt_correct = q1.options.get(is_correct=True)
        AssessmentQuestion.objects.create(assessment=assessment, question=q1, order=1, marks=Decimal("2.0"))

        # Add Essay
        q2 = create_question(
            school=self.school,
            subject=self.subject,
            prompt="Explain acute angles with an example.",
            question_type=QUESTION_TYPE_ESSAY,
            default_marks=8.0,
        )
        AssessmentQuestion.objects.create(assessment=assessment, question=q2, order=2, marks=Decimal("8.0"))

        # 2. Student Submits Assessment
        submission = StudentAssessmentSubmission.objects.create(
            school=self.school,
            assessment=assessment,
            student=self.student,
        )

        submit_student_assessment(
            submission=submission,
            answers_data=[
                {"question_id": str(q1.id), "selected_option_id": str(opt_correct.id)},
                {"question_id": str(q2.id), "essay_text": "An acute angle is an angle less than 90 degrees, e.g. 45 degrees."},
            ],
        )

        submission.refresh_from_db()
        self.assertEqual(submission.status, SUBMISSION_STATUS_SUBMITTED)
        self.assertEqual(submission.auto_marked_score, Decimal("2.0"))
        self.assertEqual(submission.total_score, Decimal("2.0"))

        # 3. Teacher Grades Essay in Marking Queue
        essay_answer = StudentAssessmentAnswer.objects.get(submission=submission, question=q2)
        self.assertIsNone(essay_answer.is_correct)

        mark_essay_answer(
            answer=essay_answer,
            marks_awarded=7.0,
            feedback="Excellent definition and correct example.",
            marked_by=self.teacher,
        )

        submission.refresh_from_db()
        self.assertEqual(submission.status, SUBMISSION_STATUS_MARKED)
        self.assertEqual(submission.manual_marked_score, Decimal("7.0"))
        self.assertEqual(submission.total_score, Decimal("9.0"))
        self.assertEqual(submission.percentage, Decimal("90.0"))
        self.assertTrue(submission.is_passed)

    def test_views_question_bank_and_assessment_list(self):
        self.client.force_login(self.teacher)

        # GET Question Bank
        res = self.client.get("/assessments/questions/", HTTP_HOST="grace.localhost")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Question Bank")

        # POST Create Question
        res = self.client.post(
            "/assessments/questions/create/",
            {
                "subject": str(self.subject.id),
                "question_type": "multiple_choice",
                "prompt": "Which of these is a multiple of 3?",
                "default_marks": "2.0",
                "option_1": "4",
                "option_2": "9",
                "option_3": "10",
                "option_4": "14",
                "correct_option": "2",
            },
            HTTP_HOST="grace.localhost",
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Question.objects.filter(school=self.school, prompt__contains="multiple of 3").exists())

        # GET Assessment List
        res = self.client.get("/assessments/", HTTP_HOST="grace.localhost")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Continuous Assessments &amp; Tests")
