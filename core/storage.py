"""
Storage backends and helpers for EduFlow.

Architecture:
- Public storage: Used for school logos, branding assets, avatars, and product images.
  Defaults to media/public/ (or S3/Cloudinary when configured).
- Private storage: Used for student records, admission documents, receipts, etc.
  Defaults to media/private/ (or S3/Cloudinary private bucket with signed URLs).

Cloudinary / S3 Adaptability:
Any model field can use:
    storage=get_public_storage()
    storage=get_private_storage()
This abstracts the physical backend so swapping between Local Disk, AWS S3,
Cloudflare R2, or Cloudinary requires zero changes to models or database schema.
"""
import os
import uuid
from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.utils.deconstruct import deconstructible


class DefaultPublicStorage(FileSystemStorage):
    """
    Public media storage for local development and non-cloud deployments.
    Files are served under media/public/
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", os.path.join(settings.MEDIA_ROOT, "public"))
        kwargs.setdefault("base_url", settings.MEDIA_URL + "public/")
        super().__init__(*args, **kwargs)


class PrivateFileSystemStorage(FileSystemStorage):
    """
    Private media storage for sensitive assets.
    Stored under media/private/ and strictly blocked from public direct URLs.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", os.path.join(settings.MEDIA_ROOT, "private"))
        kwargs.setdefault("base_url", None)
        super().__init__(*args, **kwargs)

    def url(self, name):
        raise ValueError(
            f"Private storage does not support direct public URLs. "
            f"Access to '{name}' must be routed through an authenticated view."
        )


def get_public_storage():
    """Return the configured public storage backend (Local, S3, or Cloudinary)."""
    return storages["default"]


def get_private_storage():
    """Return the configured private storage backend (Local, S3, or Cloudinary Private)."""
    return storages["private"]


# ==============================================================================
# Tenant-aware dynamic upload path helpers
# ==============================================================================

@deconstructible
class TenantUploadPath:
    """
    Callable generator for tenant-isolated upload paths.
    Avoids messy root directories by organizing files cleanly:
    - Public:  public/<category>/<school_code>/<filename>
    - Private: private/<category>/<school_code>/<filename>
    """

    def __init__(self, category: str, is_private: bool = False):
        self.category = category.strip().strip("/")
        self.is_private = is_private

    def __call__(self, instance, filename: str) -> str:
        # Determine school code if instance has school reference
        school = getattr(instance, "school", None)
        if school and hasattr(school, "code"):
            school_folder = school.code.upper()
        elif hasattr(instance, "code"):
            school_folder = instance.code.upper()
        else:
            school_folder = "common"

        # Safe unique filename while preserving extension
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex[:12]}{ext}"

        subfolder = "private" if self.is_private else "public"
        return f"{subfolder}/{self.category}/{school_folder}/{unique_name}"


# Standard upload path callables for models
upload_school_logo = TenantUploadPath("logos", is_private=False)
upload_user_avatar = TenantUploadPath("avatars", is_private=False)
upload_student_document = TenantUploadPath("student_docs", is_private=True)
upload_admission_document = TenantUploadPath("admissions", is_private=True)
