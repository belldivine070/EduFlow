"""
Examinations data models.

Covers:
- School-configurable Grading Scales (e.g., A: 70-100, B: 60-69)
- Continuous Assessment + Examination score records (TET: 30%, EXAM: 70%)
- Result approval and multi-step publication workflows
- Termly Student Report Cards with academic performance, class rank, and attendance summary
"""
import uuid
from django.db import models
from django.utils import timezone
from core.models import TimestampedModel


RESULT_STATUS_DRAFT = "draft"
RESULT_STATUS_SUBMITTED = "submitted"
RESULT_STATUS_APPROVED = "approved"
RESULT_STATUS_PUBLISHED = "published"

RESULT_STATUS_CHOICES = [
    (RESULT_STATUS_DRAFT, "Draft (Score Entry)"),
    (RESULT_STATUS_SUBMITTED, "Submitted (Pending Review)"),
    (RESULT_STATUS_APPROVED, "Approved by Principal"),
    (RESULT_STATUS_PUBLISHED, "Published to Students & Parents"),
]


class GradingScale(TimestampedModel):
    """
    Grading boundaries configured per school tenant.
    Default Nigerian secondary school scale:
    - 70 to 100: A (Excellent)
    - 60 to 69:  B (Very Good)
    - 50 to 59:  C (Good / Credit)
    - 40 to 49:  D (Pass)
    - 0 to 39:   E (Fail)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="grading_scales",
    )
    grade = models.CharField(max_length=5)
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    remark = models.CharField(max_length=50, blank=True, default="")
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Grading Scale"
        verbose_name_plural = "Grading Scales"
        ordering = ["-min_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "grade"],
                name="unique_school_grade",
            )
        ]

    def __str__(self):
        return f"{self.grade} ({self.min_score}-{self.max_score}%) - {self.school.name}"


class StudentSubjectResult(TimestampedModel):
    """
    Termly score breakdown for a student in a specific subject.
    Combines Continuous Assessment (TET: 30%) and Final Exam (70%).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    school_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    class_arm = models.ForeignKey(
        "academics.ClassArm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subject_results",
    )

    ca_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Continuous Assessment score (default max 30). Null if pending.",
    )
    exam_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Terminal examination score (default max 70). Null if pending.",
    )
    total_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sum of CA and Exam score (max 100).",
    )
    grade = models.CharField(max_length=5, blank=True, default="")
    teacher_remarks = models.CharField(max_length=255, blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=RESULT_STATUS_CHOICES,
        default=RESULT_STATUS_DRAFT,
    )
    entered_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_results",
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_results",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Student Subject Result"
        verbose_name_plural = "Student Subject Results"
        ordering = ["school_class__order", "student__user__last_name", "subject__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "student", "session", "term", "subject"],
                name="unique_student_term_subject_result",
            )
        ]

    def __str__(self):
        score_display = f"{self.total_score} ({self.grade})" if self.total_score is not None else "Pending"
        return f"{self.student.user.get_full_name()} - {self.subject.code}: {score_display}"

    def calculate_totals(self, grading_scales=None):
        """
        Computes total score and determines grade.
        If either component is missing, marks as pending.
        """
        if self.ca_score is not None and self.exam_score is not None:
            self.total_score = round(float(self.ca_score) + float(self.exam_score), 2)
            # Find matching grade
            if grading_scales:
                for scale in grading_scales:
                    if scale.min_score <= self.total_score <= scale.max_score:
                        self.grade = scale.grade
                        break
            else:
                # Default fallback scale
                ts = self.total_score
                if ts >= 70:
                    self.grade = "A"
                elif ts >= 60:
                    self.grade = "B"
                elif ts >= 50:
                    self.grade = "C"
                elif ts >= 40:
                    self.grade = "D"
                else:
                    self.grade = "E"
        elif self.ca_score is not None:
            self.total_score = self.ca_score
            self.grade = "Pending"
        elif self.exam_score is not None:
            self.total_score = self.exam_score
            self.grade = "Pending"
        else:
            self.total_score = None
            self.grade = "Pending"


class StudentTermReport(TimestampedModel):
    """
    Termly compilation and Report Card for a student.
    Contains aggregated academic performance, rank, attendance summary, and remarks.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="term_reports",
    )
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.CASCADE,
        related_name="term_reports",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="term_reports",
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.CASCADE,
        related_name="term_reports",
    )
    school_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.CASCADE,
        related_name="term_reports",
    )
    class_arm = models.ForeignKey(
        "academics.ClassArm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="term_reports",
    )

    total_subjects = models.PositiveSmallIntegerField(default=0)
    total_obtainable_score = models.DecimalField(max_digits=7, decimal_places=2, default=0.0)
    total_obtained_score = models.DecimalField(max_digits=7, decimal_places=2, default=0.0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    class_size = models.PositiveSmallIntegerField(null=True, blank=True)
    arm_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    arm_size = models.PositiveSmallIntegerField(null=True, blank=True)

    # Attendance summary
    attendance_days_present = models.PositiveSmallIntegerField(default=0)
    attendance_days_absent = models.PositiveSmallIntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)

    class_teacher_remarks = models.TextField(blank=True, default="")
    principal_remarks = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=RESULT_STATUS_CHOICES,
        default=RESULT_STATUS_DRAFT,
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_term_reports",
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Student Term Report"
        verbose_name_plural = "Student Term Reports"
        ordering = ["school_class__order", "-average_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "student", "session", "term"],
                name="unique_student_term_report",
            )
        ]

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.term.get_name_display()} ({self.session.name}): {self.average_score}%"
