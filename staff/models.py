"""
Staff data models.

Covers staff profiles and institutional employment details for school tenants.
Users connect to schools via accounts.SchoolMembership, and their detailed
staff record (qualifications, employment date, title, designation) lives in StaffProfile.
"""
from django.db import models
from core.models import TimestampedUUIDModel

GENDER_MALE = "male"
GENDER_FEMALE = "female"
GENDER_CHOICES = [
    (GENDER_MALE, "Male"),
    (GENDER_FEMALE, "Female"),
]

EMPLOYMENT_FULL_TIME = "full_time"
EMPLOYMENT_PART_TIME = "part_time"
EMPLOYMENT_CONTRACT = "contract"
EMPLOYMENT_NYSC = "nysc"
EMPLOYMENT_TYPE_CHOICES = [
    (EMPLOYMENT_FULL_TIME, "Full-Time"),
    (EMPLOYMENT_PART_TIME, "Part-Time"),
    (EMPLOYMENT_CONTRACT, "Contract"),
    (EMPLOYMENT_NYSC, "NYSC Corps Member"),
]

STAFF_DOC_CV = "cv"
STAFF_DOC_DEGREE = "degree_certificate"
STAFF_DOC_TRCN = "trcn_certificate"
STAFF_DOC_NYSC = "nysc_certificate"
STAFF_DOC_NIN = "nin_slip"
STAFF_DOC_BIRTH = "birth_certificate"
STAFF_DOC_GUARANTOR = "guarantor_form"
STAFF_DOC_MEDICAL = "medical_fitness"
STAFF_DOC_OTHER = "other"

STAFF_DOC_TYPE_CHOICES = [
    (STAFF_DOC_DEGREE, "Academic Qualification (NCE / B.Ed / B.Sc / M.Ed / PGDE)"),
    (STAFF_DOC_TRCN, "TRCN Certificate / License"),
    (STAFF_DOC_NYSC, "NYSC Discharge / Exemption Certificate"),
    (STAFF_DOC_CV, "Curriculum Vitae (CV / Resume)"),
    (STAFF_DOC_NIN, "National Identification Number (NIN Slip)"),
    (STAFF_DOC_BIRTH, "Birth Certificate / Age Declaration"),
    (STAFF_DOC_GUARANTOR, "Guarantor Form"),
    (STAFF_DOC_MEDICAL, "Medical Fitness Certificate"),
    (STAFF_DOC_OTHER, "Other Supporting Credential"),
]


class StaffProfile(TimestampedUUIDModel):
    """
    Detailed employment and professional profile of a staff member at a school.
    One per user per school tenant.
    """

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="staff_profiles",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="staff_profiles",
    )
    title = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="e.g. Mr., Mrs., Dr., Pastor, Engr., Alh.",
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        default="",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    date_employed = models.DateField(null=True, blank=True)
    qualification = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="e.g. B.Ed, B.Sc, N.C.E, M.Ed, HND, PGDE",
    )
    specialization = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="e.g. Mathematics, English Language, Physics",
    )
    designation = models.CharField(
        max_length=100,
        blank=True,
        default="Teaching Staff",
        help_text="e.g. Class Teacher, Subject Teacher, Bursar, Vice Principal Academic",
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default=EMPLOYMENT_FULL_TIME,
    )
    trcn_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Teachers Registration Council of Nigeria (TRCN) number.",
    )
    nin = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="11-digit National Identification Number (NIN).",
    )
    assigned_subjects = models.ManyToManyField(
        "academics.Subject",
        blank=True,
        related_name="qualified_staff",
        help_text="Subjects this staff member is assigned/qualified to teach.",
    )
    residential_address = models.TextField(blank=True, default="")
    next_of_kin_name = models.CharField(max_length=120, blank=True, default="")
    next_of_kin_phone = models.CharField(max_length=30, blank=True, default="")
    next_of_kin_relationship = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"
        ordering = ["user__last_name", "user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "user"],
                name="unique_school_staff_profile",
            )
        ]

    def __str__(self):
        full_title = f"{self.title} " if self.title else ""
        return f"{full_title}{self.user.get_full_name()} ({self.user.username}) — {self.school.name}"


# ==============================================================================
# StaffAttendance
# ==============================================================================

STAFF_ATTENDANCE_PRESENT = "present"
STAFF_ATTENDANCE_ABSENT = "absent"
STAFF_ATTENDANCE_LATE = "late"
STAFF_ATTENDANCE_EXCUSED = "excused"
STAFF_ATTENDANCE_ON_LEAVE = "on_leave"

STAFF_ATTENDANCE_CHOICES = [
    (STAFF_ATTENDANCE_PRESENT, "Present"),
    (STAFF_ATTENDANCE_ABSENT, "Absent"),
    (STAFF_ATTENDANCE_LATE, "Late"),
    (STAFF_ATTENDANCE_EXCUSED, "Excused"),
    (STAFF_ATTENDANCE_ON_LEAVE, "On Leave"),
]


class StaffAttendance(TimestampedUUIDModel):
    """
    Daily attendance record for school staff members.
    Marked by Principal, Vice Principal, or School Director.
    """

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="staff_attendances",
    )
    staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=STAFF_ATTENDANCE_CHOICES,
        default=STAFF_ATTENDANCE_PRESENT,
    )
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    marked_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_staff_attendances",
    )
    remarks = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Staff Attendance"
        verbose_name_plural = "Staff Attendances"
        ordering = ["-date", "staff__user__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "staff", "date"],
                name="unique_staff_daily_attendance",
            )
        ]
        indexes = [
            models.Index(fields=["school", "date"]),
        ]

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.date}: {self.get_status_display()}"


class StaffDocument(TimestampedUUIDModel):
    """
    Qualification certificates and employment onboarding documents for staff.
    """
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="staff_documents",
    )
    staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=40,
        choices=STAFF_DOC_TYPE_CHOICES,
        default=STAFF_DOC_DEGREE,
    )
    file = models.FileField(upload_to="staff/documents/")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Staff Document"
        verbose_name_plural = "Staff Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.staff.user.get_full_name()}"
