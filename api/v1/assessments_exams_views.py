"""
Assessments & Examinations API v1 views and serializers.
"""
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import IsTenantMember, IsTenantTeachingStaff, get_active_membership
from accounts.models import ParentStudentRelationship
from assessments.models import Assessment
from core.constants import ROLE_PARENT, ROLE_STUDENT
from examinations.models import (
    RESULT_STATUS_PUBLISHED,
    StudentSubjectResult,
    StudentTermReport,
)


class AssessmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    class_name = serializers.CharField(source="school_class.name", read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "subject",
            "subject_name",
            "school_class",
            "class_name",
            "session",
            "term",
            "duration_minutes",
            "total_marks",
            "pass_mark",
            "is_published",
            "start_time",
            "end_time",
        ]


class StudentSubjectResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = StudentSubjectResult
        fields = [
            "id",
            "student",
            "student_name",
            "subject",
            "subject_name",
            "session",
            "term",
            "ca_score",
            "exam_score",
            "total_score",
            "grade",
            "status",
        ]


class StudentTermReportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    class_name = serializers.CharField(source="school_class.name", read_only=True)

    class Meta:
        model = StudentTermReport
        fields = [
            "id",
            "student",
            "admission_number",
            "student_name",
            "school_class",
            "class_name",
            "session",
            "term",
            "total_subjects",
            "total_obtained_score",
            "total_obtainable_score",
            "average_score",
            "class_rank",
            "class_size",
            "attendance_days_present",
            "attendance_days_absent",
            "attendance_percentage",
            "class_teacher_remarks",
            "principal_remarks",
            "status",
            "published_at",
        ]


class AssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssessmentSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        school = self.request.school
        qs = Assessment.objects.filter(school=school).select_related("subject", "school_class")
        membership = get_active_membership(self.request)
        if not self.request.user.is_superuser and membership:
            if membership.role in {ROLE_STUDENT, ROLE_PARENT}:
                qs = qs.filter(is_published=True)
        return qs


class ExamResultListAPIView(APIView):
    """
    Returns subject results.
    Students & Parents see ONLY published results for themselves/their children.
    Teaching staff & Admins can view all results for the school.
    """
    permission_classes = [IsTenantMember]

    def get(self, request):
        school = request.school
        qs = StudentSubjectResult.objects.filter(school=school).select_related("student__user", "subject")
        membership = get_active_membership(request)
        if not request.user.is_superuser and membership:
            if membership.role == ROLE_STUDENT:
                qs = qs.filter(student__user=request.user, status=RESULT_STATUS_PUBLISHED)
            elif membership.role == ROLE_PARENT:
                child_ids = ParentStudentRelationship.objects.filter(
                    school=school, parent=request.user
                ).values_list("student_id", flat=True)
                qs = qs.filter(student_id__in=child_ids, status=RESULT_STATUS_PUBLISHED)

        term_id = request.query_params.get("term")
        if term_id:
            qs = qs.filter(term_id=term_id)
        return Response(StudentSubjectResultSerializer(qs[:100], many=True).data)


class ReportCardListAPIView(APIView):
    """
    Returns termly student report cards.
    Students & Parents see ONLY published report cards for themselves/their children.
    """
    permission_classes = [IsTenantMember]

    def get(self, request):
        school = request.school
        qs = StudentTermReport.objects.filter(school=school).select_related("student__user", "school_class")
        membership = get_active_membership(request)
        if not request.user.is_superuser and membership:
            if membership.role == ROLE_STUDENT:
                qs = qs.filter(student__user=request.user, status=RESULT_STATUS_PUBLISHED)
            elif membership.role == ROLE_PARENT:
                child_ids = ParentStudentRelationship.objects.filter(
                    school=school, parent=request.user
                ).values_list("student_id", flat=True)
                qs = qs.filter(student_id__in=child_ids, status=RESULT_STATUS_PUBLISHED)

        return Response(StudentTermReportSerializer(qs[:100], many=True).data)
