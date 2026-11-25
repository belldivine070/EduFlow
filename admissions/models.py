"""
Admissions data models.

Supports:
- Public admission applications scoped to tenant.
- Applicant biodata and parent/guardian information.
- Document submissions (birth certificate, transcript/report, photo, etc.).
- Application review, interview scheduling, admission decisions.
- Official printable admission letter.
- Direct conversion of admitted applicant into student account, enrollment, and parent linking.
"""
import uuid
from django.db import models
from django.utils import timezone
from core.models import TimestampedModel
from core.constants import GENDER_CHOICES

APPLICATION_STATUS_PENDING = "pending"
APPLICATION_STATUS_UNDER_REVIEW = "under_review"
APPLICATION_STATUS_INTERVIEW_SCHEDULED = "interview_scheduled"
APPLICATION_STATUS_ADMITTED = "admitted"
APPLICATION_STATUS_REJECTED = "rejected"
APPLICATION_STATUS_ENROLLED = "enrolled"

APPLICATION_STATUS_CHOICES = [
    (APPLICATION_STATUS_PENDING, "Pending"),
    (APPLICATION_STATUS_UNDER_REVIEW, "Under Review"),
    (APPLICATION_STATUS_INTERVIEW_SCHEDULED, "Interview Scheduled"),
    (APPLICATION_STATUS_ADMITTED, "Admitted"),
    (APPLICATION_STATUS_REJECTED, "Rejected"),
    (APPLICATION_STATUS_ENROLLED, "Enrolled as Student"),
]

DOCUMENT_TYPE_BIRTH_CERTIFICATE = "birth_certificate"
DOCUMENT_TYPE_PREVIOUS_REPORT = "previous_report"
DOCUMENT_TYPE_PASSPORT_PHOTO = "passport_photo"
DOCUMENT_TYPE_MEDICAL_REPORT = "medical_report"
DOCUMENT_TYPE_OTHER = "other"

DOCUMENT_TYPE_CHOICES = [
    (DOCUMENT_TYPE_BIRTH_CERTIFICATE, "Birth Certificate"),
    (DOCUMENT_TYPE_PREVIOUS_REPORT, "Previous Term Report / Transcript"),
    (DOCUMENT_TYPE_PASSPORT_PHOTO, "Passport Photograph"),
    (DOCUMENT_TYPE_MEDICAL_REPORT, "Medical Fitness Report"),
    (DOCUMENT_TYPE_OTHER, "Other Supporting Document"),
]


class AdmissionApplication(TimestampedModel):
    """
    Public student admission application submitted to a specific school tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="admission_applications",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="admission_applications",
        help_text="Academic session applied for.",
    )
    application_number = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Unique application reference (e.g. HS-ADM-2026-0001).",
    )

    # Applicant details
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, blank=True, default="")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="male")
    date_of_birth = models.DateField()
    applying_for_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.CASCADE,
        related_name="admission_applications",
    )
    state_of_origin = models.CharField(max_length=100, blank=True, default="")
    lga = models.CharField(max_length=100, blank=True, default="", verbose_name="LGA of Origin")
    residential_address = models.TextField(blank=True, default="")
    previous_school = models.CharField(max_length=255, blank=True, default="")
    medical_conditions = models.TextField(blank=True, default="")

    # Parent / Guardian details
    parent_name = models.CharField(max_length=200)
    parent_email = models.EmailField(blank=True, default="")
    parent_phone = models.CharField(max_length=32)
    parent_relationship = models.CharField(max_length=64, default="Father")
    parent_address = models.TextField(blank=True, default="")

    # Workflow & Decision
    status = models.CharField(
        max_length=32,
        choices=APPLICATION_STATUS_CHOICES,
        default=APPLICATION_STATUS_PENDING,
        db_index=True,
    )
    interview_date = models.DateTimeField(null=True, blank=True)
    decision_date = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_admission_applications",
    )

    # If applicant is converted to enrolled student
    enrolled_student = models.OneToOneField(
        "academics.StudentProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_application",
    )
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Admission Application"
        verbose_name_plural = "Admission Applications"
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "application_number"],
                name="unique_school_admission_application_number",
            )
        ]

    def __str__(self):
        return f"{self.application_number} - {self.first_name} {self.last_name} ({self.school.code})"

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"


class ApplicationDocument(TimestampedModel):
    """
    Uploaded supporting documents for an admission application.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        AdmissionApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to="admissions/documents/")
    original_filename = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Application Document"
        verbose_name_plural = "Application Documents"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.application.application_number}"
