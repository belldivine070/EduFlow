"""
Academics data models.

Covers the full academic hierarchy for each school tenant:
- Section         → Primary / JSS / SSS groupings
- SchoolClass     → e.g. Primary 1, JSS 2, SSS 3  (seeded per school, deactivatable)
- ClassArm        → Subdivisions within a class  e.g. A, B, Gold
- AcademicSession → e.g. 2025/2026 school year
- Term            → First, Second, or Third term within a session
"""
import uuid
from django.db import models
from django.utils import timezone
from core.models import TimestampedModel
from core.constants import (
    SECTION_CHOICES,
    SECTION_PRIMARY,
    GENDER_CHOICES,
    BLOOD_GROUP_CHOICES,
    GENOTYPE_CHOICES,
    ENROLLMENT_STATUS_CHOICES,
    ENROLLMENT_ACTIVE,
)


# ==============================================================================
# Section
# ==============================================================================

class Section(TimestampedModel):
    """
    Academic section within a school (Primary, JSS, SSS).
    One per section type per school.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="sections",
    )
    section_type = models.CharField(
        max_length=20,
        choices=SECTION_CHOICES,
        default=SECTION_PRIMARY,
    )
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ["school", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "section_type"],
                name="unique_school_section_type",
            )
        ]

    def __str__(self):
        return f"{self.name} — {self.school.name}"


# ==============================================================================
# SchoolClass
# ==============================================================================

class SchoolClass(TimestampedModel):
    """
    Standard Nigerian school class (e.g. Primary 1, JSS 1, SSS 3).

    Seeded automatically with is_active=True when a school is registered.
    Schools can deactivate classes they do not offer (e.g. a school without
    Primary 6 sets it inactive — it disappears from all operational views).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="classes",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="classes",
    )
    name = models.CharField(max_length=60, help_text="e.g. Primary 1, JSS 1, SSS 3")
    order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive classes are not offered by the school and hidden from operations.",
    )

    class Meta:
        verbose_name = "School Class"
        verbose_name_plural = "School Classes"
        ordering = ["school", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"],
                name="unique_school_class_name",
            )
        ]

    def __str__(self):
        return f"{self.name} — {self.school.name}"


# ==============================================================================
# ClassArm
# ==============================================================================

