"""
Assessments data models.

Covers:
- Question Bank (Objective multiple choice, True/False, Essay)
- Question Options and Images
- Assessment / CBT Tests configuration
- Student Submissions and Answers
- Auto-marking and manual marking workflows
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from core.models import TimestampedModel


QUESTION_TYPE_MULTIPLE_CHOICE = "multiple_choice"
QUESTION_TYPE_TRUE_FALSE = "true_false"
QUESTION_TYPE_ESSAY = "essay"

QUESTION_TYPE_CHOICES = [
    (QUESTION_TYPE_MULTIPLE_CHOICE, "Multiple Choice (Objective)"),
    (QUESTION_TYPE_TRUE_FALSE, "True / False"),
    (QUESTION_TYPE_ESSAY, "Essay / Theory"),
]

SUBMISSION_STATUS_IN_PROGRESS = "in_progress"
SUBMISSION_STATUS_SUBMITTED = "submitted"
SUBMISSION_STATUS_MARKED = "marked"

SUBMISSION_STATUS_CHOICES = [
    (SUBMISSION_STATUS_IN_PROGRESS, "In Progress"),
    (SUBMISSION_STATUS_SUBMITTED, "Submitted (Pending Marking)"),
    (SUBMISSION_STATUS_MARKED, "Marked & Finalized"),
]


class QuestionCategory(TimestampedModel):
    """
    Topic or category grouping for questions within a subject.
    E.g., 'Algebra', 'Cell Biology', 'Verbal Reasoning'.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="question_categories",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="question_categories",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Question Category"
        verbose_name_plural = "Question Categories"
        ordering = ["subject__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "subject", "name"],
                name="unique_school_subject_question_category",
            )
        ]

    def __str__(self):
        return f"{self.subject.code} - {self.name}"


class Question(TimestampedModel):
    """
    Individual question stored in the school's question bank.
    Can be reused across multiple tests and continuous assessments.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    category = models.ForeignKey(
        QuestionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    question_type = models.CharField(
        max_length=30,
        choices=QUESTION_TYPE_CHOICES,
        default=QUESTION_TYPE_MULTIPLE_CHOICE,
    )
    prompt = models.TextField(help_text="The question text or prompt.")
    explanation = models.TextField(
        blank=True,
        default="",
        help_text="Optional pedagogical explanation of the correct solution.",
    )
    default_marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_questions",
    )

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ["subject__name", "-created_at"]

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.prompt[:60]}..."


class QuestionOption(models.Model):
    """
    Options for multiple-choice or true/false questions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Question Option"
        verbose_name_plural = "Question Options"
        ordering = ["order"]

    def __str__(self):
        return f"{self.option_text} ({'Correct' if self.is_correct else 'Incorrect'})"


class QuestionImage(models.Model):
    """
    Diagram, chart, or scientific figure attached to a question.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="questions/diagrams/")
    caption = models.CharField(max_length=200, blank=True, default="")
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Image for question {self.question_id}"


class Assessment(TimestampedModel):
    """
    Continuous Assessment (CA test), quiz, or CBT test for students.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    school_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    title = models.CharField(max_length=200, help_text="e.g. First CA Test, Mid-Term Test")
    instructions = models.TextField(blank=True, default="")
    duration_minutes = models.PositiveIntegerField(default=45, help_text="Duration in minutes (0 for untimed)")
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=30.0)
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=15.0)
    is_published = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_assessments",
    )

    class Meta:
        verbose_name = "Assessment"
        verbose_name_plural = "Assessments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.subject.name} ({self.school_class.name})"


class AssessmentQuestion(models.Model):
    """
    Ordered question included in a specific assessment with allocated marks.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="assessment_questions",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="included_in_assessments",
    )
    order = models.PositiveSmallIntegerField(default=1)
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "question"],
                name="unique_assessment_question",
            )
        ]

    def __str__(self):
        return f"{self.assessment.title} - Q{self.order}"


class StudentAssessmentSubmission(TimestampedModel):
    """
    Student attempt and score record for an assessment.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="assessment_submissions",
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.CASCADE,
        related_name="assessment_submissions",
    )
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=SUBMISSION_STATUS_CHOICES,
        default=SUBMISSION_STATUS_IN_PROGRESS,
    )
    auto_marked_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    manual_marked_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    is_passed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Student Assessment Submission"
        verbose_name_plural = "Student Assessment Submissions"
        ordering = ["-submitted_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "student"],
                name="unique_student_assessment_submission",
            )
        ]

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.assessment.title}: {self.total_score}/{self.assessment.total_marks}"


class StudentAssessmentAnswer(TimestampedModel):
    """
    Individual answer submitted by a student for a question in an assessment.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        StudentAssessmentSubmission,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="student_answers",
    )
    selected_option = models.ForeignKey(
        QuestionOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_answers",
    )
    essay_response = models.TextField(blank=True, default="")
    is_correct = models.BooleanField(null=True, blank=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    feedback = models.TextField(blank=True, default="")
    marked_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_answers",
    )

    class Meta:
        verbose_name = "Student Answer"
        verbose_name_plural = "Student Answers"
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "question"],
                name="unique_submission_question_answer",
            )
        ]

    def __str__(self):
        return f"Answer for Q: {self.question_id} - Marks: {self.marks_awarded}"
