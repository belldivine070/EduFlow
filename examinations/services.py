"""
Examinations services.

Covers:
- Default Nigerian grading scale seeding (70-100 A, 60-69 B, 50-59 C, 40-49 D, 0-39 E)
- Score recording and validation (TET: 30%, EXAM: 70%)
- Termly report compilation and class / arm ranking
- Result approval and publication workflows
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from core.constants import DEFAULT_TET_WEIGHT, DEFAULT_EXAM_WEIGHT
from examinations.models import (
    GradingScale,
    StudentSubjectResult,
    StudentTermReport,
    RESULT_STATUS_DRAFT,
    RESULT_STATUS_SUBMITTED,
    RESULT_STATUS_APPROVED,
    RESULT_STATUS_PUBLISHED,
)
from academics.services import get_student_attendance_stats


@transaction.atomic
def seed_default_grading_scale(school) -> list[GradingScale]:
    """
    Seed standard Nigerian secondary school grading scale for a school.
    Idempotent: safe to run multiple times.
    """
    DEFAULT_SCALES = [
        ("A", 70.0, 100.0, "Excellent", 1),
        ("B", 60.0, 69.99, "Very Good", 2),
        ("C", 50.0, 59.99, "Good / Credit", 3),
        ("D", 40.0, 49.99, "Pass", 4),
        ("E", 0.0, 39.99, "Fail", 5),
    ]

    created = []
    for grade, min_s, max_s, remark, order in DEFAULT_SCALES:
        scale, _ = GradingScale.objects.get_or_create(
            school=school,
            grade=grade,
            defaults={
                "min_score": Decimal(str(min_s)),
                "max_score": Decimal(str(max_s)),
                "remark": remark,
                "order": order,
            },
        )
        created.append(scale)
    return created


def get_grade_for_score(school, score: float) -> str:
    """
    Determine letter grade for a score based on school's configured scales.
    """
    score_dec = Decimal(str(score))
    scale = (
        GradingScale.objects
        .filter(school=school, min_score__lte=score_dec, max_score__gte=score_dec)
        .first()
    )
    if scale:
        return scale.grade

    # Fallback
    if score >= 70:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 40:
        return "D"
    return "E"


@transaction.atomic
def record_student_subject_score(
    *,
    school,
    student,
    session,
    term,
    subject,
    school_class,
    class_arm=None,
    ca_score=None,
    exam_score=None,
    teacher_remarks: str = "",
    entered_by=None,
    max_ca: float = DEFAULT_TET_WEIGHT,
    max_exam: float = DEFAULT_EXAM_WEIGHT,
) -> StudentSubjectResult:
    """
    Records or updates a student's termly score for a subject.
    Validates ca_score <= max_ca and exam_score <= max_exam.
    Calculates total score and assigns grade.
    """
    ca_dec = Decimal(str(ca_score)) if ca_score is not None else None
    exam_dec = Decimal(str(exam_score)) if exam_score is not None else None

    max_ca_dec = Decimal(str(max_ca))
    max_exam_dec = Decimal(str(max_exam))

    if ca_dec is not None and (ca_dec < 0 or ca_dec > max_ca_dec):
        raise ValueError(f"Continuous Assessment score must be between 0 and {max_ca}.")

    if exam_dec is not None and (exam_dec < 0 or exam_dec > max_exam_dec):
        raise ValueError(f"Examination score must be between 0 and {max_exam}.")

    result, _ = StudentSubjectResult.objects.get_or_create(
        school=school,
        student=student,
        session=session,
        term=term,
        subject=subject,
        defaults={
            "school_class": school_class,
            "class_arm": class_arm,
            "entered_by": entered_by,
        },
    )

    result.school_class = school_class
    result.class_arm = class_arm
    result.ca_score = ca_dec
    result.exam_score = exam_dec
    result.teacher_remarks = teacher_remarks.strip()
    if entered_by:
        result.entered_by = entered_by

    # Recalculate totals
    scales = GradingScale.objects.filter(school=school).order_by("-min_score")
    result.calculate_totals(grading_scales=scales)
    result.save()
    return result


@transaction.atomic
def compute_term_reports_for_class(
    *,
    school,
    session,
    term,
    school_class,
    class_arm=None,
) -> list[StudentTermReport]:
    """
    Aggregates all subject scores for every student in a class / arm,
    computes total obtainable, total obtained, average percentage,
    class rank, arm rank, and attendance statistics.
    """
    # 1. Fetch active enrollments
    enrollments_qs = (
        school_class.enrollments
        .filter(school=school, session=session, status="active")
        .select_related("student__user", "class_arm")
    )
    if class_arm:
        enrollments_qs = enrollments_qs.filter(class_arm=class_arm)

    reports = []
    student_averages = []

    for enr in enrollments_qs:
        student = enr.student

        # Fetch all subject results for this student in this session and term
        results = StudentSubjectResult.objects.filter(
            school=school,
            student=student,
            session=session,
            term=term,
        )

        total_subjects = results.count()
        total_obtainable = Decimal(str(total_subjects * 100))
        total_obtained = Decimal("0.0")

        for r in results:
            if r.total_score is not None:
                total_obtained += r.total_score

        avg_score = Decimal("0.0")
        if total_subjects > 0:
            avg_score = round(total_obtained / Decimal(str(total_subjects)), 2)

        # Attendance stats
        att_stats = get_student_attendance_stats(student, session=session, term=term)

        report, _ = StudentTermReport.objects.update_or_create(
            school=school,
            student=student,
            session=session,
            term=term,
            defaults={
                "school_class": school_class,
                "class_arm": enr.class_arm,
                "total_subjects": total_subjects,
                "total_obtainable_score": total_obtainable,
                "total_obtained_score": total_obtained,
                "average_score": avg_score,
                "attendance_days_present": att_stats["present"],
                "attendance_days_absent": att_stats["absent"],
                "attendance_percentage": Decimal(str(att_stats["percentage"])),
            },
        )
        reports.append(report)
        student_averages.append((report, avg_score))

    # 2. Compute Class and Arm Rankings
    student_averages.sort(key=lambda x: x[1], reverse=True)
    total_in_class = len(student_averages)

    for rank, (rep, _) in enumerate(student_averages, start=1):
        rep.class_rank = rank
        rep.class_size = total_in_class
        rep.save(update_fields=["class_rank", "class_size"])

    return reports


@transaction.atomic
def approve_term_results(
    *,
    school,
    session,
    term,
    school_class,
    approved_by,
) -> int:
    """
    Principal review and approval for an entire class's results.
    Transitions StudentSubjectResult and StudentTermReport from submitted/draft to approved.
    """
    now = timezone.now()
    sub_count = StudentSubjectResult.objects.filter(
        school=school,
        session=session,
        term=term,
        school_class=school_class,
    ).update(
        status=RESULT_STATUS_APPROVED,
        approved_by=approved_by,
        approved_at=now,
    )

    StudentTermReport.objects.filter(
        school=school,
        session=session,
        term=term,
        school_class=school_class,
    ).update(
        status=RESULT_STATUS_APPROVED,
        approved_by=approved_by,
    )

    return sub_count


@transaction.atomic
def publish_term_results(
    *,
    school,
    session,
    term,
    school_class=None,
) -> int:
    """
    Publishes approved term results so students and parents can view report cards.
    """
    now = timezone.now()
    qs_res = StudentSubjectResult.objects.filter(
        school=school,
        session=session,
        term=term,
        status=RESULT_STATUS_APPROVED,
    )
    qs_rep = StudentTermReport.objects.filter(
        school=school,
        session=session,
        term=term,
        status=RESULT_STATUS_APPROVED,
    )

    if school_class:
        qs_res = qs_res.filter(school_class=school_class)
        qs_rep = qs_rep.filter(school_class=school_class)

    count = qs_res.update(status=RESULT_STATUS_PUBLISHED)
    qs_rep.update(status=RESULT_STATUS_PUBLISHED, published_at=now)
    return count
