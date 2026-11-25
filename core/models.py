"""
Abstract base models.

All concrete models should extend the appropriate base class.
Do not add foreign keys here — this module must not import from other apps.
"""
import uuid
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """Adds created_at and updated_at to any model."""

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Uses UUID as primary key instead of sequential integer."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedUUIDModel(UUIDModel, TimestampedModel):
    """UUID primary key + timestamps."""

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Soft-delete mixin.

    Records are never physically deleted; they are marked deleted_at.
    Use the ActiveManager as the default manager on concrete models that need soft-delete.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    def soft_delete(self, *, commit: bool = True) -> None:
        self.deleted_at = timezone.now()
        if commit:
            self.save(update_fields=["deleted_at"])

    def restore(self, *, commit: bool = True) -> None:
        self.deleted_at = None
        if commit:
            self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    class Meta:
        abstract = True


class ActiveManager(models.Manager):
    """Returns only records that have not been soft-deleted."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AuditedModel(TimestampedModel):
    """
    Extends timestamps with created_by and updated_by fields.

    The FK to User uses a string reference to avoid circular imports.
    Set related_name on concrete subclasses if multiple audited models
    reference User to avoid clashes.
    """

    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True
