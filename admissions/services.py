"""
Admissions business logic services.
Handles application number generation, submission, review decisions,
and atomic conversion of admitted applicants into enrolled students and linked parents.
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from admissions.models import (
    AdmissionApplication,
    ApplicationDocument,
    APPLICATION_STATUS_PENDING,
    APPLICATION_STATUS_ADMITTED,
    APPLICATION_STATUS_ENROLLED,
)
from academics.services import admit_student
from accounts.models import User, SchoolMembership, ParentStudentRelationship
from accounts.services import create_school_user, link_parent_to_student
from core.constants import ROLE_PARENT, MEMBERSHIP_ACTIVE


def generate_application_number(school, session) -> str:
    """
    Generate unique application number scoped to school and session.
    Format: {SCHOOL_CODE}-ADM-{YEAR}-{SEQ:04d}
    Example: HS-ADM-2026-0001
    """
    year = str(session.start_date.year) if session and session.start_date else str(timezone.now().year)
    prefix = f"{school.code}-ADM-{year}-"
    latest = (
        AdmissionApplication.objects.filter(school=school, application_number__startswith=prefix)
        .order_by("-application_number")
        .first()
    )
    if latest:
        try:
            last_seq = int(latest.application_number.split("-")[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1
    return f"{prefix}{new_seq:04d}"


@transaction.atomic
def submit_admission_application(
    *,
    school,
    session,
    first_name: str,
    last_name: str,
    middle_name: str = "",
    gender: str = "male",
    date_of_birth,
    applying_for_class,
    state_of_origin: str = "",
    lga: str = "",
    residential_address: str = "",
    previous_school: str = "",
    medical_conditions: str = "",
    parent_name: str,
    parent_email: str = "",
    parent_phone: str,
    parent_relationship: str = "Father",
    parent_address: str = "",
    documents: list = None,
) -> AdmissionApplication:
    """
    Public admission submission service.
    Creates an AdmissionApplication and attaches uploaded documents.
    """
    app_number = generate_application_number(school, session)

    application = AdmissionApplication.objects.create(
        school=school,
        session=session,
        application_number=app_number,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        middle_name=middle_name.strip(),
        gender=gender,
        date_of_birth=date_of_birth,
        applying_for_class=applying_for_class,
        state_of_origin=state_of_origin.strip(),
        lga=lga.strip(),
        residential_address=residential_address.strip(),
        previous_school=previous_school.strip(),
        medical_conditions=medical_conditions.strip(),
        parent_name=parent_name.strip(),
        parent_email=parent_email.strip().lower() if parent_email else "",
        parent_phone=parent_phone.strip(),
        parent_relationship=parent_relationship.strip(),
        parent_address=parent_address.strip(),
        status=APPLICATION_STATUS_PENDING,
        submitted_at=timezone.now(),
    )

    if documents:
        for doc_item in documents:
            doc_type = doc_item.get("document_type")
            doc_file = doc_item.get("file")
            orig_name = doc_item.get("original_filename", "")
            if doc_type and doc_file:
                ApplicationDocument.objects.create(
                    application=application,
                    document_type=doc_type,
                    file=doc_file,
                    original_filename=orig_name or getattr(doc_file, "name", ""),
                )

    return application


@transaction.atomic
def convert_applicant_to_student(
    application: AdmissionApplication,
    *,
    class_arm=None,
    session=None,
    student_password: str = None,
    admitted_by=None,
) -> tuple:
    """
    Converts an admitted applicant into an official enrolled student.
    
    1. Creates User + SchoolMembership + StudentProfile + StudentEnrollment via admit_student.
    2. Finds or creates Parent User, grants Parent SchoolMembership, links via ParentStudentRelationship.
    3. Updates AdmissionApplication status to 'enrolled' with enrolled_student foreign key.
    """
    if application.enrolled_student:
        raise ValidationError(
            f"Applicant {application.full_name} is already enrolled as student {application.enrolled_student.admission_number}."
        )

    school = application.school
    target_session = session or application.session

    # 1. Admit student
    student_profile, enrollment = admit_student(
        school=school,
        first_name=application.first_name,
        last_name=application.last_name,
        middle_name=application.middle_name,
        gender=application.gender,
        school_class=application.applying_for_class,
        class_arm=class_arm,
        session=target_session,
        date_of_birth=application.date_of_birth,
        state_of_origin=application.state_of_origin,
        lga=application.lga,
        residential_address=application.residential_address,
        emergency_contact_name=application.parent_name,
        emergency_contact_phone=application.parent_phone,
        emergency_contact_relationship=application.parent_relationship,
        medical_conditions=application.medical_conditions,
        admission_date=timezone.now().date(),
        password=student_password,
    )

    # 2. Find or create Parent User
    parent_user = None
    if application.parent_email:
        parent_user = User.objects.filter(email=application.parent_email).first()

    if not parent_user:
        # Split parent name
        name_parts = application.parent_name.split()
        p_first = name_parts[0] if name_parts else "Parent"
        p_last = name_parts[-1] if len(name_parts) > 1 else application.last_name

        parent_user, _ = create_school_user(
            school=school,
            role=ROLE_PARENT,
            first_name=p_first,
            last_name=p_last,
            email=application.parent_email or None,
            phone_number=application.parent_phone,
            password="Parent123!",
        )
    else:
        # Ensure parent has membership in this school
        SchoolMembership.objects.get_or_create(
            user=parent_user,
            school=school,
            role=ROLE_PARENT,
            defaults={"status": MEMBERSHIP_ACTIVE, "id_number": parent_user.username},
        )

    # Link parent to student
    parent_rel = link_parent_to_student(
        school=school,
        parent=parent_user,
        student=student_profile,
        relationship_type=application.parent_relationship.lower(),
        is_primary_contact=True,
        is_emergency_contact=True,
        can_view_results=True,
    )

    # 3. Update Admission Application
    application.status = APPLICATION_STATUS_ENROLLED
    application.enrolled_student = student_profile
    application.decision_date = timezone.now()
    if admitted_by:
        application.reviewed_by = admitted_by
    application.save(update_fields=["status", "enrolled_student", "decision_date", "reviewed_by", "updated_at"])

    return student_profile, enrollment, parent_rel
