"""
Admissions views.
Handles public tenant-scoped admissions application, status tracking,
official admission letter rendering, and staff admissions management/onboarding.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.core.exceptions import ValidationError

from schools.services import resolve_school_template
from academics.models import AcademicSession, SchoolClass, ClassArm
from admissions.models import (
    AdmissionApplication,
    ApplicationDocument,
    APPLICATION_STATUS_PENDING,
    APPLICATION_STATUS_UNDER_REVIEW,
    APPLICATION_STATUS_INTERVIEW_SCHEDULED,
    APPLICATION_STATUS_ADMITTED,
    APPLICATION_STATUS_REJECTED,
    APPLICATION_STATUS_ENROLLED,
    DOCUMENT_TYPE_CHOICES,
)
from admissions.services import (
    submit_admission_application,
    convert_applicant_to_student,
)


class SchoolRequiredMixin(LoginRequiredMixin):
    """
    Ensures the request has an active school tenant attached.
    """
    def get_school(self):
        return getattr(self.request, "school", None)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        school = self.get_school()
        if not school:
            messages.warning(request, "Please access admissions through a verified school domain.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class PublicApplyView(View):
    """
    Public admissions application form.
    Scoped to the current school tenant from request.school.
    """
    def get(self, request):
        school = getattr(request, "school", None)
        if not school:
            return render(request, "schools/default/admissions/no_school.html", status=400)

        sessions = AcademicSession.objects.filter(school=school).order_by("-start_date")
        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order", "name")

        template = resolve_school_template(school, "admissions/apply.html")
        return render(request, template, {
            "school": school,
            "sessions": sessions,
            "classes": classes,
            "document_types": DOCUMENT_TYPE_CHOICES,
        })

    def post(self, request):
        school = getattr(request, "school", None)
        if not school:
            return render(request, "schools/default/admissions/no_school.html", status=400)

        session_id = request.POST.get("session_id")
        class_id = request.POST.get("class_id")

        session = get_object_or_404(AcademicSession, id=session_id, school=school)
        school_class = get_object_or_404(SchoolClass, id=class_id, school=school)

        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        middle_name = request.POST.get("middle_name", "").strip()
        gender = request.POST.get("gender", "male")
        date_of_birth = request.POST.get("date_of_birth")
        state_of_origin = request.POST.get("state_of_origin", "").strip()
        lga = request.POST.get("lga", "").strip()
        residential_address = request.POST.get("residential_address", "").strip()
        previous_school = request.POST.get("previous_school", "").strip()
        medical_conditions = request.POST.get("medical_conditions", "").strip()

        parent_name = request.POST.get("parent_name", "").strip()
        parent_email = request.POST.get("parent_email", "").strip()
        parent_phone = request.POST.get("parent_phone", "").strip()
        parent_relationship = request.POST.get("parent_relationship", "Father").strip()
        parent_address = request.POST.get("parent_address", "").strip()

        if not first_name or not last_name or not date_of_birth or not parent_name or not parent_phone:
            messages.error(request, "Please fill in all required fields marked with *.")
            sessions = AcademicSession.objects.filter(school=school).order_by("-start_date")
            classes = SchoolClass.objects.filter(school=school, is_active=True)
            template = resolve_school_template(school, "admissions/apply.html")
            return render(request, template, {
                "school": school,
                "sessions": sessions,
                "classes": classes,
                "document_types": DOCUMENT_TYPE_CHOICES,
                "form_data": request.POST,
            }, status=400)

        # Collect uploaded documents
        documents = []
        for file_key in request.FILES:
            if file_key.startswith("document_"):
                doc_type = file_key.replace("document_", "")
                doc_file = request.FILES[file_key]
                documents.append({
                    "document_type": doc_type,
                    "file": doc_file,
                    "original_filename": doc_file.name,
                })

        application = submit_admission_application(
            school=school,
            session=session,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            gender=gender,
            date_of_birth=date_of_birth,
            applying_for_class=school_class,
            state_of_origin=state_of_origin,
            lga=lga,
            residential_address=residential_address,
            previous_school=previous_school,
            medical_conditions=medical_conditions,
            parent_name=parent_name,
            parent_email=parent_email,
            parent_phone=parent_phone,
            parent_relationship=parent_relationship,
            parent_address=parent_address,
            documents=documents,
        )

        request.session["latest_application_number"] = application.application_number
        return redirect("admissions:apply_success")


class ApplySuccessView(View):
    """
    Confirmation screen after successful public application submission.
    """
    def get(self, request):
        school = getattr(request, "school", None)
        app_number = request.session.get("latest_application_number", "")
        template = resolve_school_template(school, "admissions/apply_success.html")
        return render(request, template, {
            "school": school,
            "application_number": app_number,
        })


class ApplicationStatusLookupView(View):
    """
    Public tracking view for applicants to check their admission progress.
    """
    def get(self, request):
        school = getattr(request, "school", None)
        template = resolve_school_template(school, "admissions/status.html")
        return render(request, template, {"school": school})

    def post(self, request):
        school = getattr(request, "school", None)
        app_number = request.POST.get("application_number", "").strip().upper()
        phone_or_email = request.POST.get("phone_or_email", "").strip()

        template = resolve_school_template(school, "admissions/status.html")
        context = {"school": school, "searched": True, "app_number": app_number, "phone_or_email": phone_or_email}

        if not app_number or not phone_or_email:
            messages.error(request, "Please enter both your Application Number and Parent Phone/Email.")
            return render(request, template, context, status=400)

        qs = AdmissionApplication.objects.filter(school=school, application_number=app_number)
        application = qs.filter(parent_phone=phone_or_email).first() or qs.filter(parent_email__iexact=phone_or_email).first()

        if not application:
            messages.error(request, "No matching application found. Please verify your reference number and contact info.")
            return render(request, template, context, status=404)

        context["application"] = application
        return render(request, template, context)


class AdmissionLetterView(View):
    """
    Printable Official Admission Letter.
    """
    def get(self, request, pk):
        school = getattr(request, "school", None)
        application = get_object_or_404(AdmissionApplication, id=pk, school=school)

        # Allow access if staff or if applicant verified
        is_staff = request.user.is_authenticated and hasattr(request.user, "memberships") and request.user.memberships.filter(school=school).exists()
        auth_app_num = request.session.get("latest_application_number", "")

        if not is_staff and auth_app_num != application.application_number and application.status not in [APPLICATION_STATUS_ADMITTED, APPLICATION_STATUS_ENROLLED]:
            messages.error(request, "You are not authorized to view this admission letter.")
            return redirect("admissions:status")

        template = resolve_school_template(school, "admissions/letter.html")
        return render(request, template, {
            "school": school,
            "application": application,
            "current_date": timezone.now().date(),
        })


class AdmissionApplicationListView(SchoolRequiredMixin, View):
    """
    Staff portal: List and filter all admission applications.
    """
    def get(self, request):
        school = self.get_school()
        status_filter = request.GET.get("status", "")
        class_filter = request.GET.get("class_id", "")
        search_query = request.GET.get("q", "").strip()

        applications = AdmissionApplication.objects.filter(school=school).select_related(
            "session", "applying_for_class", "enrolled_student", "reviewed_by"
        )

        if status_filter:
            applications = applications.filter(status=status_filter)
        if class_filter:
            applications = applications.filter(applying_for_class_id=class_filter)
        if search_query:
            applications = applications.filter(
                first_name__icontains=search_query
            ) | applications.filter(
                last_name__icontains=search_query
            ) | applications.filter(
                application_number__icontains=search_query
            ) | applications.filter(
                parent_phone__icontains=search_query
            )

        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order", "name")

        template = resolve_school_template(school, "admissions/admin/list.html")
        return render(request, template, {
            "school": school,
            "applications": applications,
            "classes": classes,
            "status_filter": status_filter,
            "class_filter": class_filter,
            "search_query": search_query,
            "status_choices": AdmissionApplication.status.field.choices,
        })


class AdmissionApplicationDetailView(SchoolRequiredMixin, View):
    """
    Staff portal: View full application profile, documents, review actions.
    """
    def get(self, request, pk):
        school = self.get_school()
        application = get_object_or_404(
            AdmissionApplication.objects.select_related(
                "session", "applying_for_class", "enrolled_student", "reviewed_by"
            ).prefetch_related("documents"),
            id=pk,
            school=school,
        )

        arms = ClassArm.objects.filter(school_class=application.applying_for_class, is_active=True)

        template = resolve_school_template(school, "admissions/admin/detail.html")
        return render(request, template, {
            "school": school,
            "application": application,
            "arms": arms,
            "status_choices": AdmissionApplication.status.field.choices,
        })


class AdmissionApplicationDecisionView(SchoolRequiredMixin, View):
    """
    Staff portal: Update application review status, notes, interview date.
    """
    def post(self, request, pk):
        school = self.get_school()
        application = get_object_or_404(AdmissionApplication, id=pk, school=school)

        new_status = request.POST.get("status")
        interview_date = request.POST.get("interview_date")
        decision_notes = request.POST.get("decision_notes", "").strip()

        valid_statuses = [
            APPLICATION_STATUS_PENDING,
            APPLICATION_STATUS_UNDER_REVIEW,
            APPLICATION_STATUS_INTERVIEW_SCHEDULED,
            APPLICATION_STATUS_ADMITTED,
            APPLICATION_STATUS_REJECTED,
        ]

        if new_status in valid_statuses:
            application.status = new_status
            application.decision_notes = decision_notes
            application.reviewed_by = request.user
            application.decision_date = timezone.now()

            if interview_date and new_status == APPLICATION_STATUS_INTERVIEW_SCHEDULED:
                application.interview_date = interview_date

            application.save()
            messages.success(request, f"Application {application.application_number} updated to {application.get_status_display()}.")
        else:
            messages.error(request, "Invalid decision status.")

        return redirect("admissions:admin_detail", pk=application.id)


class AdmissionApplicationConvertView(SchoolRequiredMixin, View):
    """
    Staff portal: Convert an admitted applicant into an official enrolled student.
    """
    def post(self, request, pk):
        school = self.get_school()
        application = get_object_or_404(AdmissionApplication, id=pk, school=school)

        class_arm_id = request.POST.get("class_arm_id")
        class_arm = None
        if class_arm_id:
            class_arm = ClassArm.objects.filter(id=class_arm_id, school_class=application.applying_for_class).first()

        try:
            student_profile, enrollment, parent_rel = convert_applicant_to_student(
                application,
                class_arm=class_arm,
                admitted_by=request.user,
            )
            messages.success(
                request,
                f"Applicant successfully converted! Generated Student ID: {student_profile.admission_number}. "
                f"Linked Parent User: {parent_rel.parent.username}."
            )
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
        except Exception as e:
            messages.error(request, f"Failed to convert applicant: {str(e)}")

        return redirect("admissions:admin_detail", pk=application.id)
