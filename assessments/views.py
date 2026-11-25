"""
Assessments views.

Covers:
- QuestionBankListView: Browse and filter questions
- QuestionCreateView: Create MCQ, True/False, or Essay questions
- AssessmentListView: Continuous assessment and test management
- AssessmentCreateView: Configure a test or quiz
- AssessmentDetailView: Test details and question management
- AssessmentTakeView: Student CBT test interface
- AssessmentMarkingQueueView: Teacher marking queue for essay responses
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from schools.services import resolve_school_template
from academics.models import Subject, SchoolClass, AcademicSession, Term, StudentProfile
from assessments.models import (
    Question,
    QuestionOption,
    QuestionCategory,
    Assessment,
    AssessmentQuestion,
    StudentAssessmentSubmission,
    StudentAssessmentAnswer,
    QUESTION_TYPE_CHOICES,
    QUESTION_TYPE_MULTIPLE_CHOICE,
    QUESTION_TYPE_TRUE_FALSE,
    QUESTION_TYPE_ESSAY,
    SUBMISSION_STATUS_IN_PROGRESS,
    SUBMISSION_STATUS_SUBMITTED,
    SUBMISSION_STATUS_MARKED,
)
from assessments.services import (
    create_question,
    submit_student_assessment,
    mark_essay_answer,
)


class SchoolRequiredMixin(LoginRequiredMixin):
    def get_school(self):
        return getattr(self.request, "school", None)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        school = self.get_school()
        if not school:
            messages.warning(request, "Please access this feature through a school portal.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class QuestionBankListView(SchoolRequiredMixin, View):
    """
    Question Bank listing with filters by subject and question type.
    """

    def get(self, request):
        school = self.get_school()
        subject_id = request.GET.get("subject")
        q_type = request.GET.get("type")

        questions = (
            Question.objects
            .filter(school=school)
            .select_related("subject", "category")
            .prefetch_related("options")
            .order_by("subject__name", "-created_at")
        )

        if subject_id:
            questions = questions.filter(subject_id=subject_id)
        if q_type:
            questions = questions.filter(question_type=q_type)

        subjects = Subject.objects.filter(school=school, is_active=True).order_by("name")

        context = {
            "questions": questions,
            "subjects": subjects,
            "selected_subject": subject_id,
            "selected_type": q_type,
            "question_type_choices": QUESTION_TYPE_CHOICES,
        }
        template = resolve_school_template(school, "assessments/questions/list.html")
        return render(request, template, context)


class QuestionCreateView(SchoolRequiredMixin, View):
    """
    Create a new question in the question bank.
    """

    def post(self, request):
        school = self.get_school()
        subject_id = request.POST.get("subject")
        prompt = request.POST.get("prompt", "").strip()
        q_type = request.POST.get("question_type", QUESTION_TYPE_MULTIPLE_CHOICE)
        default_marks = request.POST.get("default_marks", "1.0")
        explanation = request.POST.get("explanation", "").strip()

        subject = get_object_or_404(Subject, id=subject_id, school=school)

        options = []
        if q_type == QUESTION_TYPE_MULTIPLE_CHOICE:
            correct_idx = request.POST.get("correct_option")
            for i in range(1, 5):
                text = request.POST.get(f"option_{i}", "").strip()
                if text:
                    options.append({
                        "text": text,
                        "is_correct": str(i) == str(correct_idx),
                    })
        elif q_type == QUESTION_TYPE_TRUE_FALSE:
            correct_val = request.POST.get("tf_correct", "true")
            options = [
                {"text": "True", "is_correct": correct_val == "true"},
                {"text": "False", "is_correct": correct_val == "false"},
            ]

        create_question(
            school=school,
            subject=subject,
            prompt=prompt,
            question_type=q_type,
            explanation=explanation,
            default_marks=float(default_marks or 1.0),
            created_by=request.user,
            options=options,
        )

        messages.success(request, "Question added to Question Bank successfully.")
        return redirect("assessments:question_list")


class AssessmentListView(SchoolRequiredMixin, View):
    """
    List assessments / CBT tests configured for the school.
    """

    def get(self, request):
        school = self.get_school()
        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()

        assessments = (
            Assessment.objects
            .filter(school=school)
            .select_related("subject", "school_class", "session", "term")
            .order_by("-created_at")
        )

        subjects = Subject.objects.filter(school=school, is_active=True).order_by("name")
        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order")

        context = {
            "assessments": assessments,
            "subjects": subjects,
            "classes": classes,
            "current_session": current_session,
            "current_term": current_term,
        }
        template = resolve_school_template(school, "assessments/tests/list.html")
        return render(request, template, context)


class AssessmentCreateView(SchoolRequiredMixin, View):
    """
    Create a new assessment / test.
    """

    def post(self, request):
        school = self.get_school()
        title = request.POST.get("title", "").strip()
        subject_id = request.POST.get("subject")
        school_class_id = request.POST.get("school_class")
        duration = request.POST.get("duration_minutes", "45")
        total_marks = request.POST.get("total_marks", "30.0")
        pass_mark = request.POST.get("pass_mark", "15.0")
        instructions = request.POST.get("instructions", "").strip()

        subject = get_object_or_404(Subject, id=subject_id, school=school)
        school_class = get_object_or_404(SchoolClass, id=school_class_id, school=school)
        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()

        if not (current_session and current_term):
            messages.error(request, "Please set an active session and term before creating tests.")
            return redirect("assessments:assessment_list")

        assessment = Assessment.objects.create(
            school=school,
            session=current_session,
            term=current_term,
            subject=subject,
            school_class=school_class,
            title=title,
            instructions=instructions,
            duration_minutes=int(duration or 45),
            total_marks=Decimal(str(total_marks or 30.0)),
            pass_mark=Decimal(str(pass_mark or 15.0)),
            is_published=True,
            created_by=request.user,
        )

        messages.success(request, f"Assessment '{title}' created successfully.")
        return redirect("assessments:assessment_detail", assessment_id=assessment.id)


class AssessmentDetailView(SchoolRequiredMixin, View):
    """
    Assessment overview: view questions included, submissions, and add questions.
    """

    def get(self, request, assessment_id):
        school = self.get_school()
        assessment = get_object_or_404(
            Assessment.objects.select_related("subject", "school_class", "session", "term"),
            id=assessment_id,
            school=school,
        )

        included_questions = (
            AssessmentQuestion.objects
            .filter(assessment=assessment)
            .select_related("question")
            .prefetch_related("question__options")
            .order_by("order")
        )

        # Bank questions for this subject that are not yet added
        existing_q_ids = included_questions.values_list("question_id", flat=True)
        available_questions = (
            Question.objects
            .filter(school=school, subject=assessment.subject, is_active=True)
            .exclude(id__in=existing_q_ids)
            .order_by("-created_at")
        )

        submissions = (
            StudentAssessmentSubmission.objects
            .filter(assessment=assessment)
            .select_related("student__user")
            .order_by("-submitted_at")
        )

        context = {
            "assessment": assessment,
            "included_questions": included_questions,
            "available_questions": available_questions,
            "submissions": submissions,
        }
        template = resolve_school_template(school, "assessments/tests/detail.html")
        return render(request, template, context)

    def post(self, request, assessment_id):
        """Add a question from bank to this assessment."""
        school = self.get_school()
        assessment = get_object_or_404(Assessment, id=assessment_id, school=school)
        question_id = request.POST.get("question_id")
        marks = request.POST.get("marks", "1.0")

        question = get_object_or_404(Question, id=question_id, school=school)
        next_order = AssessmentQuestion.objects.filter(assessment=assessment).count() + 1

        AssessmentQuestion.objects.create(
            assessment=assessment,
            question=question,
            order=next_order,
            marks=Decimal(str(marks or 1.0)),
        )

        messages.success(request, "Question added to assessment.")
        return redirect("assessments:assessment_detail", assessment_id=assessment.id)


class AssessmentTakeView(SchoolRequiredMixin, View):
    """
    Student interface for taking a CBT assessment.
    """

    def get(self, request, assessment_id):
        school = self.get_school()
        assessment = get_object_or_404(Assessment, id=assessment_id, school=school)
        student_profile = StudentProfile.objects.filter(school=school, user=request.user).first()

        submission = None
        if student_profile:
            submission, _ = StudentAssessmentSubmission.objects.get_or_create(
                school=school,
                assessment=assessment,
                student=student_profile,
                defaults={"started_at": timezone.now()},
            )

        questions = (
            AssessmentQuestion.objects
            .filter(assessment=assessment)
            .select_related("question")
            .prefetch_related("question__options")
            .order_by("order")
        )

        context = {
            "assessment": assessment,
            "submission": submission,
            "questions": questions,
            "student_profile": student_profile,
        }
        template = resolve_school_template(school, "assessments/tests/take.html")
        return render(request, template, context)

    def post(self, request, assessment_id):
        """Submit the assessment."""
        school = self.get_school()
        assessment = get_object_or_404(Assessment, id=assessment_id, school=school)
        student_profile = get_object_or_404(StudentProfile, school=school, user=request.user)

        submission, _ = StudentAssessmentSubmission.objects.get_or_create(
            school=school,
            assessment=assessment,
            student=student_profile,
        )

        questions = AssessmentQuestion.objects.filter(assessment=assessment).select_related("question")
        answers_data = []

        for aq in questions:
            q = aq.question
            if q.question_type in [QUESTION_TYPE_MULTIPLE_CHOICE, QUESTION_TYPE_TRUE_FALSE]:
                selected_opt = request.POST.get(f"q_{q.id}")
                answers_data.append({
                    "question_id": str(q.id),
                    "selected_option_id": selected_opt,
                })
            elif q.question_type == QUESTION_TYPE_ESSAY:
                essay_text = request.POST.get(f"q_{q.id}", "")
                answers_data.append({
                    "question_id": str(q.id),
                    "essay_text": essay_text,
                })

        submit_student_assessment(
            submission=submission,
            answers_data=answers_data,
        )

        messages.success(request, f"Assessment submitted successfully. Score: {submission.total_score}/{assessment.total_marks}")
        return redirect("assessments:assessment_detail", assessment_id=assessment.id)


class AssessmentMarkingQueueView(SchoolRequiredMixin, View):
    """
    Teacher marking queue for essay answers.
    """

    def get(self, request, submission_id):
        school = self.get_school()
        submission = get_object_or_404(
            StudentAssessmentSubmission.objects.select_related("assessment", "student__user"),
            id=submission_id,
            school=school,
        )

        essay_answers = (
            StudentAssessmentAnswer.objects
            .filter(submission=submission, question__question_type=QUESTION_TYPE_ESSAY)
            .select_related("question")
        )

        context = {
            "submission": submission,
            "essay_answers": essay_answers,
        }
        template = resolve_school_template(school, "assessments/marking/queue.html")
        return render(request, template, context)

    def post(self, request, submission_id):
        school = self.get_school()
        submission = get_object_or_404(StudentAssessmentSubmission, id=submission_id, school=school)
        answer_id = request.POST.get("answer_id")
        marks = request.POST.get("marks", "0.0")
        feedback = request.POST.get("feedback", "")

        answer = get_object_or_404(StudentAssessmentAnswer, id=answer_id, submission=submission)
        mark_essay_answer(
            answer=answer,
            marks_awarded=float(marks or 0.0),
            feedback=feedback,
            marked_by=request.user,
        )

        messages.success(request, "Essay marked and score updated successfully.")
        return redirect("assessments:marking_queue", submission_id=submission.id)
