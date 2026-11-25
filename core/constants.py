"""
Platform-wide constants.

The Nigerian school class catalogue is defined here and used by the
academics seeding service when a new school is created.
"""

# ==============================================================================
# School sections and their display order
# ==============================================================================
SECTION_PRIMARY = "primary"
SECTION_JSS = "jss"
SECTION_SSS = "sss"

SECTION_CHOICES = [
    (SECTION_PRIMARY, "Primary"),
    (SECTION_JSS, "Junior Secondary School"),
    (SECTION_SSS, "Senior Secondary School"),
]

# ==============================================================================
# Standard Nigerian school class catalogue
# Seeded automatically on school creation (all active by default).
# Schools deactivate classes they do not offer.
# ==============================================================================
NIGERIAN_CLASS_CATALOGUE = [
    # (section_key, class_name, order)
    (SECTION_PRIMARY, "Primary 1", 1),
    (SECTION_PRIMARY, "Primary 2", 2),
    (SECTION_PRIMARY, "Primary 3", 3),
    (SECTION_PRIMARY, "Primary 4", 4),
    (SECTION_PRIMARY, "Primary 5", 5),
    (SECTION_PRIMARY, "Primary 6", 6),
    (SECTION_JSS, "JSS 1", 7),
    (SECTION_JSS, "JSS 2", 8),
    (SECTION_JSS, "JSS 3", 9),
    (SECTION_SSS, "SSS 1", 10),
    (SECTION_SSS, "SSS 2", 11),
    (SECTION_SSS, "SSS 3", 12),
]

# ==============================================================================
# Username prefix scheme
# Format: SCHOOL_CODE-ROLE_PREFIX-SEQUENCE (e.g. GS-STF-0001)
# ==============================================================================
USERNAME_PREFIX_DIRECTOR = "DIR"
USERNAME_PREFIX_STAFF = "STF"
USERNAME_PREFIX_STUDENT = "STD"
USERNAME_PREFIX_PARENT = "PAR"

# ==============================================================================
# School roles (seeded per school on creation)
# ==============================================================================
ROLE_PLATFORM_DEVELOPER = "platform_developer"
ROLE_DIRECTOR = "director"
ROLE_PRINCIPAL = "principal"
ROLE_VICE_PRINCIPAL = "vice_principal"
ROLE_TEACHING_STAFF = "teaching_staff"
ROLE_NON_TEACHING_STAFF = "non_teaching_staff"
ROLE_PARENT = "parent"
ROLE_STUDENT = "student"

SCHOOL_ROLES = [
    (ROLE_DIRECTOR, "School Director"),
    (ROLE_PRINCIPAL, "Principal"),
    (ROLE_VICE_PRINCIPAL, "Vice Principal"),
    (ROLE_TEACHING_STAFF, "Teaching Staff"),
    (ROLE_NON_TEACHING_STAFF, "Non-Teaching Staff"),
    (ROLE_PARENT, "Parent / Guardian"),
    (ROLE_STUDENT, "Student"),
]

# ==============================================================================
# Membership status
# ==============================================================================
MEMBERSHIP_ACTIVE = "active"
MEMBERSHIP_INACTIVE = "inactive"
MEMBERSHIP_SUSPENDED = "suspended"

MEMBERSHIP_STATUS_CHOICES = [
    (MEMBERSHIP_ACTIVE, "Active"),
    (MEMBERSHIP_INACTIVE, "Inactive"),
    (MEMBERSHIP_SUSPENDED, "Suspended"),
]

# ==============================================================================
# Assessment weighting defaults
# ==============================================================================
DEFAULT_TET_WEIGHT = 30   # 30%
DEFAULT_EXAM_WEIGHT = 70  # 70%

# ==============================================================================
# Default grading scale (school-configurable via AppVariable)
# ==============================================================================
DEFAULT_GRADE_SCALE = [
    (70, 100, "A"),
    (60, 69,  "B"),
    (50, 59,  "C"),
    (40, 49,  "D"),
    (0,  39,  "E"),
]

# ==============================================================================
# Pagination
# ==============================================================================
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

# ==============================================================================
# AppVariable scope keys
# ==============================================================================
# Platform-level settings stored with school=None
PLATFORM_SETTINGS = {
    "PLATFORM_NAME",
    "PLATFORM_EMAIL",
    "PLATFORM_SUPPORT_EMAIL",
    "PLATFORM_LOGO",
}

# Common school-level AppVariable keys
SCHOOL_SETTING_KEYS = {
    "SCHOOL_NAME",
    "SCHOOL_MOTTO",
    "SCHOOL_LOGO",
    "PRIMARY_COLOR",
    "SECONDARY_COLOR",
    "OFFICIAL_EMAIL",
    "SCHOOL_PHONE",
    "SCHOOL_ADDRESS",
    "CONTACT_PERSON1",
    "ADMISSION_EMAIL",
    "CURRENT_SESSION",
    "CURRENT_TERM",
    "TET_WEIGHT",
    "EXAM_WEIGHT",
    "SCHOOL_TEMPLATE",
}

# ==============================================================================
# Student Enrollment Status
# ==============================================================================
ENROLLMENT_ACTIVE = "active"
ENROLLMENT_PROMOTED = "promoted"
ENROLLMENT_REPEATED = "repeated"
ENROLLMENT_GRADUATED = "graduated"
ENROLLMENT_TRANSFERRED = "transferred"
ENROLLMENT_WITHDRAWN = "withdrawn"

ENROLLMENT_STATUS_CHOICES = [
    (ENROLLMENT_ACTIVE, "Active"),
    (ENROLLMENT_PROMOTED, "Promoted"),
    (ENROLLMENT_REPEATED, "Repeated"),
    (ENROLLMENT_GRADUATED, "Graduated"),
    (ENROLLMENT_TRANSFERRED, "Transferred"),
    (ENROLLMENT_WITHDRAWN, "Withdrawn"),
]

# ==============================================================================
# Gender, Blood Group & Genotype
# ==============================================================================
GENDER_MALE = "male"
GENDER_FEMALE = "female"

GENDER_CHOICES = [
    (GENDER_MALE, "Male"),
    (GENDER_FEMALE, "Female"),
]

BLOOD_GROUP_CHOICES = [
    ("A+", "A+"),
    ("A-", "A-"),
    ("B+", "B+"),
    ("B-", "B-"),
    ("AB+", "AB+"),
    ("AB-", "AB-"),
    ("O+", "O+"),
    ("O-", "O-"),
]

GENOTYPE_CHOICES = [
    ("AA", "AA"),
    ("AS", "AS"),
    ("SS", "SS"),
    ("AC", "AC"),
]

# Template allowlist — only these values may be used as template folder keys
ALLOWED_SCHOOL_TEMPLATES = {"default", "acumen", "blale-international-school", "heritage-school"}
