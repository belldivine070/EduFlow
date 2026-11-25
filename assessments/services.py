"""
Assessments services.

Covers:
- Question creation (Objective MCQ, True/False, Essay)
- Assessment configuration and question assignment
- Student submission processing and auto-marking
- Manual essay marking and feedback
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from assessments.models import (
    Question,
    QuestionOption,
    QuestionCategory,
    Assessment,
    AssessmentQuestion,
    StudentAssessmentSubmission,
    StudentAssessmentAnswer,
    QUESTION_TYPE_MULTIPLE_CHOICE,
    QUESTION_TYPE_TRUE_FALSE,
    QUESTION_TYPE_ESSAY,
    SUBMISSION_STATUS_IN_PROGRESS,
    SUBMISSION_STATUS_SUBMITTED,
    SUBMISSION_STATUS_MARKED,
)


@transaction.atomic
def create_question(
    *,
    school,
    subject,
    prompt: str,
    question_type: str = QUESTION_TYPE_MULTIPLE_CHOICE,
    category=None,
    explanation: str = "",
    default_marks: float = 1.0,
    created_by=None,
    options: list[dict] = None,
) -> Question:
    """
    Creates a new question with optional MCQ/TF options.
    options = [{'text': '...', 'is_correct': True|False}, ...]
    """
    question = Question.objects.create(
        school=school,
        subject=subject,
        prompt=prompt.strip(),
        question_type=question_type,
        category=category,
        explanation=explanation.strip(),
        default_marks=Decimal(str(default_marks)),
        created_by=created_by,
        is_active=True,
    )

    if options and question_type in [QUESTION_TYPE_MULTIPLE_CHOICE, QUESTION_TYPE_TRUE_FALSE]:
        for idx, opt in enumerate(options, start=1):
            QuestionOption.objects.create(
                question=question,
                option_text=opt.get("text", "").strip(),
                is_correct=opt.get("is_correct", False),
                order=idx,
            )

    return question


@transaction.atomic
def submit_student_assessment(
    *,
    submission: StudentAssessmentSubmission,
    answers_data: list[dict],
) -> StudentAssessmentSubmission:
    """
    Processes student submission of an assessment.
    answers_data = [
        {"question_id": "...", "selected_option_id": "..." (for MCQ), "essay_text": "..." (for Essay)},
        ...
    ]
    Auto-marks all objective and true/false questions.
    If essay questions exist, sets status to SUBMISSION_STATUS_SUBMITTED.
    If 100% objective, sets status to SUBMISSION_STATUS_MARKED.
    """
    assessment = submission.assessment
    aq_map = {
        aq.question_id: aq.marks
        for aq in AssessmentQuestion.objects.filter(assessment=assessment)
    }

    auto_score = Decimal("0.0")
    has_essays = False

    for item in answers_data:
        q_id = item.get("question_id")
        opt_id = item.get("selected_option_id")
        essay_text = item.get("essay_text", "").strip()

        question = Question.objects.filter(id=q_id).first()
        if not question:
            continue

        allocated_mark = aq_map.get(question.id, question.default_marks)

        if question.question_type in [QUESTION_TYPE_MULTIPLE_CHOICE, QUESTION_TYPE_TRUE_FALSE]:
            selected_opt = QuestionOption.objects.filter(id=opt_id, question=question).first() if opt_id else None
            is_correct = bool(selected_opt and selected_opt.is_correct)
            awarded = allocated_mark if is_correct else Decimal("0.0")
            auto_score += awarded

            StudentAssessmentAnswer.objects.update_or_create(
                submission=submission,
                question=question,
                defaults={
                    "selected_option": selected_opt,
                    "is_correct": is_correct,
                    "marks_awarded": awarded,
                },
            )
        elif question.question_type == QUESTION_TYPE_ESSAY:
            has_essays = True
            StudentAssessmentAnswer.objects.update_or_create(
                submission=submission,
                question=question,
                defaults={
                    "essay_response": essay_text,
                    "is_correct": None,
                    "marks_awarded": Decimal("0.0"),
                },
            )

    submission.auto_marked_score = auto_score
    submission.submitted_at = timezone.now()

    if has_essays:
        submission.status = SUBMISSION_STATUS_SUBMITTED
        submission.total_score = auto_score + Decimal(str(submission.manual_marked_score or 0.0))
    else:
        submission.status = SUBMISSION_STATUS_MARKED
        submission.total_score = auto_score

    if assessment.total_marks > 0:
        submission.percentage = round((submission.total_score / assessment.total_marks) * Decimal("100.0"), 2)
        submission.is_passed = submission.total_score >= assessment.pass_mark

    submission.save()
    return submission


@transaction.atomic
def mark_essay_answer(
    *,
    answer: StudentAssessmentAnswer,
    marks_awarded: float,
    feedback: str = "",
    marked_by=None,
) -> StudentAssessmentAnswer:
    """
    Teacher marks a student's essay answer, awards score, and provides feedback.
    Re-aggregates total score on the parent submission.
    """
    answer.marks_awarded = Decimal(str(marks_awarded))
    answer.feedback = feedback.strip()
    answer.marked_by = marked_by
    answer.is_correct = answer.marks_awarded > 0
    answer.save()

    # Recalculate submission scores
    submission = answer.submission
    manual_total = Decimal("0.0")
    pending_essays = False

    essay_answers = StudentAssessmentAnswer.objects.filter(
        submission=submission,
        question__question_type=QUESTION_TYPE_ESSAY,
    )
    for ans in essay_answers:
        if ans.marked_by is None:
            pending_essays = True
        manual_total += ans.marks_awarded

    submission.manual_marked_score = manual_total
    submission.total_score = Decimal(str(submission.auto_marked_score or 0.0)) + manual_total

    if not pending_essays:
        submission.status = SUBMISSION_STATUS_MARKED

    if submission.assessment.total_marks > 0:
        submission.percentage = round((submission.total_score / submission.assessment.total_marks) * Decimal("100.0"), 2)
        submission.is_passed = submission.total_score >= submission.assessment.pass_mark

    submission.save()
    return answer
