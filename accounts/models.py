"""
Accounts data models.

Custom User model supporting username as institutional ID (e.g., GS-STF-0001, GS-STD-0001)
and multi-school membership via SchoolMembership.
"""
import uuid
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.utils import timezone
from core.models import TimestampedModel
from core.storage import upload_user_avatar
from core.constants import (
    SCHOOL_ROLES,
    MEMBERSHIP_STATUS_CHOICES,
    MEMBERSHIP_ACTIVE,
    ROLE_PLATFORM_DEVELOPER,
)


class UserManager(BaseUserManager):
    """Manager for custom user model."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The username field is required.")
        email = self.normalize_email(email) if email else None
        user = self.model(username=username.strip().upper(), email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_platform_developer", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    """
    Custom user model for EduFlow.

    The username acts as the human-readable identifier and institutional ID.
    E.g. GS-STF-0001 (Staff at Green School), GS-STD-0001 (Student at Green School).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique institutional or system username (uppercase).",
    )
    email = models.EmailField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
    )

    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    middle_name = models.CharField(max_length=60, blank=True, default="")

    avatar = models.ImageField(upload_to=upload_user_avatar, null=True, blank=True)

    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the Django admin site.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user account should be treated as active.",
    )
    is_platform_developer = models.BooleanField(
        default=False,
        help_text="Designates whether this user is an authorized platform administrator.",
    )

    date_joined = models.DateTimeField(default=timezone.now)
    last_active_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        full_name = self.get_full_name()
        return f"{self.username} ({full_name})" if full_name else self.username

    def get_full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p).strip()

    def get_short_name(self):
        return self.first_name


class SchoolMembership(TimestampedModel):
    """
    Connects a User to a specific School with a specific Role.

    Supports multi-school membership: one User record may belong to
    multiple schools with independent roles, statuses, and permissions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=30, choices=SCHOOL_ROLES)
    status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_STATUS_CHOICES,
        default=MEMBERSHIP_ACTIVE,
        db_index=True,
    )
    id_number = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="School-assigned identification / badge number.",
    )
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "School Membership"
        verbose_name_plural = "School Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "school", "role"],
                name="unique_user_school_role",
            )
        ]
        indexes = [
            models.Index(fields=["school", "role", "status"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} @ {self.school.name}"

    @property
    def is_active(self):
        return self.status == MEMBERSHIP_ACTIVE


# ==============================================================================
# Parent-Student Relationship
# ==============================================================================

RELATIONSHIP_FATHER = "father"
RELATIONSHIP_MOTHER = "mother"
RELATIONSHIP_GUARDIAN = "guardian"
RELATIONSHIP_SPONSOR = "sponsor"
RELATIONSHIP_OTHER = "other"

RELATIONSHIP_CHOICES = [
    (RELATIONSHIP_FATHER, "Father"),
    (RELATIONSHIP_MOTHER, "Mother"),
    (RELATIONSHIP_GUARDIAN, "Guardian"),
    (RELATIONSHIP_SPONSOR, "Sponsor"),
    (RELATIONSHIP_OTHER, "Other"),
]


class ParentStudentRelationship(TimestampedModel):
    """
    Connects a Parent/Guardian user to a StudentProfile within a School.
    Enables parents to track multiple children, view results, and monitor attendance.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="parent_student_relationships",
    )
    parent = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="student_relationships",
    )
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.CASCADE,
        related_name="parent_relationships",
    )
    relationship_type = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES,
        default=RELATIONSHIP_GUARDIAN,
    )
    is_primary_contact = models.BooleanField(default=False)
    is_emergency_contact = models.BooleanField(default=True)
    can_view_results = models.BooleanField(default=True)
    can_view_attendance = models.BooleanField(default=True)
    can_view_finances = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Parent-Student Relationship"
        verbose_name_plural = "Parent-Student Relationships"
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "student"],
                name="unique_parent_student_relationship",
            )
        ]

    def __str__(self):
        return f"{self.parent.get_full_name()} ({self.get_relationship_type_display()}) -> {self.student.user.get_full_name()}"
