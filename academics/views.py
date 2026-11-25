"""
Academics views.

Covers:
- ClassListView        → List and toggle school classes (Primary 1-6, JSS, SSS)
- SessionListView      → Manage academic sessions for the school year
- SessionCreateView    → Create a new academic session
- SessionSetCurrentView → Mark a session as the current active one
- TermListView         → List terms within a session
- TermCreateView       → Add a new term to a session
- TermSetCurrentView   → Mark a term as the current active one
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.utils import timezone
from accounts.models import User, SchoolMembership
from core.constants import (
    ROLE_TEACHING_STAFF,
    ROLE_PRINCIPAL,
    ROLE_VICE_PRINCIPAL,
)
from academics.models import (
    Section,
    SchoolClass,
    ClassArm,
    AcademicSession,
    Term,
    TERM_CHOICES,
    Subject,
    StudentProfile,
    StudentEnrollment,
    TeachingAssignment,
    StudentAttendance,
    GENDER_CHOICES,
    BLOOD_GROUP_CHOICES,
    GENOTYPE_CHOICES,
    ENROLLMENT_ACTIVE,
    ATTENDANCE_STATUS_CHOICES,
    ATTENDANCE_PRESENT,
)
from academics.services import (
    seed_school_classes,
    admit_student,
    seed_default_school_subjects,
    assign_teacher,
    record_student_attendance,
    get_student_attendance_stats,
)
from schools.services import resolve_school_template


# ==============================================================================
# Helper mixin
# ==============================================================================

class SchoolRequiredMixin(LoginRequiredMixin):
    """
    Mixin that ensures the request has an active school tenant attached.
    If not (e.g. platform-level access), redirect to dashboard with a warning.
    """

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


# ==============================================================================
# Class Management
# ==============================================================================

class ClassListView(LoginRequiredMixin, View):
    """
    List all seeded classes grouped by section (Primary, JSS, SSS).
    Allows school administrators to activate or deactivate individual classes
    (e.g. a school without Primary 6 can deactivate it here).
    """

    def get(self, request):
        school = getattr(request, "school", None)
        if not school:
            messages.warning(request, "Please access this portal through a school domain.")
            return redirect("accounts:dashboard")

        # Auto-seed classes if this school hasn't been seeded yet
        if not SchoolClass.objects.filter(school=school).exists():
            seed_school_classes(school)

        sections = (
            Section.objects.filter(school=school)
            .prefetch_related(
                Prefetch("classes", queryset=SchoolClass.objects.prefetch_related("arms"))
            )
            .order_by("order")
        )

        total_classes = SchoolClass.objects.filter(school=school).count()
        active_classes = SchoolClass.objects.filter(school=school, is_active=True).count()
        inactive_classes = total_classes - active_classes

        template = resolve_school_template(school, "academics/classes.html")
        return render(request, template, {
            "sections": sections,
            "total_classes": total_classes,
            "active_classes": active_classes,
            "inactive_classes": inactive_classes,
            "current_school": school,
        })

    def post(self, request):
        """Toggle a class between active and inactive."""
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        class_id = request.POST.get("class_id")
        school_class = get_object_or_404(SchoolClass, id=class_id, school=school)

        school_class.is_active = not school_class.is_active
        school_class.save(update_fields=["is_active", "updated_at"])

        state_str = "activated" if school_class.is_active else "deactivated"
        messages.success(request, f"{school_class.name} has been {state_str}.")
        return redirect("academics:class_list")


class ClassArmCreateView(LoginRequiredMixin, View):
    """
    Create a new arm for an active school class (e.g. Arm A, Gold, Diamond).
    """

    def post(self, request, class_id):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        school_class = get_object_or_404(SchoolClass, id=class_id, school=school)
        name = request.POST.get("name", "").strip()

        if not name:
            messages.error(request, "Arm name is required (e.g. A, B, Gold).")
            return redirect("academics:class_list")

        if ClassArm.objects.filter(school_class=school_class, name__iexact=name).exists():
            messages.error(request, f"Arm '{name}' already exists for {school_class.name}.")
            return redirect("academics:class_list")

        ClassArm.objects.create(
            school=school,
            school_class=school_class,
            name=name,
        )

        messages.success(request, f"Arm '{name}' added to {school_class.name}.")
        return redirect("academics:class_list")


class ClassArmToggleView(LoginRequiredMixin, View):
    """
    Toggle active/inactive status of a class arm.
    """

    def post(self, request, arm_id):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        arm = get_object_or_404(ClassArm, id=arm_id, school=school)
        arm.is_active = not arm.is_active
        arm.save(update_fields=["is_active", "updated_at"])

        state_str = "activated" if arm.is_active else "deactivated"
        messages.success(request, f"Arm {arm.school_class.name} {arm.name} has been {state_str}.")
        return redirect("academics:class_list")


# ==============================================================================
# Academic Sessions
# ==============================================================================

class SessionListView(LoginRequiredMixin, View):
    """
    List all academic sessions for the school.
    Shows which one is current and allows setting the current session.
    """

    def get(self, request):
        school = getattr(request, "school", None)
        if not school:
            messages.warning(request, "Please access this portal through a school domain.")
            return redirect("accounts:dashboard")

        sessions = (
            AcademicSession.objects.filter(school=school)
            .prefetch_related("terms")
            .order_by("-start_date")
        )

        template = resolve_school_template(school, "academics/sessions.html")
        return render(request, template, {
            "sessions": sessions,
            "current_school": school,
        })


class SessionCreateView(LoginRequiredMixin, View):
    """
    Create a new academic session for the school.
    Accepts POST: name (e.g. 2026/2027), start_date, end_date.
    """

    def post(self, request):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        name = request.POST.get("name", "").strip()
        start_date = request.POST.get("start_date") or None
        end_date = request.POST.get("end_date") or None
        is_current = request.POST.get("is_current") in ["1", "true", "True", "on"]

        if not name:
            messages.error(request, "Session name is required (e.g. 2026/2027).")
            return redirect("academics:session_list")

        if AcademicSession.objects.filter(school=school, name=name).exists():
            messages.error(request, f"Session '{name}' already exists for this school.")
            return redirect("academics:session_list")

        AcademicSession.objects.create(
            school=school,
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
        )

        messages.success(request, f"Academic Session '{name}' created successfully.")
        return redirect("academics:session_list")


class SessionSetCurrentView(LoginRequiredMixin, View):
    """
    Mark a session as the current active session for the school.
    The model's save() automatically unmarks the previous current session.
    """

    def post(self, request, session_id):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        session = get_object_or_404(AcademicSession, id=session_id, school=school)
        session.is_current = True
        session.save()

        messages.success(request, f"'{session.name}' is now the current academic session.")
        return redirect("academics:session_list")


# ==============================================================================
# Terms
# ==============================================================================

class TermCreateView(LoginRequiredMixin, View):
    """
    Add a term (First, Second, or Third) to an existing academic session.
    """

    def post(self, request, session_id):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        session = get_object_or_404(AcademicSession, id=session_id, school=school)
        term_key = request.POST.get("term", "").strip()
        start_date = request.POST.get("start_date") or None
        end_date = request.POST.get("end_date") or None

        # Validate term key against allowed choices
        valid_keys = {k for k, _ in TERM_CHOICES}
        if term_key not in valid_keys:
            messages.error(request, "Please select a valid term (First, Second, or Third).")
            return redirect("academics:session_list")

        if Term.objects.filter(session=session, term=term_key).exists():
            term_label = dict(TERM_CHOICES).get(term_key)
            messages.error(request, f"{term_label} already exists for session '{session.name}'.")
            return redirect("academics:session_list")

        Term.objects.create(
            school=school,
            session=session,
            term=term_key,
            start_date=start_date,
            end_date=end_date,
        )

        term_label = dict(TERM_CHOICES).get(term_key)
        messages.success(request, f"{term_label} created for session '{session.name}'.")
        return redirect("academics:session_list")


class TermSetCurrentView(LoginRequiredMixin, View):
    """
    Mark a term as the current active term for the school.
    The model's save() automatically unmarks the previous current term.
    """

    def post(self, request, term_id):
        school = getattr(request, "school", None)
        if not school:
            return redirect("accounts:dashboard")

        term = get_object_or_404(Term, id=term_id, school=school)
        term.is_current = True
        term.save()

        messages.success(request, f"'{term.display_name} — {term.session.name}' is now the current term.")
        return redirect("academics:session_list")


# ==============================================================================
# Student Management
# ==============================================================================

class StudentListView(SchoolRequiredMixin, View):
    """
    List all students enrolled in the school tenant.
    Supports filtering by class, arm, gender, and status, and full-text name/ID search.
    """

    def get(self, request):
        school = self.get_school()
        search_query = request.GET.get("q", "").strip()
        class_filter = request.GET.get("class", "").strip()
        arm_filter = request.GET.get("arm", "").strip()
        gender_filter = request.GET.get("gender", "").strip()
        status_filter = request.GET.get("status", "").strip()

        students_qs = (
            StudentProfile.objects
            .filter(school=school)
            .select_related("user")
            .prefetch_related(
                Prefetch(
                    "enrollments",
                    queryset=StudentEnrollment.objects.select_related("school_class", "class_arm", "session").order_by("-created_at"),
                )
            )
            .order_by("user__last_name", "user__first_name")
        )

        if search_query:
            from django.db.models import Q
            students_qs = students_qs.filter(
                Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
                | Q(admission_number__icontains=search_query)
            )

        if gender_filter:
            students_qs = students_qs.filter(gender=gender_filter)

        if status_filter:
            if status_filter == "active":
                students_qs = students_qs.filter(is_active=True)
            elif status_filter == "inactive":
                students_qs = students_qs.filter(is_active=False)

        if class_filter:
            students_qs = students_qs.filter(enrollments__school_class_id=class_filter, enrollments__status=ENROLLMENT_ACTIVE)

        if arm_filter:
            students_qs = students_qs.filter(enrollments__class_arm_id=arm_filter, enrollments__status=ENROLLMENT_ACTIVE)

        # Metrics
        all_students = StudentProfile.objects.filter(school=school)
        total_count = all_students.count()
        active_count = all_students.filter(is_active=True).count()
        male_count = all_students.filter(gender="male", is_active=True).count()
        female_count = all_students.filter(gender="female", is_active=True).count()

        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order")
        arms = ClassArm.objects.filter(school=school, is_active=True).order_by("school_class__order", "name")

        context = {
            "students": students_qs.distinct(),
            "classes": classes,
            "arms": arms,
            "search_query": search_query,
            "class_filter": class_filter,
            "arm_filter": arm_filter,
            "gender_filter": gender_filter,
            "status_filter": status_filter,
            "total_count": total_count,
            "active_count": active_count,
            "male_count": male_count,
            "female_count": female_count,
        }

        template = resolve_school_template(school, "academics/students/list.html")
        return render(request, template, context)


class StudentCreateView(SchoolRequiredMixin, View):
    """
    Onboard and admit a brand new student.
    Generates a unique institutional Student ID adhering to the school's configured prefix.
    """

    def get(self, request):
        school = self.get_school()
        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order")
        arms = ClassArm.objects.filter(school=school, is_active=True).order_by("school_class__order", "name")
        sessions = AcademicSession.objects.filter(school=school).order_by("-is_current", "-start_date")
        current_session = sessions.filter(is_current=True).first() or sessions.first()

        context = {
            "classes": classes,
            "arms": arms,
            "sessions": sessions,
            "current_session": current_session,
            "gender_choices": GENDER_CHOICES,
            "blood_group_choices": BLOOD_GROUP_CHOICES,
            "genotype_choices": GENOTYPE_CHOICES,
        }
        template = resolve_school_template(school, "academics/students/create.html")
        return render(request, template, context)

    def post(self, request):
        school = self.get_school()

        # 1. Read Form Data
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        gender = request.POST.get("gender", "male")
        class_id = request.POST.get("school_class")
        arm_id = request.POST.get("class_arm")
        session_id = request.POST.get("session")

        date_of_birth = request.POST.get("date_of_birth") or None
        blood_group = request.POST.get("blood_group", "")
        genotype = request.POST.get("genotype", "")
        state_of_origin = request.POST.get("state_of_origin", "").strip()
        lga = request.POST.get("lga", "").strip()
        residential_address = request.POST.get("residential_address", "").strip()

        emergency_contact_name = request.POST.get("emergency_contact_name", "").strip()
        emergency_contact_phone = request.POST.get("emergency_contact_phone", "").strip()
        emergency_contact_relationship = request.POST.get("emergency_contact_relationship", "").strip()
        medical_conditions = request.POST.get("medical_conditions", "").strip()

        if not (first_name and last_name and class_id):
            messages.error(request, "First Name, Last Name, and Class are mandatory.")
            return redirect("academics:student_create")

        school_class = get_object_or_404(SchoolClass, id=class_id, school=school)
        class_arm = ClassArm.objects.filter(id=arm_id, school=school).first() if arm_id else None
        session = AcademicSession.objects.filter(id=session_id, school=school).first() if session_id else None

        try:
            student_profile, enrollment = admit_student(
                school=school,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                school_class=school_class,
                class_arm=class_arm,
                session=session,
                date_of_birth=date_of_birth,
                blood_group=blood_group,
                genotype=genotype,
                state_of_origin=state_of_origin,
                lga=lga,
                residential_address=residential_address,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                emergency_contact_relationship=emergency_contact_relationship,
                medical_conditions=medical_conditions,
            )

            messages.success(
                request,
                f"Student {first_name} {last_name} admitted successfully! "
                f"Assigned Student ID: {student_profile.admission_number}"
            )
            return redirect("academics:student_detail", student_id=student_profile.id)
        except Exception as e:
            messages.error(request, f"Error admitting student: {str(e)}")
            return redirect("academics:student_create")


class StudentDetailView(SchoolRequiredMixin, View):
    """
    Detailed student dossier including biodata, current placement, and enrollment history.
    """

    def get(self, request, student_id):
        school = self.get_school()
        student = get_object_or_404(
            StudentProfile.objects.select_related("user", "school"),
            id=student_id,
            school=school,
        )

        enrollments = (
            StudentEnrollment.objects
            .filter(student=student)
            .select_related("school_class", "class_arm", "session")
            .order_by("-session__start_date")
        )

        context = {
            "student": student,
            "enrollments": enrollments,
            "current_enrollment": student.current_enrollment,
        }
        template = resolve_school_template(school, "academics/students/detail.html")
        return render(request, template, context)


class StudentToggleStatusView(SchoolRequiredMixin, View):
    """
    Activate or deactivate a student account and profile.
    """

    def post(self, request, student_id):
        school = self.get_school()
        student = get_object_or_404(StudentProfile, id=student_id, school=school)
        student.is_active = not student.is_active
        student.save(update_fields=["is_active", "updated_at"])

        # Sync user account
        student.user.is_active = student.is_active
        student.user.save(update_fields=["is_active"])

        status_text = "activated" if student.is_active else "deactivated"
        messages.success(request, f"Student '{student.user.get_full_name()}' has been {status_text}.")
        return redirect("academics:student_detail", student_id=student.id)


# ==============================================================================
# Subject Management
# ==============================================================================

class SubjectListView(SchoolRequiredMixin, View):
    """
    List and configure academic subjects offered by the school.
    """

    def get(self, request):
        school = self.get_school()
        subjects = (
            Subject.objects
            .filter(school=school)
            .select_related("section")
            .prefetch_related("applicable_classes")
            .order_by("name")
        )
        sections = Section.objects.filter(school=school, is_active=True).order_by("order")
        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order")

        context = {
            "subjects": subjects,
            "sections": sections,
            "classes": classes,
        }
        template = resolve_school_template(school, "academics/subjects/list.html")
        return render(request, template, context)


class SubjectCreateView(SchoolRequiredMixin, View):
    """
    Create a new subject for the school.
    """

    def post(self, request):
        school = self.get_school()
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip().upper()
        section_id = request.POST.get("section")
        is_elective = request.POST.get("is_elective") == "on"
        class_ids = request.POST.getlist("applicable_classes")

        if not (name and code):
            messages.error(request, "Subject Name and Subject Code are required.")
            return redirect("academics:subject_list")

        if Subject.objects.filter(school=school, code=code).exists():
            messages.error(request, f"Subject with code '{code}' already exists in this school.")
            return redirect("academics:subject_list")

        section = Section.objects.filter(id=section_id, school=school).first() if section_id else None

        subject = Subject.objects.create(
            school=school,
            name=name,
            code=code,
            section=section,
            is_elective=is_elective,
            is_active=True,
        )

        if class_ids:
            classes = SchoolClass.objects.filter(id__in=class_ids, school=school)
            subject.applicable_classes.set(classes)

        messages.success(request, f"Subject '{name}' ({code}) created successfully.")
        return redirect("academics:subject_list")


class SubjectToggleStatusView(SchoolRequiredMixin, View):
    """
    Toggle a subject's active status.
    """

    def post(self, request, subject_id):
        school = self.get_school()
        subject = get_object_or_404(Subject, id=subject_id, school=school)
        subject.is_active = not subject.is_active
        subject.save(update_fields=["is_active", "updated_at"])

        status_text = "activated" if subject.is_active else "deactivated"
        messages.success(request, f"Subject '{subject.name}' has been {status_text}.")
        return redirect("academics:subject_list")


# ==============================================================================
# Teaching Assignments
# ==============================================================================

class TeachingAssignmentListView(SchoolRequiredMixin, View):
    """
    List and manage teaching assignments for the school's active session.
    """

    def get(self, request):
        school = self.get_school()
        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        sessions = AcademicSession.objects.filter(school=school).order_by("-start_date")
        
        session_id = request.GET.get("session")
        selected_session = None
        if session_id:
            selected_session = AcademicSession.objects.filter(id=session_id, school=school).first()
        if not selected_session:
            selected_session = current_session or sessions.first()

        assignments = (
            TeachingAssignment.objects
            .filter(school=school)
            .select_related("teacher", "subject", "school_class", "class_arm", "session")
            .order_by("school_class__order", "class_arm__name", "subject__name")
        )
        if selected_session:
            assignments = assignments.filter(session=selected_session)

        # Teachers available for assignment (Teaching staff, principal, vice principal)
        teacher_memberships = (
            SchoolMembership.objects
            .filter(
                school=school,
                role__in=[ROLE_TEACHING_STAFF, ROLE_PRINCIPAL, ROLE_VICE_PRINCIPAL],
                status="active",
            )
            .select_related("user")
            .order_by("user__last_name", "user__first_name")
        )

        classes = SchoolClass.objects.filter(school=school, is_active=True).prefetch_related("arms").order_by("order")
        subjects = Subject.objects.filter(school=school, is_active=True).order_by("name")

        context = {
            "assignments": assignments,
            "sessions": sessions,
            "selected_session": selected_session,
            "teachers": teacher_memberships,
            "classes": classes,
            "subjects": subjects,
        }
        template = resolve_school_template(school, "academics/assignments/list.html")
        return render(request, template, context)


class TeachingAssignmentCreateView(SchoolRequiredMixin, View):
    """
    Assign a teacher to one or multiple subjects, a class, and optional arm for an academic session.
    """

    def post(self, request):
        school = self.get_school()
        teacher_id = request.POST.get("teacher")
        session_id = request.POST.get("session")
        subject_ids = request.POST.getlist("subjects")
        single_subject_id = request.POST.get("subject")
        if single_subject_id and single_subject_id not in subject_ids:
            subject_ids.append(single_subject_id)

        school_class_id = request.POST.get("school_class")
        class_arm_id = request.POST.get("class_arm") or None

        if not subject_ids:
            messages.error(request, "Please select at least one subject to assign.")
            return redirect(f"/academics/assignments/?session={session_id}")

        teacher = get_object_or_404(User, id=teacher_id)
        session = get_object_or_404(AcademicSession, id=session_id, school=school)
        school_class = get_object_or_404(SchoolClass, id=school_class_id, school=school)
        class_arm = get_object_or_404(ClassArm, id=class_arm_id, school=school) if class_arm_id else None

        subjects = Subject.objects.filter(school=school, id__in=subject_ids)
        assigned_names = []
        for subject in subjects:
            assign_teacher(
                school=school,
                teacher=teacher,
                session=session,
                subject=subject,
                school_class=school_class,
                class_arm=class_arm,
            )
            assigned_names.append(subject.name)

        arm_str = f" ({class_arm.name})" if class_arm else ""
        messages.success(
            request,
            f"Assigned {teacher.get_full_name()} to teach {', '.join(assigned_names)} for {school_class.name}{arm_str} ({session.name}).",
        )
        return redirect(f"/academics/assignments/?session={session.id}")


class TeachingAssignmentToggleView(SchoolRequiredMixin, View):
    """
    Toggle teaching assignment active status.
    """

    def post(self, request, assignment_id):
        school = self.get_school()
        assignment = get_object_or_404(TeachingAssignment, id=assignment_id, school=school)
        assignment.is_active = not assignment.is_active
        assignment.save(update_fields=["is_active", "updated_at"])

        status_text = "activated" if assignment.is_active else "deactivated"
        messages.success(request, f"Assignment has been {status_text}.")
        return redirect(f"/academics/assignments/?session={assignment.session.id}")


class TeachingAssignmentDeleteView(SchoolRequiredMixin, View):
    """
    Delete a teaching assignment.
    """

    def post(self, request, assignment_id):
        school = self.get_school()
        assignment = get_object_or_404(TeachingAssignment, id=assignment_id, school=school)
        session_id = assignment.session.id
        assignment.delete()
        messages.success(request, "Teaching assignment removed successfully.")
        return redirect(f"/academics/assignments/?session={session_id}")


# ==============================================================================
# Student Attendance
# ==============================================================================

class StudentAttendanceRegisterView(SchoolRequiredMixin, View):
    """
    Daily attendance register for a specific class, arm, and date.
    Teachers and school administrators can mark attendance in single-click or bulk.
    """

    def get(self, request):
        school = self.get_school()
        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()
        
        classes = SchoolClass.objects.filter(school=school, is_active=True).prefetch_related("arms").order_by("order")
        
        class_id = request.GET.get("class_id")
        arm_id = request.GET.get("arm_id")
        date_str = request.GET.get("date")

        target_date = timezone.now().date()
        if date_str:
            try:
                target_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        selected_class = None
        if class_id:
            selected_class = SchoolClass.objects.filter(id=class_id, school=school).first()
        if not selected_class:
            selected_class = classes.first()

        selected_arm = None
        if arm_id and selected_class:
            selected_arm = ClassArm.objects.filter(id=arm_id, school_class=selected_class).first()

        # Fetch enrolled students
        students_roster = []
        if selected_class and current_session:
            enrollments = (
                StudentEnrollment.objects
                .filter(
                    school=school,
                    school_class=selected_class,
                    session=current_session,
                    status=ENROLLMENT_ACTIVE,
                )
                .select_related("student__user")
                .order_by("student__user__last_name", "student__user__first_name")
            )
            if selected_arm:
                enrollments = enrollments.filter(class_arm=selected_arm)

            # Get existing attendance for this date
            attendances = {
                att.student_id: att
                for att in StudentAttendance.objects.filter(
                    school=school,
                    date=target_date,
                    school_class=selected_class,
                )
            }

            for enr in enrollments:
                st = enr.student
                existing_att = attendances.get(st.id)
                students_roster.append({
                    "student": st,
                    "enrollment": enr,
                    "status": existing_att.status if existing_att else ATTENDANCE_PRESENT,
                    "remarks": existing_att.remarks if existing_att else "",
                })

        context = {
            "classes": classes,
            "selected_class": selected_class,
            "selected_arm": selected_arm,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "current_session": current_session,
            "current_term": current_term,
            "students_roster": students_roster,
            "attendance_choices": ATTENDANCE_STATUS_CHOICES,
        }
        template = resolve_school_template(school, "academics/attendance/register.html")
        return render(request, template, context)

    def post(self, request):
        school = self.get_school()
        class_id = request.POST.get("class_id")
        arm_id = request.POST.get("arm_id") or None
        date_str = request.POST.get("date")

        school_class = get_object_or_404(SchoolClass, id=class_id, school=school)
        class_arm = get_object_or_404(ClassArm, id=arm_id, school_class=school_class) if arm_id else None

        current_session = AcademicSession.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(school=school, is_current=True).first()

        if not (current_session and current_term):
            messages.error(request, "Please configure and set an active Academic Session and Term first.")
            return redirect("academics:attendance_register")

        try:
            target_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            target_date = timezone.now().date()

        student_ids = request.POST.getlist("student_ids")
        records = []
        for s_id in student_ids:
            status = request.POST.get(f"status_{s_id}", ATTENDANCE_PRESENT)
            remarks = request.POST.get(f"remarks_{s_id}", "")
            records.append({
                "student_id": s_id,
                "status": status,
                "remarks": remarks,
            })

        count = record_student_attendance(
            school=school,
            session=current_session,
            term=current_term,
            school_class=school_class,
            class_arm=class_arm,
            date=target_date,
            marked_by=request.user,
            attendance_records=records,
        )

        arm_suffix = f"&arm_id={class_arm.id}" if class_arm else ""
        messages.success(request, f"Attendance marked successfully for {count} student(s) on {target_date}.")
        return redirect(f"/academics/attendance/register/?class_id={school_class.id}{arm_suffix}&date={target_date}")


