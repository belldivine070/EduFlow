"""
Finance data models.

Supports:
- Fee categories and class/session-based fee structures.
- Student invoices with line items and balance tracking.
- Multi-channel payments (Paystack, Bank Transfer, Cash, POS).
- Server-side Paystack transaction verification and idempotent receipt generation.
- Official printable payment receipts and financial audits.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from core.models import TimestampedModel

INVOICE_STATUS_PENDING = "pending"
INVOICE_STATUS_PARTIALLY_PAID = "partially_paid"
INVOICE_STATUS_PAID = "paid"
INVOICE_STATUS_OVERDUE = "overdue"
INVOICE_STATUS_CANCELLED = "cancelled"

INVOICE_STATUS_CHOICES = [
    (INVOICE_STATUS_PENDING, "Pending"),
    (INVOICE_STATUS_PARTIALLY_PAID, "Partially Paid"),
    (INVOICE_STATUS_PAID, "Fully Paid"),
    (INVOICE_STATUS_OVERDUE, "Overdue"),
    (INVOICE_STATUS_CANCELLED, "Cancelled"),
]

PAYMENT_METHOD_PAYSTACK = "paystack"
PAYMENT_METHOD_BANK_TRANSFER = "bank_transfer"
PAYMENT_METHOD_CASH = "cash"
PAYMENT_METHOD_POS = "pos"

PAYMENT_METHOD_CHOICES = [
    (PAYMENT_METHOD_PAYSTACK, "Paystack Online"),
    (PAYMENT_METHOD_BANK_TRANSFER, "Bank Transfer"),
    (PAYMENT_METHOD_CASH, "Cash"),
    (PAYMENT_METHOD_POS, "POS Terminal"),
]

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_SUCCESSFUL = "successful"
PAYMENT_STATUS_FAILED = "failed"
PAYMENT_STATUS_CANCELLED = "cancelled"
PAYMENT_STATUS_REFUNDED = "refunded"

PAYMENT_STATUS_CHOICES = [
    (PAYMENT_STATUS_PENDING, "Pending"),
    (PAYMENT_STATUS_SUCCESSFUL, "Successful"),
    (PAYMENT_STATUS_FAILED, "Failed"),
    (PAYMENT_STATUS_CANCELLED, "Cancelled"),
    (PAYMENT_STATUS_REFUNDED, "Refunded"),
]


class FeeCategory(TimestampedModel):
    """
    Broad category of school fees (e.g. Tuition, Development Levy, Exam Fee, Uniform, PTA).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="fee_categories",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fee Category"
        verbose_name_plural = "Fee Categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_school_fee_category")
        ]

    def __str__(self):
        return f"{self.name} ({self.school.code})"


class FeeStructure(TimestampedModel):
    """
    Configured pricing rule per academic session, term, and target class.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="fee_structures",
    )
    category = models.ForeignKey(
        FeeCategory,
        on_delete=models.CASCADE,
        related_name="structures",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="fee_structures",
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fee_structures",
        help_text="Leave blank if fee applies to entire session.",
    )
    school_class = models.ForeignKey(
        "academics.SchoolClass",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fee_structures",
        help_text="Leave blank if fee applies to all classes.",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_compulsory = models.BooleanField(default=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Fee Structure"
        verbose_name_plural = "Fee Structures"
        ordering = ["category", "school_class"]

    def __str__(self):
        cls_name = self.school_class.name if self.school_class else "All Classes"
        term_name = f" - {self.term.display_name}" if self.term else ""
        return f"{self.category.name} ({cls_name}{term_name}): ₦{self.amount:,.2f}"


class StudentInvoice(TimestampedModel):
    """
    Official invoice issued to a student for a session/term.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    session = models.ForeignKey(
        "academics.AcademicSession",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    invoice_number = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Format: {SCHOOL_CODE}-INV-{YEAR}-{SEQ}",
    )
    title = models.CharField(max_length=200)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS_CHOICES,
        default=INVOICE_STATUS_PENDING,
        db_index=True,
    )
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_invoices",
    )

    class Meta:
        verbose_name = "Student Invoice"
        verbose_name_plural = "Student Invoices"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["school", "invoice_number"], name="unique_school_invoice_number")
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.student.admission_number} (₦{self.total_amount:,.2f})"

    @property
    def balance_due(self) -> Decimal:
        bal = self.total_amount - self.amount_paid
        return bal if bal > Decimal("0.00") else Decimal("0.00")

    def update_payment_totals(self):
        """Recalculate paid amount and invoice status based on successful payments."""
        successful_sum = self.payments.filter(status=PAYMENT_STATUS_SUCCESSFUL).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")
        self.amount_paid = successful_sum

        if self.amount_paid >= self.total_amount and self.total_amount > Decimal("0.00"):
            self.status = INVOICE_STATUS_PAID
        elif self.amount_paid > Decimal("0.00"):
            self.status = INVOICE_STATUS_PARTIALLY_PAID
        elif self.due_date and self.due_date < timezone.now().date():
            self.status = INVOICE_STATUS_OVERDUE
        else:
            self.status = INVOICE_STATUS_PENDING
        self.save(update_fields=["amount_paid", "status", "updated_at"])


class InvoiceItem(TimestampedModel):
    """
    Line item belonging to a StudentInvoice.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        StudentInvoice,
        on_delete=models.CASCADE,
        related_name="items",
    )
    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items",
    )
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = "Invoice Item"
        verbose_name_plural = "Invoice Items"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.description}: ₦{self.amount:,.2f}"


class Payment(TimestampedModel):
    """
    Transaction record of a payment made against an invoice.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    invoice = models.ForeignKey(
        StudentInvoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    reference = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Unique verifiable transaction reference (Paystack ref or internal ID).",
    )
    receipt_number = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Format: {SCHOOL_CODE}-REC-{YEAR}-{SEQ}",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_METHOD_PAYSTACK)
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_PENDING,
        db_index=True,
    )
    paid_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_payments",
    )
    gateway_response = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-paid_at"]
        constraints = [
            models.UniqueConstraint(fields=["school", "reference"], name="unique_school_payment_reference"),
            models.UniqueConstraint(fields=["school", "receipt_number"], name="unique_school_payment_receipt"),
        ]

    def __str__(self):
        return f"{self.receipt_number} - ₦{self.amount:,.2f} ({self.get_status_display()})"
