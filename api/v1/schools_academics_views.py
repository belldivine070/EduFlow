"""
Schools & Academics API v1 views and serializers.
"""
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import (
    IsActiveTenant,
    IsTenantAdmin,
    IsTenantMember,
    IsTenantTeachingStaff,
    get_active_membership,
)
from accounts.models import ParentStudentRelationship
from academics.models import (
    AcademicSession,
    ClassArm,
    SchoolClass,
    StudentAttendance,
    StudentEnrollment,
    StudentProfile,
    Subject,
    Term,
)
from core.constants import ROLE_PARENT, ROLE_STUDENT


class CurrentSchoolAPIView(APIView):
    """
    Returns public tenant metadata for the school resolved from the request hostname.
    """
    permission_classes = [IsActiveTenant]

    def get(self, request):
        school = request.school
        return Response(
            {
                "id": str(school.id),
                "name": school.name,
                "code": school.code,
                "slug": school.slug,
                "motto": school.motto,
                "student_id_prefix": school.student_id_prefix,
                "is_active": school.is_active,
            }
        )


class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = ["id", "name", "start_date", "end_date", "is_current"]


class TermSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Term
        fields = ["id", "session", "term", "display_name", "start_date", "end_date", "is_current"]


class ClassArmSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassArm
        fields = ["id", "name", "school_class"]


class SchoolClassSerializer(serializers.ModelSerializer):
    arms = ClassArmSerializer(many=True, read_only=True)

    class Meta:
        model = SchoolClass
        fields = ["id", "name", "order", "section", "arms"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "code", "section", "is_elective"]


class StudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "admission_number",
            "full_name",
            "email",
            "gender",
            "date_of_birth",
            "admission_date",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class StudentAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)

    class Meta:
        model = StudentAttendance
        fields = [
            "id",
            "student",
            "admission_number",
            "student_name",
            "session",
            "term",
            "school_class",
            "class_arm",
            "date",
            "status",
            "remark",
        ]


class AcademicSessionViewSet(viewsets.ModelViewSet):
    serializer_class = AcademicSessionSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsTenantMember()]
        return [IsTenantAdmin()]

    def get_queryset(self):
        return AcademicSession.objects.filter(school=self.request.school)

    def perform_create(self, serializer):
        serializer.save(school=self.request.school)


class TermViewSet(viewsets.ModelViewSet):
    serializer_class = TermSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsTenantMember()]
        return [IsTenantAdmin()]

    def get_queryset(self):
        return Term.objects.filter(school=self.request.school).select_related("session")

    def perform_create(self, serializer):
        serializer.save(school=self.request.school)


class SchoolClassViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SchoolClassSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return SchoolClass.objects.filter(school=self.request.school).prefetch_related("arms")


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Subject.objects.filter(school=self.request.school)


class StudentProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StudentProfileSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        school = self.request.school
        qs = StudentProfile.objects.filter(school=school).select_related("user")
        if self.request.user.is_superuser:
            return qs
        membership = get_active_membership(self.request)
        if not membership:
            return qs.none()
        if membership.role == ROLE_STUDENT:
            return qs.filter(user=self.request.user)
        if membership.role == ROLE_PARENT:
            child_ids = ParentStudentRelationship.objects.filter(
                school=school, parent=self.request.user
            ).values_list("student_id", flat=True)
            return qs.filter(id__in=child_ids)
        return qs


class StudentAttendanceAPIView(APIView):
    """
    List student attendance (scoped by role) or mark attendance (teaching staff+).
    """
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsTenantMember()]
        return [IsTenantTeachingStaff()]

    def get(self, request):
        school = request.school
        qs = StudentAttendance.objects.filter(school=school).select_related("student__user")
        membership = get_active_membership(request)
        if not request.user.is_superuser and membership:
            if membership.role == ROLE_STUDENT:
                qs = qs.filter(student__user=request.user)
            elif membership.role == ROLE_PARENT:
                child_ids = ParentStudentRelationship.objects.filter(
                    school=school, parent=request.user
                ).values_list("student_id", flat=True)
                qs = qs.filter(student_id__in=child_ids)

        date_param = request.query_params.get("date")
        class_id = request.query_params.get("school_class")
        if date_param:
            qs = qs.filter(date=date_param)
        if class_id:
            qs = qs.filter(school_class_id=class_id)

        serializer = StudentAttendanceSerializer(qs[:100], many=True)
        return Response(serializer.data)

    def post(self, request):
        school = request.school
        records = request.data.get("records", [])
        if not isinstance(records, list) or not records:
            return Response(
                {"detail": "Provide a non-empty 'records' list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = 0
        for item in records:
            student_id = item.get("student_id")
            date_val = item.get("date")
            att_status = item.get("status", "present")
            remark = item.get("remark", "")
            session_id = item.get("session_id")
            term_id = item.get("term_id")
            school_class_id = item.get("school_class_id")
            if not (student_id and date_val and session_id and term_id and school_class_id):
                continue
            StudentAttendance.objects.update_or_create(
                school=school,
                student_id=student_id,
                date=date_val,
                defaults={
                    "session_id": session_id,
                    "term_id": term_id,
                    "school_class_id": school_class_id,
                    "status": att_status,
                    "remark": remark,
                    "recorded_by": request.user,
                },
            )
            updated += 1
        return Response({"updated": updated}, status=status.HTTP_200_OK)