class ClassArm(TimestampedModel):
    """
    Arm or subdivision of a class (e.g. A, B, Gold, Diamond).
    Schools create arms as needed; there is no default seeding.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="class_arms",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="arms",
    )
    name = models.CharField(max_length=40, help_text="e.g. A, B, Gold, Blue")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Class Arm"
        verbose_name_plural = "Class Arms"
        ordering = ["school_class", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "name"],
                name="unique_class_arm_name",
            )
        ]

    def __str__(self):
        return f"{self.school_class.name} {self.name} — {self.school.name}"


# ==============================================================================
# AcademicSession
# ==============================================================================

class AcademicSession(TimestampedModel):
    """
    A school year (academic session), e.g. '2025/2026'.

    Only one session may be current at a time per school.
    When a new session is set as current, the previous one is automatically
    unmarked via the save() override below.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    name = models.CharField(
        max_length=20,
        help_text="e.g. 2025/2026",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(
        default=False,
        help_text="Marks the active academic session for this school.",
    )

    class Meta:
        verbose_name = "Academic Session"
        verbose_name_plural = "Academic Sessions"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"],
                name="unique_school_session_name",
            )
        ]

    def __str__(self):
        marker = " [Current]" if self.is_current else ""
        return f"{self.name}{marker} — {self.school.name}"

    def save(self, *args, **kwargs):
        # Enforce only one current session per school
        if self.is_current:
            AcademicSession.objects.filter(
                school=self.school, is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


# ==============================================================================
# Term
# ==============================================================================

TERM_FIRST = "first"
TERM_SECOND = "second"
TERM_THIRD = "third"

TERM_CHOICES = [
    (TERM_FIRST,  "First Term"),
    (TERM_SECOND, "Second Term"),
    (TERM_THIRD,  "Third Term"),
]


class Term(TimestampedModel):
    """
    One of the three school terms within an academic session.

    Only one term may be current at a time per school.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="terms",
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name="terms",
    )
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(
        default=False,
        help_text="Marks the active term for this school.",
    )

    class Meta:
        verbose_name = "Term"
        verbose_name_plural = "Terms"
        ordering = ["-session__start_date", "term"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "term"],
                name="unique_session_term",
            )
        ]

    def __str__(self):
        label = dict(TERM_CHOICES).get(self.term, self.term)
        marker = " [Current]" if self.is_current else ""
        return f"{label}{marker} — {self.session.name} — {self.school.name}"

    def save(self, *args, **kwargs):
        # Enforce only one current term per school at a time
        if self.is_current:
            Term.objects.filter(
                school=self.school, is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return dict(TERM_CHOICES).get(self.term, self.term)


# ==============================================================================
# Subject
# ==============================================================================

class Subject(TimestampedModel):
    """
    Academic subject offered by a school (e.g. Mathematics, English Language, Physics).
    Belongs to a school tenant and can be offered to specific classes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="subjects",
    )
    name = models.CharField(max_length=100, help_text="e.g. Mathematics, English Language")
    code = models.CharField(max_length=20, help_text="Short uppercase code, e.g. MTH, ENG, PHY")
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subjects",
        help_text="Primary, JSS, or SSS section this subject belongs to.",
    )
    applicable_classes = models.ManyToManyField(
        SchoolClass,
        blank=True,
        related_name="subjects",
        help_text="Classes offering this subject.",
    )
    is_elective = models.BooleanField(
        default=False,
        help_text="If True, this is an optional/elective subject rather than compulsory core.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "code"],
                name="unique_school_subject_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code}) — {self.school.name}"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


# ==============================================================================
# StudentProfile
# ==============================================================================

class StudentProfile(TimestampedModel):
    """
    Student biodata and institution-level profile.
    Linked to the central user record (which holds username, names, password, etc.).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="students",
    )
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    admission_number = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Institutional student ID matching the user's login username.",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="male")
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True, default="")
    genotype = models.CharField(max_length=5, choices=GENOTYPE_CHOICES, blank=True, default="")
    state_of_origin = models.CharField(max_length=100, blank=True, default="")
    lga = models.CharField(max_length=100, blank=True, default="", verbose_name="LGA of Origin")
    residential_address = models.TextField(blank=True, default="")

    # Emergency & Parent/Guardian contact details
    emergency_contact_name = models.CharField(max_length=120, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=30, blank=True, default="")
    emergency_contact_relationship = models.CharField(max_length=60, blank=True, default="")

    medical_conditions = models.TextField(blank=True, default="", help_text="Allergies, chronic conditions, etc.")
    nin = models.CharField(max_length=20, blank=True, default="", help_text="Student NIN (optional).")
    previous_school = models.CharField(max_length=255, blank=True, default="", help_text="Previous school attended (for transfers).")
    admission_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        ordering = ["user__last_name", "user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "admission_number"],
                name="unique_school_student_admission_number",
            )
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.admission_number}) — {self.school.name}"

    @property
    def current_enrollment(self):
        """Returns the most recent active enrollment."""
        return self.enrollments.filter(status=ENROLLMENT_ACTIVE).select_related(
            "school_class", "class_arm", "session"
        ).first()


STUDENT_DOC_BIRTH = "birth_certificate"
STUDENT_DOC_TRANSFER = "transfer_certificate"
STUDENT_DOC_REPORT = "previous_report"
STUDENT_DOC_MEDICAL = "medical_report"
STUDENT_DOC_PASSPORT = "passport_photo"
STUDENT_DOC_OTHER = "other"

STUDENT_DOC_TYPE_CHOICES = [
    (STUDENT_DOC_BIRTH, "Birth Certificate"),
    (STUDENT_DOC_TRANSFER, "Transfer Certificate / Testimonial"),
    (STUDENT_DOC_REPORT, "Previous Term Report Card"),
    (STUDENT_DOC_MEDICAL, "Medical Fitness / Immunization Record"),
    (STUDENT_DOC_PASSPORT, "Passport Photograph"),
    (STUDENT_DOC_OTHER, "Other Supporting Document"),
]


class StudentDocument(TimestampedModel):
    """
    Registration and onboarding documents submitted for a student.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="student_documents",
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=40,
        choices=STUDENT_DOC_TYPE_CHOICES,
        default=STUDENT_DOC_BIRTH,
    )
    file = models.FileField(upload_to="students/documents/")
    original_filename = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Student Document"
        verbose_name_plural = "Student Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.student.admission_number}"


