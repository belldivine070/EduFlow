"""
Examinations views.

Covers:
- ScoreEntryView: Teacher score entry (TET: 30%, EXAM: 70%)
- ResultApprovalView: Principal review and approval
- ResultPublicationView: Publish approved results
- ReportCardView: Detailed Nigerian report card dossier
- StudentResultListView: Student / Parent portal to view published results
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from schools.services import resolve_school_template
from academics.models import Subject, SchoolClass, ClassArm, AcademicSession, Term, StudentProfile, StudentEnrollment
from core.constants import DEFAULT_TET_WEIGHT, DEFAULT_EXAM_WEIGHT, ROLE_DIRECTOR, ROLE_PRINCIPAL
from examinations.models import (
    GradingScale,
    StudentSubjectResult,
    StudentTermReport,
    RESULT_STATUS_DRAFT,
    RESULT_STATUS_SUBMITTED,
    RESULT_STATUS_APPROVED,
    RESULT_STATUS_PUBLISHED,
)
from examinations.services import (
    seed_default_grading_scale,
    record_student_subject_score,
    compute_term_reports_for_class,
    approve_term_results,
    publish_term_results,
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


class ScoreEntryView(SchoolRequiredMixin, View):
    """
    Teacher entry interface for Continuous Assessment (30%) and Exam (70%) scores.
    """

    def get(self, request):
        school = self.get_school()
        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()

        classes = SchoolClass.objects.filter(school=school, is_active=True).prefetch_related("arms").order_by("order")
        subjects = Subject.objects.filter(school=school, is_active=True).order_by("name")

        class_id = request.GET.get("class_id")
        arm_id = request.GET.get("arm_id")
        subject_id = request.GET.get("subject_id")

        selected_class = None
        if class_id:
            selected_class = SchoolClass.objects.filter(id=class_id, school=school).first()
        if not selected_class:
            selected_class = classes.first()

        selected_arm = None
        if arm_id and selected_class:
            selected_arm = ClassArm.objects.filter(id=arm_id, school_class=selected_class).first()

        selected_subject = None
        if subject_id:
            selected_subject = Subject.objects.filter(id=subject_id, school=school).first()
        if not selected_subject:
            selected_subject = subjects.first()

        student_scores = []
        if selected_class and selected_subject and current_session and current_term:
            enrollments = (
                StudentEnrollment.objects
                .filter(school=school, school_class=selected_class, session=current_session, status="active")
                .select_related("student__user")
                .order_by("student__user__last_name", "student__user__first_name")
            )
            if selected_arm:
                enrollments = enrollments.filter(class_arm=selected_arm)

            existing_results = {
                r.student_id: r
                for r in StudentSubjectResult.objects.filter(
                    school=school,
                    session=current_session,
                    term=current_term,
                    subject=selected_subject,
                    school_class=selected_class,
                )
            }

            for enr in enrollments:
                st = enr.student
                res = existing_results.get(st.id)
                student_scores.append({
                    "student": st,
                    "ca_score": res.ca_score if res else "",
                    "exam_score": res.exam_score if res else "",
                    "total_score": res.total_score if res else "",
                    "grade": res.grade if res else "",
                    "remarks": res.teacher_remarks if res else "",
                    "status": res.status if res else RESULT_STATUS_DRAFT,
                })

        context = {
            "classes": classes,
            "subjects": subjects,
            "selected_class": selected_class,
            "selected_arm": selected_arm,
            "selected_subject": selected_subject,
            "current_session": current_session,
            "current_term": current_term,
            "student_scores": student_scores,
            "max_ca": DEFAULT_TET_WEIGHT,
            "max_exam": DEFAULT_EXAM_WEIGHT,
        }
        template = resolve_school_template(school, "examinations/scores/entry.html")
        return render(request, template, context)

    def post(self, request):
        school = self.get_school()
        class_id = request.POST.get("class_id")
        arm_id = request.POST.get("arm_id") or None
        subject_id = request.POST.get("subject_id")

        school_class = get_object_or_404(SchoolClass, id=class_id, school=school)
        class_arm = get_object_or_404(ClassArm, id=arm_id, school_class=school_class) if arm_id else None
        subject = get_object_or_404(Subject, id=subject_id, school=school)

        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()

        student_ids = request.POST.getlist("student_ids")
        saved_count = 0

        for s_id in student_ids:
            student = StudentProfile.objects.filter(id=s_id, school=school).first()
            if not student:
                continue

            ca_val = request.POST.get(f"ca_{s_id}", "").strip()
            exam_val = request.POST.get(f"exam_{s_id}", "").strip()
            remarks = request.POST.get(f"remarks_{s_id}", "").strip()

            ca_score = float(ca_val) if ca_val else None
            exam_score = float(exam_val) if exam_val else None

            record_student_subject_score(
                school=school,
                student=student,
                session=current_session,
                term=current_term,
                subject=subject,
                school_class=school_class,
                class_arm=class_arm,
                ca_score=ca_score,
                exam_score=exam_score,
                teacher_remarks=remarks,
                entered_by=request.user,
            )
            saved_count += 1

        arm_suffix = f"&arm_id={class_arm.id}" if class_arm else ""
        messages.success(request, f"Scores saved successfully for {saved_count} student(s) in {subject.name}.")
        return redirect(f"/examinations/scores/?class_id={school_class.id}{arm_suffix}&subject_id={subject.id}")


class ResultApprovalView(SchoolRequiredMixin, View):
    """
    Principal / Director review and bulk approval for class results.
    """

    def get(self, request):
        school = self.get_school()
        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()
        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order")

        class_id = request.GET.get("class_id")
        selected_class = SchoolClass.objects.filter(id=class_id, school=school).first() if class_id else classes.first()

        results_summary = []
        if selected_class and current_session and current_term:
            subjects = Subject.objects.filter(school=school, is_active=True)
            for sub in subjects:
                sub_results = StudentSubjectResult.objects.filter(
                    school=school,
                    session=current_session,
                    term=current_term,
                    school_class=selected_class,
                    subject=sub,
                )
                if sub_results.exists():
                    total_count = sub_results.count()
                    approved_count = sub_results.filter(status=RESULT_STATUS_APPROVED).count()
                    results_summary.append({
                        "subject": sub,
                        "total_count": total_count,
                        "approved_count": approved_count,
                        "is_all_approved": total_count == approved_count,
                    })

        context = {
            "classes": classes,
            "selected_class": selected_class,
            "current_session": current_session,
            "current_term": current_term,
            "results_summary": results_summary,
        }
        template = resolve_school_template(school, "examinations/approvals/index.html")
        return render(request, template, context)

    def post(self, request):
        """Principal approves all scores and computes term report card metrics for the class."""
        school = self.get_school()
        class_id = request.POST.get("class_id")
        school_class = get_object_or_404(SchoolClass, id=class_id, school=school)

        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()

        # 1. Batch approve all subject scores
        count = approve_term_results(
            school=school,
            session=current_session,
            term=current_term,
            school_class=school_class,
            approved_by=request.user,
        )

        # 2. Compute rankings and report cards
        compute_term_reports_for_class(
            school=school,
            session=current_session,
            term=current_term,
            school_class=school_class,
        )

        messages.success(request, f"Successfully approved {count} subject scores and computed term rankings for {school_class.name}.")
        return redirect(f"/examinations/approvals/?class_id={school_class.id}")


class ResultPublicationView(SchoolRequiredMixin, View):
    """
    Publish or unpublish approved term results so parents and students can access them.
    """

    def post(self, request):
        school = self.get_school()
        class_id = request.POST.get("class_id") or None
        school_class = get_object_or_404(SchoolClass, id=class_id, school=school) if class_id else None

        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()

        count = publish_term_results(
            school=school,
            session=current_session,
            term=current_term,
            school_class=school_class,
        )

        target_name = school_class.name if school_class else "all classes"
        messages.success(request, f"Term results published for {target_name} ({count} subject scores).")
        return redirect("examinations:result_approval")


class ReportCardDetailView(SchoolRequiredMixin, View):
    """
    Detailed Nigerian school student term report card dossier.
    """

    def get(self, request, report_id):
        school = self.get_school()
        report = get_object_or_404(
            StudentTermReport.objects.select_related("student__user", "school_class", "class_arm", "session", "term"),
            id=report_id,
            school=school,
        )

        subject_results = (
            StudentSubjectResult.objects
            .filter(
                school=school,
                student=report.student,
                session=report.session,
                term=report.term,
            )
            .select_related("subject")
            .order_by("subject__name")
        )

        grading_scales = GradingScale.objects.filter(school=school).order_by("-min_score")

        context = {
            "report": report,
            "student": report.student,
            "subject_results": subject_results,
            "grading_scales": grading_scales,
        }
        template = resolve_school_template(school, "examinations/reports/card.html")
        return render(request, template, context)
