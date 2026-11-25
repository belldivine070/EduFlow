"""
Admissions, Finance & School Store API v1 views and serializers.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import (
    IsActiveTenant,
    IsTenantAdmin,
    IsTenantMember,
    IsTenantStaff,
    get_active_membership,
)
from accounts.models import ParentStudentRelationship
from academics.models import AcademicSession, SchoolClass
from admissions.models import (
    AdmissionApplication,
    APPLICATION_STATUS_ADMITTED,
    APPLICATION_STATUS_REJECTED,
    APPLICATION_STATUS_UNDER_REVIEW,
)
from admissions.services import convert_applicant_to_student, submit_admission_application
from core.constants import ROLE_PARENT, ROLE_STUDENT
from finance.models import FeeStructure, Payment, StudentInvoice
from finance.services import record_payment
from store.models import Product, StoreOrder
from store.services import process_store_purchase


# ==============================================================================
# ADMISSIONS
# ==============================================================================

class AdmissionApplicationSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="applying_for_class.name", read_only=True)

    class Meta:
        model = AdmissionApplication
        fields = [
            "id",
            "application_number",
            "first_name",
            "last_name",
            "middle_name",
            "gender",
            "date_of_birth",
            "applying_for_class",
            "class_name",
            "parent_name",
            "parent_email",
            "parent_phone",
            "status",
            "created_at",
        ]


class PublicAdmissionApplyAPIView(APIView):
    """
    Public endpoint for submitting a new admission application to the current school tenant.
    """
    permission_classes = [IsActiveTenant]

    def post(self, request):
        school = request.school
        session_id = request.data.get("session_id")
        class_id = request.data.get("applying_for_class_id")
        session = (
            AcademicSession.objects.filter(school=school, id=session_id).first()
            if session_id
            else AcademicSession.objects.filter(school=school, is_current=True).first()
        )
        school_class = SchoolClass.objects.filter(school=school, id=class_id).first()
        if not session or not school_class:
            return Response(
                {"detail": "Valid academic session and target class are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            application = submit_admission_application(
                school=school,
                session=session,
                first_name=request.data.get("first_name", ""),
                last_name=request.data.get("last_name", ""),
                middle_name=request.data.get("middle_name", ""),
                gender=request.data.get("gender", "male"),
                date_of_birth=request.data.get("date_of_birth"),
                applying_for_class=school_class,
                parent_name=request.data.get("parent_name", ""),
                parent_email=request.data.get("parent_email", ""),
                parent_phone=request.data.get("parent_phone", ""),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AdmissionApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class PublicAdmissionStatusAPIView(APIView):
    """
    Public endpoint to check admission application status using application_number and parent_phone.
    """
    permission_classes = [IsActiveTenant]

    def get(self, request):
        app_number = request.query_params.get("application_number", "").strip()
        phone = request.query_params.get("parent_phone", "").strip()
        if not app_number or not phone:
            return Response(
                {"detail": "application_number and parent_phone are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        application = AdmissionApplication.objects.filter(
            school=request.school,
            application_number=app_number,
            parent_phone=phone,
        ).first()
        if not application:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdmissionApplicationSerializer(application).data)


class AdmissionApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdmissionApplicationSerializer
    permission_classes = [IsTenantAdmin]

    def get_queryset(self):
        return AdmissionApplication.objects.filter(school=self.request.school).select_related("applying_for_class")

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        application = self.get_object()
        new_status = request.data.get("status")
        if new_status not in {APPLICATION_STATUS_UNDER_REVIEW, APPLICATION_STATUS_ADMITTED, APPLICATION_STATUS_REJECTED}:
            return Response({"detail": "Invalid status transition."}, status=status.HTTP_400_BAD_REQUEST)
        application.status = new_status
        application.save(update_fields=["status", "updated_at"])
        return Response(AdmissionApplicationSerializer(application).data)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        application = self.get_object()
        try:
            student_profile = convert_applicant_to_student(application=application, converted_by=request.user)
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"admission_number": student_profile.admission_number, "status": "enrolled"})


# ==============================================================================
# FINANCE
# ==============================================================================

class FeeStructureSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    class_name = serializers.CharField(source="school_class.name", read_only=True)

    class Meta:
        model = FeeStructure
        fields = ["id", "category", "category_name", "school_class", "class_name", "session", "term", "amount", "is_compulsory"]


class StudentInvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)

    class Meta:
        model = StudentInvoice
        fields = [
            "id",
            "invoice_number",
            "student",
            "admission_number",
            "student_name",
            "session",
            "term",
            "total_amount",
            "amount_paid",
            "balance_due",
            "status",
            "due_date",
        ]


class FeeStructureViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FeeStructureSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return FeeStructure.objects.filter(school=self.request.school).select_related("category", "school_class")


class StudentInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StudentInvoiceSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        school = self.request.school
        qs = StudentInvoice.objects.filter(school=school).select_related("student__user")
        membership = get_active_membership(self.request)
        if not self.request.user.is_superuser and membership:
            if membership.role == ROLE_STUDENT:
                qs = qs.filter(student__user=self.request.user)
            elif membership.role == ROLE_PARENT:
                child_ids = ParentStudentRelationship.objects.filter(
                    school=school, parent=self.request.user
                ).values_list("student_id", flat=True)
                qs = qs.filter(student_id__in=child_ids)
        return qs

    @action(detail=True, methods=["post"], permission_classes=[IsTenantAdmin])
    def pay(self, request, pk=None):
        invoice = self.get_object()
        try:
            amount = Decimal(str(request.data.get("amount", "0")))
        except Exception:
            return Response({"detail": "Invalid payment amount."}, status=status.HTTP_400_BAD_REQUEST)
        method = request.data.get("payment_method", "cash")
        try:
            payment = record_payment(
                invoice=invoice,
                amount=amount,
                payment_method=method,
                recorded_by=request.user,
            )
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "receipt_number": payment.receipt_number,
                "amount": str(payment.amount),
                "invoice_status": invoice.status,
                "remaining_balance": str(invoice.balance_due),
            },
            status=status.HTTP_201_CREATED,
        )


# ==============================================================================
# SCHOOL STORE
# ==============================================================================

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "sku", "category", "category_name", "price", "stock_quantity", "is_active"]


class StoreOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreOrder
        fields = ["id", "order_number", "customer_name", "student", "total_amount", "payment_method", "status", "created_at"]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Product.objects.filter(school=self.request.school, is_active=True).select_related("category")


class StoreOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StoreOrderSerializer
    permission_classes = [IsTenantStaff]

    def get_queryset(self):
        return StoreOrder.objects.filter(school=self.request.school)

    @action(detail=False, methods=["post"])
    def pos(self, request):
        items = request.data.get("items", [])
        customer_name = request.data.get("customer_name") or request.data.get("buyer_name", "Walk-in Customer")
        payment_method = request.data.get("payment_method", "cash")
        if not isinstance(items, list) or not items:
            return Response({"detail": "Provide a non-empty 'items' list."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order = process_store_purchase(
                school=request.school,
                items_data=items,
                customer_name=customer_name,
                payment_method=payment_method,
                user=request.user,
            )
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StoreOrderSerializer(order).data, status=status.HTTP_201_CREATED)