# ==============================================================================
# StudentEnrollment
# ==============================================================================

class StudentEnrollment(TimestampedModel):
    """
    Tracks a student's placement in a specific SchoolClass and optional ClassArm
    for a given AcademicSession. Enables session-by-session academic history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    class_arm = models.ForeignKey(
        ClassArm,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollments",
    )
    status = models.CharField(
        max_length=20,
        choices=ENROLLMENT_STATUS_CHOICES,
        default=ENROLLMENT_ACTIVE,
    )
    enrolled_at = models.DateField(default=timezone.now)

    class Meta:
        verbose_name = "Student Enrollment"
        verbose_name_plural = "Student Enrollments"
        ordering = ["-session__start_date", "school_class__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "session"],
                name="unique_student_session_enrollment",
            )
        ]

    def __str__(self):
        arm_label = f" {self.class_arm.name}" if self.class_arm else ""
        return f"{self.student.admission_number}: {self.school_class.name}{arm_label} ({self.session.name})"


# ==============================================================================
# TeachingAssignment
# ==============================================================================

class TeachingAssignment(TimestampedModel):
    """
    Session-aware assignment linking a teacher to a subject, class, and optional arm.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    teacher = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    class_arm = models.ForeignKey(
        ClassArm,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="teaching_assignments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Teaching Assignment"
        verbose_name_plural = "Teaching Assignments"
        ordering = ["session", "school_class__order", "subject__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "subject", "school_class", "class_arm"],
                name="unique_teaching_assignment_arm",
            )
        ]

    def __str__(self):
        arm = f" ({self.class_arm.name})" if self.class_arm else ""
        return f"{self.teacher.get_full_name()} — {self.subject.code} in {self.school_class.name}{arm}"


# ==============================================================================
# StudentAttendance
# ==============================================================================

ATTENDANCE_PRESENT = "present"
ATTENDANCE_ABSENT = "absent"
ATTENDANCE_LATE = "late"
ATTENDANCE_EXCUSED = "excused"

ATTENDANCE_STATUS_CHOICES = [
    (ATTENDANCE_PRESENT, "Present"),
    (ATTENDANCE_ABSENT, "Absent"),
    (ATTENDANCE_LATE, "Late"),
    (ATTENDANCE_EXCUSED, "Excused"),
]


class StudentAttendance(TimestampedModel):
    """
    Daily attendance record for a student within an academic session, term, and class arm.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="student_attendances",
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name="student_attendances",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="student_attendances",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="student_attendances",
    )
    class_arm = models.ForeignKey(
        ClassArm,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_attendances",
    )
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES,
        default=ATTENDANCE_PRESENT,
    )
    marked_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_student_attendances",
    )
    remarks = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Student Attendance"
        verbose_name_plural = "Student Attendances"
        ordering = ["-date", "school_class__order", "student__user__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "student", "date"],
                name="unique_student_daily_attendance",
            )
        ]
        indexes = [
            models.Index(fields=["school", "school_class", "date"]),
            models.Index(fields=["school", "session", "term", "date"]),
        ]

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.date}: {self.get_status_display()}"

