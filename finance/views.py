"""
Finance views.

Handles fee structures, student invoices (individual & bulk generation),
offline/online payment recording, Paystack server verification,
printable official payment receipts, and revenue summaries.
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q

from schools.services import resolve_school_template
from academics.models import AcademicSession, Term, SchoolClass, StudentProfile
from finance.models import (
    FeeCategory,
    FeeStructure,
    StudentInvoice,
    Payment,
    INVOICE_STATUS_CHOICES,
    PAYMENT_METHOD_CHOICES,
    PAYMENT_METHOD_PAYSTACK,
    PAYMENT_STATUS_SUCCESSFUL,
)
from finance.services import (
    create_student_invoice,
    generate_class_invoices,
    record_payment,
    verify_paystack_transaction,
)


class SchoolRequiredMixin(LoginRequiredMixin):
    def get_school(self):
        return getattr(self.request, "school", None)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        school = self.get_school()
        if not school:
            messages.warning(request, "Please access finance through a verified school domain.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class FeeStructureListView(SchoolRequiredMixin, View):
    """
    List and configure fee categories and class/session pricing structures.
    """
    def get(self, request):
        school = self.get_school()
        categories = FeeCategory.objects.filter(school=school)
        structures = FeeStructure.objects.filter(school=school).select_related(
            "category", "session", "term", "school_class"
        )
        sessions = AcademicSession.objects.filter(school=school).order_by("-start_date")
        terms = Term.objects.filter(session__school=school)
        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order", "name")

        template = resolve_school_template(school, "finance/structures.html")
        return render(request, template, {
            "school": school,
            "categories": categories,
            "structures": structures,
            "sessions": sessions,
            "terms": terms,
            "classes": classes,
        })

    def post(self, request):
        school = self.get_school()
        action = request.POST.get("action")

        if action == "create_category":
            name = request.POST.get("name", "").strip()
            desc = request.POST.get("description", "").strip()
            if name:
                FeeCategory.objects.get_or_create(
                    school=school,
                    name=name,
                    defaults={"description": desc},
                )
                messages.success(request, f"Fee category '{name}' created.")
            else:
                messages.error(request, "Category name is required.")

        elif action == "create_structure":
            cat_id = request.POST.get("category_id")
            session_id = request.POST.get("session_id")
            term_id = request.POST.get("term_id")
            class_id = request.POST.get("class_id")
            amount_str = request.POST.get("amount", "0")
            due_date = request.POST.get("due_date") or None

            try:
                category = get_object_or_404(FeeCategory, id=cat_id, school=school)
                session = get_object_or_404(AcademicSession, id=session_id, school=school)
                term = Term.objects.filter(id=term_id, session__school=school).first() if term_id else None
                school_class = SchoolClass.objects.filter(id=class_id, school=school).first() if class_id else None
                amount = Decimal(amount_str)

                FeeStructure.objects.create(
                    school=school,
                    category=category,
                    session=session,
                    term=term,
                    school_class=school_class,
                    amount=amount,
                    due_date=due_date,
                )
                messages.success(request, "Fee structure configured successfully.")
            except Exception as e:
                messages.error(request, f"Failed to configure fee structure: {str(e)}")

        return redirect("finance:fee_structures")


class InvoiceListView(SchoolRequiredMixin, View):
    """
    List student invoices, aggregate revenue metrics, and filter by status/class.
    """
    def get(self, request):
        school = self.get_school()
        status_filter = request.GET.get("status", "")
        class_filter = request.GET.get("class_id", "")
        search_query = request.GET.get("q", "").strip()

        invoices = StudentInvoice.objects.filter(school=school).select_related(
            "student__user", "session", "term"
        )

        if status_filter:
            invoices = invoices.filter(status=status_filter)
        if search_query:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search_query) |
                Q(student__admission_number__icontains=search_query) |
                Q(student__user__first_name__icontains=search_query) |
                Q(student__user__last_name__icontains=search_query)
            )

        # Revenue Metrics
        total_billed = StudentInvoice.objects.filter(school=school).aggregate(s=Sum("total_amount"))["s"] or Decimal("0.00")
        total_collected = StudentInvoice.objects.filter(school=school).aggregate(s=Sum("amount_paid"))["s"] or Decimal("0.00")
        total_outstanding = max(Decimal("0.00"), total_billed - total_collected)

        classes = SchoolClass.objects.filter(school=school, is_active=True).order_by("order", "name")
        sessions = AcademicSession.objects.filter(school=school).order_by("-start_date")
        terms = Term.objects.filter(session__school=school)

        template = resolve_school_template(school, "finance/invoices/list.html")
        return render(request, template, {
            "school": school,
            "invoices": invoices[:100],
            "classes": classes,
            "sessions": sessions,
            "terms": terms,
            "total_billed": total_billed,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "status_filter": status_filter,
            "class_filter": class_filter,
            "search_query": search_query,
            "status_choices": INVOICE_STATUS_CHOICES,
        })


class ClassInvoiceBulkGenerateView(SchoolRequiredMixin, View):
    """
    Bulk generates invoices for all students in a target class.
    """
    def post(self, request):
        school = self.get_school()
        class_id = request.POST.get("class_id")
        session_id = request.POST.get("session_id")
        term_id = request.POST.get("term_id")
        due_date = request.POST.get("due_date") or None

        school_class = get_object_or_404(SchoolClass, id=class_id, school=school)
        session = get_object_or_404(AcademicSession, id=session_id, school=school)
        term = Term.objects.filter(id=term_id, session__school=school).first() if term_id else None

        try:
            created = generate_class_invoices(
                school=school,
                school_class=school_class,
                session=session,
                term=term,
                due_date=due_date,
                created_by=request.user,
            )
            messages.success(request, f"Generated {len(created)} invoices for students in {school_class.name}.")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
        except Exception as e:
            messages.error(request, f"Failed to generate class invoices: {str(e)}")

        return redirect("finance:invoice_list")


class InvoiceDetailView(SchoolRequiredMixin, View):
    """
    Detailed invoice view showing line items, payment history, and payment recording form.
    """
    def get(self, request, pk):
        school = self.get_school()
        invoice = get_object_or_404(
            StudentInvoice.objects.select_related("student__user", "session", "term").prefetch_related("items", "payments"),
            id=pk,
            school=school,
        )

        template = resolve_school_template(school, "finance/invoices/detail.html")
        return render(request, template, {
            "school": school,
            "invoice": invoice,
            "payment_methods": PAYMENT_METHOD_CHOICES,
        })


class PaymentRecordView(SchoolRequiredMixin, View):
    """
    Staff portal: Record an offline payment (Cash, Bank Transfer, POS) against an invoice.
    """
    def post(self, request, pk):
        school = self.get_school()
        invoice = get_object_or_404(StudentInvoice, id=pk, school=school)

        amount_str = request.POST.get("amount", "0")
        method = request.POST.get("method", "cash")
        reference = request.POST.get("reference", "").strip()

        try:
            amount = Decimal(amount_str)
            payment = record_payment(
                school=school,
                invoice=invoice,
                amount=amount,
                method=method,
                reference=reference or None,
                recorded_by=request.user,
                status=PAYMENT_STATUS_SUCCESSFUL,
            )
            messages.success(
                request,
                f"Payment of ₦{payment.amount:,.2f} recorded successfully! Receipt #{payment.receipt_number}."
            )
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
        except Exception as e:
            messages.error(request, f"Failed to record payment: {str(e)}")

        return redirect("finance:invoice_detail", pk=invoice.id)


class PaystackVerifyView(View):
    """
    Server-side verification endpoint for online Paystack transactions.
    Can be called via GET query params ?reference=... or POST webhook.
    """
    def get(self, request):
        school = getattr(request, "school", None)
        reference = request.GET.get("reference", "").strip()
        invoice_id = request.GET.get("invoice_id")

        if not reference or not invoice_id:
            messages.error(request, "Missing payment reference or invoice ID.")
            return redirect("accounts:dashboard")

        invoice = get_object_or_404(StudentInvoice, id=invoice_id, school=school)

        result = verify_paystack_transaction(school, reference)
        if result.get("status") and result.get("data", {}).get("status") == "success":
            data = result["data"]
            amount_kobo = data.get("amount", 0)
            amount_naira = Decimal(str(amount_kobo)) / Decimal("100")

            payment = record_payment(
                school=school,
                invoice=invoice,
                amount=amount_naira,
                method=PAYMENT_METHOD_PAYSTACK,
                reference=reference,
                recorded_by=request.user if request.user.is_authenticated else None,
                gateway_response=data,
                status=PAYMENT_STATUS_SUCCESSFUL,
            )
            messages.success(request, f"Online payment of ₦{payment.amount:,.2f} verified! Receipt #{payment.receipt_number}.")
            return redirect("finance:payment_receipt", pk=payment.id)
        else:
            messages.error(request, "Payment verification failed or was cancelled by gateway.")
            return redirect("finance:invoice_detail", pk=invoice.id)


class PaymentReceiptView(SchoolRequiredMixin, View):
    """
    Official printable school fee payment receipt with school letterhead.
    """
    def get(self, request, pk):
        school = self.get_school()
        payment = get_object_or_404(
            Payment.objects.select_related("invoice", "student__user", "recorded_by"),
            id=pk,
            school=school,
        )

        template = resolve_school_template(school, "finance/receipt.html")
        return render(request, template, {
            "school": school,
            "payment": payment,
            "invoice": payment.invoice,
            "student": payment.student,
            "current_date": timezone.now().date(),
        })
