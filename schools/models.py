"""
Schools data models.

School tenant registry, verified domains for host-based routing,
and centralized AppVariable key-value configuration.
"""
import uuid
from django.db import models
from django.utils.text import slugify
from core.models import TimestampedModel
from core.storage import upload_school_logo


class School(TimestampedModel):
    """
    Central tenant registry.
    All tenant-scoped records connect back to this model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Full official name of the school.")
    code = models.CharField(
        max_length=8,
        unique=True,
        db_index=True,
        help_text="Short uppercase code used for ID prefixes (e.g., GS, BSC, KING).",
    )
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    motto = models.CharField(max_length=255, blank=True, default="")
    logo = models.ImageField(upload_to=upload_school_logo, null=True, blank=True)
    student_id_prefix = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Custom student ID prefix set by the school (e.g. KHA/2026/ or GS-STD-).",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Controls whether the school is active on the SaaS platform.",
    )

    class Meta:
        verbose_name = "School"
        verbose_name_plural = "Schools"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.student_id_prefix:
            self.student_id_prefix = f"{self.code}-STD-"
        super().save(*args, **kwargs)


class SchoolDomain(TimestampedModel):
    """
    Domain resolution mapping for tenants.
    A request hostname is matched against verified and active domains.
    """

    DOMAIN_SUBDOMAIN = "subdomain"
    DOMAIN_CUSTOM = "custom"

    DOMAIN_TYPE_CHOICES = [
        (DOMAIN_SUBDOMAIN, "SaaS Subdomain"),
        (DOMAIN_CUSTOM, "Custom Domain"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="domains",
    )
    domain = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Normalized lowercase domain or subdomain (e.g., green.yoursaas.com).",
    )
    domain_type = models.CharField(
        max_length=20,
        choices=DOMAIN_TYPE_CHOICES,
        default=DOMAIN_SUBDOMAIN,
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Designates this domain as the primary domain for the school.",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Designates whether the domain ownership has been verified.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Controls whether traffic to this domain resolves to the school.",
    )

    class Meta:
        verbose_name = "School Domain"
        verbose_name_plural = "School Domains"
        ordering = ["-is_primary", "domain"]

    def __str__(self):
        return f"{self.domain} -> {self.school.name}"

    def save(self, *args, **kwargs):
        self.domain = self.domain.strip().lower()
        if self.is_primary:
            # Ensure only one primary domain per school
            SchoolDomain.objects.filter(school=self.school, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class AppVariable(models.Model):
    """
    Centralized key-value configuration system for school and platform settings.
    - school=None represents a platform-wide setting.
    - school=<School> represents a school-specific configuration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        School,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="variables",
        help_text="Associated school tenant, or null for platform-level setting.",
    )
    var_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Setting key name in uppercase (e.g., SCHOOL_NAME, TET_WEIGHT).",
    )
    var_value = models.TextField(help_text="Stored configuration value.")
    description = models.TextField(blank=True, default="")
    isreadonly = models.BooleanField(
        default=False,
        help_text="If true, cannot be modified via standard school settings UI.",
    )
    lastupdated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
        constraints = [
            models.UniqueConstraint(
                fields=["school", "var_name"],
                name="unique_school_var_name",
            )
        ]

    def __str__(self):
        scope = self.school.code if self.school else "PLATFORM"
        return f"[{scope}] {self.var_name}"

    def save(self, *args, **kwargs):
        self.var_name = self.var_name.strip().upper()
        super().save(*args, **kwargs)


def get_setting(name: str, school=None, default=""):
    """
    Retrieve setting value for a school, falling back to platform setting, then default.
    """
    name = name.strip().upper()
    if school:
        val = AppVariable.objects.filter(school=school, var_name=name).values_list("var_value", flat=True).first()
        if val is not None:
            return val

    # Platform-level fallback
    val = AppVariable.objects.filter(school__isnull=True, var_name=name).values_list("var_value", flat=True).first()
    return val if val is not None else default
