"""
Accounts service functions.

Encapsulates user creation, institutional username generation,
and membership management.
"""
import re
import secrets
from django.db import transaction
from accounts.models import User, SchoolMembership
from core.exceptions import InvalidUsernameFormatError
from core.constants import (
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
    ROLE_STUDENT,
    ROLE_PARENT,
)

STAFF_ROLES = {
    ROLE_DIRECTOR,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
    ROLE_TEACHING_STAFF,
    ROLE_NON_TEACHING_STAFF,
}

# Regex allowing:
# 1. Staff random numeric ID: 6-8 digits (e.g. 849201)
# 2. Student ID with school prefix: e.g. KHA/2026/0001, GS-STD-0001, EF/2026/042
# 3. Standard alphanumeric/underscore usernames: e.g. dev_admin, bell_divine
USERNAME_PATTERN = re.compile(r"^(?:\d{5,10}|[A-Za-z0-9][A-Za-z0-9/_.-]{2,63})$")


def generate_staff_id() -> str:
    """
    Generate a random numeric staff ID that is guaranteed unique across the entire platform.
    Produces a 6-digit to 7-digit integer (e.g. '839201', '5729104').
    """
    for _ in range(100):
        # Generate random 6-digit or 7-digit number
        candidate = str(secrets.randbelow(9000000) + 1000000)
        if not User.objects.filter(username=candidate).exists():
            return candidate

    # Fallback to 8-digit if high density
    while True:
        candidate = str(secrets.randbelow(90000000) + 10000000)
        if not User.objects.filter(username=candidate).exists():
            return candidate


def generate_student_id(school) -> str:
    """
    Generate the next student ID using the school's configured prefix.
    Default prefix: '<CODE>-STD-' (e.g. 'GS-STD-') or school custom prefix (e.g. 'KHA/2026/').
    Appends a 4-digit sequential zero-padded number (e.g. 'KHA/2026/0001').
    """
    prefix = (school.student_id_prefix or f"{school.code}-STD-").strip().upper()

    # Query latest student username matching this prefix
    last_user = (
        User.objects
        .filter(username__startswith=prefix)
        .order_by("-username")
        .values_list("username", flat=True)
        .first()
    )

    if last_user and len(last_user) > len(prefix):
        suffix = last_user[len(prefix):]
        # Extract trailing digits
        digits = re.findall(r"\d+", suffix)
        if digits:
            next_seq = int(digits[-1]) + 1
        else:
            next_seq = User.objects.filter(username__startswith=prefix).count() + 1
    else:
        next_seq = 1

    candidate = f"{prefix}{next_seq:04d}"

    # Ensure uniqueness in case of gaps or manual imports
    while User.objects.filter(username=candidate).exists():
        next_seq += 1
        candidate = f"{prefix}{next_seq:04d}"

    return candidate


def generate_username(school_code: str, role_prefix: str) -> str:
    """
    Legacy helper: Generate sequential institutional username for a school.
    Kept for backward compatibility.
    """
    school_code = school_code.strip().upper()
    role_prefix = role_prefix.strip().upper()
    prefix = f"{school_code}-{role_prefix}-"

    last_user = (
        User.objects
        .filter(username__startswith=prefix)
        .order_by("-username")
        .values_list("username", flat=True)
        .first()
    )

    if last_user:
        try:
            last_seq = int(last_user[len(prefix):])
            next_seq = last_seq + 1
        except ValueError:
            next_seq = User.objects.filter(username__startswith=prefix).count() + 1
    else:
        next_seq = 1

    candidate = f"{prefix}{next_seq:04d}"
    while User.objects.filter(username=candidate).exists():
        next_seq += 1
        candidate = f"{prefix}{next_seq:04d}"

    return candidate


def validate_username_format(username: str) -> None:
    """Validate that a username matches platform format (numeric staff ID, student ID with prefix, or alphanumeric)."""
    cleaned = username.strip()
    if not USERNAME_PATTERN.match(cleaned):
        raise InvalidUsernameFormatError(
            f"Username '{username}' does not conform to the expected format (e.g. 748291, KHA/2026/0001, or dev_admin)."
        )


@transaction.atomic
def create_school_user(
    *,
    school,
    role: str,
    first_name: str,
    last_name: str,
    middle_name: str = "",
    email: str = None,
    phone_number: str = None,
    password: str = None,
    custom_username: str = None,
) -> tuple[User, SchoolMembership]:
    """
    Create a new user with an institutional ID username and assign their school membership.
    
    ID Generation rules:
    - Staff (Director, Principal, Teacher, Non-Teaching): unique random number across platform.
    - Student: school-configured prefix + sequential number (e.g. KHA/2026/0001).
    - Custom username: allowed when explicitly provided (e.g. platform admin or legacy import).
    """
    if custom_username:
        validate_username_format(custom_username)
        username = custom_username.strip().upper()
    elif role == ROLE_STUDENT:
        username = generate_student_id(school)
    elif role in STAFF_ROLES:
        username = generate_staff_id()
    else:
        # Parents or other roles
        prefix = f"{school.code}-PAR-"
        username = generate_username(school.code, "PAR")

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        phone_number=phone_number,
    )

    membership = SchoolMembership.objects.create(
        user=user,
        school=school,
        role=role,
        id_number=username,
    )

    return user, membership


@transaction.atomic
def link_parent_to_student(
    *,
    school,
    parent: User,
    student,
    relationship_type: str = "guardian",
    is_primary_contact: bool = False,
    is_emergency_contact: bool = True,
    can_view_results: bool = True,
    can_view_attendance: bool = True,
    can_view_finances: bool = True,
):
    """
    Link a parent/guardian user to a student profile.
    """
    from accounts.models import ParentStudentRelationship

    rel, _ = ParentStudentRelationship.objects.update_or_create(
        parent=parent,
        student=student,
        defaults={
            "school": school,
            "relationship_type": relationship_type,
            "is_primary_contact": is_primary_contact,
            "is_emergency_contact": is_emergency_contact,
            "can_view_results": can_view_results,
            "can_view_attendance": can_view_attendance,
            "can_view_finances": can_view_finances,
        },
    )
    return rel
