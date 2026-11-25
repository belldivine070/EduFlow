"""
Academics services.

Automated seeding of Nigerian standard classes (Primary 1-6, JSS 1-3, SSS 1-3)
and section management.
"""
from django.db import transaction
from django.utils import timezone
from core.constants import (
    NIGERIAN_CLASS_CATALOGUE,
    SECTION_CHOICES,
    ROLE_STUDENT,
    ENROLLMENT_ACTIVE,
)
from academics.models import (
    Section,
    SchoolClass,
    ClassArm,
    AcademicSession,
    Term,
    StudentProfile,
    StudentEnrollment,
    Subject,
    TeachingAssignment,
    StudentAttendance,
    ATTENDANCE_PRESENT,
    ATTENDANCE_ABSENT,
    ATTENDANCE_LATE,
    ATTENDANCE_EXCUSED,
)
from accounts.models import User, SchoolMembership
from accounts.services import generate_student_id


SECTION_DISPLAY_MAP = dict(SECTION_CHOICES)


@transaction.atomic
def seed_school_classes(school) -> list[SchoolClass]:
    """
    Seed the standard Nigerian class catalogue for a new school.

    Creates:
    - Primary 1 through 6
    - JSS 1 through 3
    - SSS 1 through 3
    All seeded classes default to is_active=True.
    Schools deactivate classes they do not offer (e.g. Primary 6).

    Idempotent: safe to run multiple times without duplicating classes.
    """
    # 1. Ensure sections exist for this school
    section_instances = {}
    for order, (sec_type, sec_name) in enumerate(SECTION_CHOICES, start=1):
        section, _ = Section.objects.get_or_create(
            school=school,
            section_type=sec_type,
            defaults={
                "name": sec_name,
                "order": order,
                "is_active": True,
            },
        )
        section_instances[sec_type] = section

    # 2. Seed all standard classes
    created_or_found = []
    for sec_type, class_name, order in NIGERIAN_CLASS_CATALOGUE:
        section = section_instances[sec_type]
        school_class, _ = SchoolClass.objects.get_or_create(
            school=school,
            name=class_name,
            defaults={
                "section": section,
                "order": order,
                "is_active": True,
            },
        )
        created_or_found.append(school_class)

    return created_or_found


@transaction.atomic
def admit_student(
    *,
    school,
    first_name: str,
    last_name: str,
    middle_name: str = "",
    gender: str = "male",
    school_class: SchoolClass,
    class_arm: ClassArm = None,
    session: AcademicSession = None,
    date_of_birth=None,
    blood_group: str = "",
    genotype: str = "",
    state_of_origin: str = "",
    lga: str = "",
    residential_address: str = "",
    emergency_contact_name: str = "",
    emergency_contact_phone: str = "",
    emergency_contact_relationship: str = "",
    medical_conditions: str = "",
    admission_date=None,
    password: str = None,
) -> tuple[StudentProfile, StudentEnrollment]:
    """
    Admit and enroll a new student in a school tenant.
    
    1. Generates sequential student ID with school custom prefix (e.g. KHA/2026/0001, A-STD-0001).
    2. Creates central User account with role=student.
    3. Creates SchoolMembership linking user to school.
    4. Creates StudentProfile with biodata and emergency contacts.
    5. Creates StudentEnrollment in the active academic session.
    """
    student_id = generate_student_id(school)
    
    # 1. Create User account
    user = User(
        username=student_id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        is_active=True,
    )
    if password:
        user.set_password(password)
    else:
        # Default secure password if none provided (e.g. 'Student123!')
        user.set_password("Student123!")
    user.save()

    # 2. Assign Membership
    membership = SchoolMembership.objects.create(
        user=user,
        school=school,
        role=ROLE_STUDENT,
        id_number=student_id,
        status="active",
    )

    # 3. Create Student Profile
    student_profile = StudentProfile.objects.create(
        school=school,
        user=user,
        admission_number=student_id,
        date_of_birth=date_of_birth,
        gender=gender,
        blood_group=blood_group,
        genotype=genotype,
        state_of_origin=state_of_origin,
        lga=lga,
        residential_address=residential_address,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        emergency_contact_relationship=emergency_contact_relationship,
        medical_conditions=medical_conditions,
        admission_date=admission_date or timezone.now().date(),
        is_active=True,
    )

    # 4. Enroll Student in Session
    target_session = session or AcademicSession.objects.filter(school=school, is_current=True).first()
    if not target_session:
        # Fallback to latest session if none marked current
        target_session = AcademicSession.objects.filter(school=school).order_by("-created_at").first()

    enrollment = None
    if target_session and school_class:
        enrollment = StudentEnrollment.objects.create(
            school=school,
            student=student_profile,
            session=target_session,
            school_class=school_class,
            class_arm=class_arm,
            status=ENROLLMENT_ACTIVE,
        )

    return student_profile, enrollment


@transaction.atomic
def seed_default_school_subjects(school) -> list[Subject]:
    """
    Seed standard core Nigerian curriculum subjects for a school.
    Idempotent: safe to run multiple times.
    """
    CORE_SUBJECTS = [
        ("Mathematics", "MTH", False),
        ("English Language", "ENG", False),
        ("Basic Science", "BSC", False),
        ("Civic Education", "CIV", False),
        ("Social Studies", "SOS", False),
        ("Agricultural Science", "AGR", False),
        ("Information Technology (ICT)", "ICT", False),
        ("Physical & Health Education", "PHE", False),
        ("Business Studies", "BUS", False),
        ("Basic Technology", "BTE", False),
    ]

    created = []
    for name, code, is_elective in CORE_SUBJECTS:
        subject, _ = Subject.objects.get_or_create(
            school=school,
            code=code,
            defaults={
                "name": name,
                "is_elective": is_elective,
                "is_active": True,
            },
        )
        created.append(subject)

    return created


@transaction.atomic
def assign_teacher(
    *,
    school,
    teacher: User,
    session: AcademicSession,
    subject: Subject,
    school_class: SchoolClass,
    class_arm: ClassArm = None,
) -> TeachingAssignment:
    """
    Assign a teaching staff member to teach a subject in a specific class / arm
    for the given academic session.
    """
    assignment, _ = TeachingAssignment.objects.update_or_create(
        school=school,
        session=session,
        subject=subject,
        school_class=school_class,
        class_arm=class_arm,
        defaults={
            "teacher": teacher,
            "is_active": True,
        },
    )
    return assignment


@transaction.atomic
def record_student_attendance(
    *,
    school,
    session: AcademicSession,
    term: Term,
    school_class: SchoolClass,
    class_arm: ClassArm = None,
    date,
    marked_by: User = None,
    attendance_records: list[dict],
) -> int:
    """
    Bulk records or updates daily student attendance for a class / arm.
    attendance_records is a list of dicts:
    [
        {"student_id": "...", "status": "present"|"absent"|"late"|"excused", "remarks": "..."},
        ...
    ]
    Returns count of records saved.
    """
    count = 0
    for record in attendance_records:
        student_id = record.get("student_id")
        status = record.get("status", ATTENDANCE_PRESENT)
        remarks = record.get("remarks", "").strip()

        student = StudentProfile.objects.filter(id=student_id, school=school).first()
        if not student:
            continue

        StudentAttendance.objects.update_or_create(
            school=school,
            student=student,
            date=date,
            defaults={
                "session": session,
                "term": term,
                "school_class": school_class,
                "class_arm": class_arm,
                "status": status,
                "marked_by": marked_by,
                "remarks": remarks,
            },
        )
        count += 1

    return count


def get_student_attendance_stats(student: StudentProfile, session: AcademicSession = None, term: Term = None) -> dict:
    """
    Calculates attendance summary statistics for a student.
    Returns:
    {
        "total_days": int,
        "present": int,
        "absent": int,
        "late": int,
        "excused": int,
        "percentage": float,
    }
    """
    qs = StudentAttendance.objects.filter(student=student)
    if session:
        qs = qs.filter(session=session)
    if term:
        qs = qs.filter(term=term)

    total = qs.count()
    if total == 0:
        return {
            "total_days": 0,
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "percentage": 100.0,
        }

    present = qs.filter(status=ATTENDANCE_PRESENT).count()
    late = qs.filter(status=ATTENDANCE_LATE).count()
    excused = qs.filter(status=ATTENDANCE_EXCUSED).count()
    absent = qs.filter(status=ATTENDANCE_ABSENT).count()

    # In Nigerian schools, present and excused are counted favorably, late is 0.5 or present
    percentage = round(((present + late) / total) * 100, 1)

    return {
        "total_days": total,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "percentage": percentage,
    }


