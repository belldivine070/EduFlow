"""
Tests for Finance and Payments module.

Covers fee categories, fee structures, individual and class-wide bulk student invoice generation,
payment recording, Paystack server-side transaction verification, idempotent receipt numbering,
and official payment receipt dossier generation.
"""
import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.core.exceptions import ValidationError

from schools.models import School, SchoolDomain
from academics.models import AcademicSession, Term, SchoolClass, StudentProfile, StudentEnrollment
from academics.services import seed_school_classes, admit_student
from accounts.models import User, SchoolMembership
from core.constants import ROLE_DIRECTOR
from finance.models import (
    FeeCategory,
    FeeStructure,
    StudentInvoice,
    Payment,
    INVOICE_STATUS_PENDING,
    INVOICE_STATUS_PARTIALLY_PAID,
    INVOICE_STATUS_PAID,
    PAYMENT_METHOD_CASH,
    PAYMENT_METHOD_PAYSTACK,
    PAYMENT_STATUS_SUCCESSFUL,
)
from finance.services import (
    generate_invoice_number,
    generate_receipt_number,
    create_student_invoice,
    generate_class_invoices,
    record_payment,
    verify_paystack_transaction,
)


class FinanceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Grace High School",
            code="GHS",
            slug="grace-high-school",
            student_id_prefix="GHS-STD-",
            is_active=True,
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="grace.localhost",
            is_primary=True,
            is_verified=True,
        )

        seed_school_classes(self.school)
        self.jss1 = SchoolClass.objects.get(school=self.school, name="JSS 1")

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2027, 7, 31),
            is_current=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            session=self.session,
            term="first",
            start_date=datetime.date(2026, 9, 10),
            end_date=datetime.date(2026, 12, 18),
            is_current=True,
        )

        # Create Director Staff User
        self.staff_user = User.objects.create_user(
            username="GHS-DIR-0001",
            first_name="Victoria",
            last_name="Olatunji",
            email="bursar@grace.ng",
            password="BursarPassword123!",
        )
        SchoolMembership.objects.create(
            user=self.staff_user,
            school=self.school,
            role=ROLE_DIRECTOR,
            id_number="GHS-DIR-0001",
            status="active",
        )

        # Admit two students into JSS 1
        self.student_profile1, self.enroll1 = admit_student(
            school=self.school,
            first_name="Femi",
            last_name="Adeyemi",
            gender="male",
            school_class=self.jss1,
            session=self.session,
            date_of_birth=datetime.date(2013, 2, 10),
        )

        self.student_profile2, self.enroll2 = admit_student(
            school=self.school,
            first_name="Bisi",
            last_name="Akande",
            gender="female",
            school_class=self.jss1,
            session=self.session,
            date_of_birth=datetime.date(2013, 6, 14),
        )

        # Setup Fee Categories & Structures
        self.tuition_cat = FeeCategory.objects.create(school=self.school, name="Tuition Fee")
        self.pta_cat = FeeCategory.objects.create(school=self.school, name="PTA Levy")

        self.tuition_struct = FeeStructure.objects.create(
            school=self.school,
            category=self.tuition_cat,
            session=self.session,
            term=self.term,
            school_class=self.jss1,
            amount=Decimal("45000.00"),
        )
        self.pta_struct = FeeStructure.objects.create(
            school=self.school,
            category=self.pta_cat,
            session=self.session,
            term=self.term,
            school_class=None,  # General for all classes
            amount=Decimal("5000.00"),
        )

    def test_invoice_and_receipt_number_generation(self):
        """Generates tenant-scoped sequential references."""
        inv_num = generate_invoice_number(self.school, self.session)
        self.assertEqual(inv_num, "GHS-INV-2026-0001")

        rec_num = generate_receipt_number(self.school)
        current_year = timezone.now().year
        self.assertEqual(rec_num, f"GHS-REC-{current_year}-0001")

    def test_create_student_invoice_service(self):
        """Individual invoice creation with line items."""
        items = [
            {"description": "First Term Tuition", "amount": Decimal("45000.00"), "fee_structure": self.tuition_struct},
            {"description": "PTA Levy", "amount": Decimal("5000.00"), "fee_structure": self.pta_struct},
        ]
        invoice = create_student_invoice(
            school=self.school,
            student=self.student_profile1,
            session=self.session,
            term=self.term,
            title="First Term Fees - Femi",
            items_data=items,
            created_by=self.staff_user,
        )

        self.assertEqual(invoice.total_amount, Decimal("50000.00"))
        self.assertEqual(invoice.amount_paid, Decimal("0.00"))
        self.assertEqual(invoice.balance_due, Decimal("50000.00"))
        self.assertEqual(invoice.status, INVOICE_STATUS_PENDING)
        self.assertEqual(invoice.items.count(), 2)

    def test_bulk_generate_class_invoices_service(self):
        """Bulk generates invoices for all actively enrolled students in a class."""
        created = generate_class_invoices(
            school=self.school,
            school_class=self.jss1,
            session=self.session,
            term=self.term,
            created_by=self.staff_user,
        )

        # 2 students enrolled in JSS 1
        self.assertEqual(len(created), 2)
        for inv in created:
            self.assertEqual(inv.total_amount, Decimal("50000.00"))  # 45k + 5k
            self.assertEqual(inv.items.count(), 2)

        # Running again must be idempotent and not create duplicate invoices
        repeat_created = generate_class_invoices(
            school=self.school,
            school_class=self.jss1,
            session=self.session,
            term=self.term,
            created_by=self.staff_user,
        )
        self.assertEqual(len(repeat_created), 0)

    def test_record_payment_and_receipt_service(self):
        """Recording partial and full payments updates invoice balances and generates receipt."""
        invoice = create_student_invoice(
            school=self.school,
            student=self.student_profile1,
            session=self.session,
            term=self.term,
            title="First Term Fees",
            items_data=[{"description": "Tuition", "amount": Decimal("50000.00")}],
            created_by=self.staff_user,
        )

        # Partial Payment ₦20,000
        pay1 = record_payment(
            school=self.school,
            invoice=invoice,
            amount=Decimal("20000.00"),
            method=PAYMENT_METHOD_CASH,
            reference="CASH-001",
            recorded_by=self.staff_user,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("20000.00"))
        self.assertEqual(invoice.balance_due, Decimal("30000.00"))
        self.assertEqual(invoice.status, INVOICE_STATUS_PARTIALLY_PAID)
        self.assertTrue(pay1.receipt_number.startswith("GHS-REC-"))

        # Final Payment ₦30,000
        pay2 = record_payment(
            school=self.school,
            invoice=invoice,
            amount=Decimal("30000.00"),
            method=PAYMENT_METHOD_CASH,
            reference="CASH-002",
            recorded_by=self.staff_user,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("50000.00"))
        self.assertEqual(invoice.balance_due, Decimal("0.00"))
        self.assertEqual(invoice.status, INVOICE_STATUS_PAID)

    def test_paystack_verification_and_receipt_flow(self):
        """Simulated server-side Paystack verification updates invoice and enables receipt view."""
        invoice = create_student_invoice(
            school=self.school,
            student=self.student_profile2,
            session=self.session,
            term=self.term,
            title="School Fees - Bisi",
            items_data=[{"description": "Tuition", "amount": Decimal("50000.00")}],
        )

        # Call Paystack verification endpoint with mock reference
        response = self.client.get(
            f"/finance/paystack/verify/?reference=pstk_test_123456&invoice_id={invoice.id}",
            HTTP_HOST="grace.localhost",
        )
        self.assertEqual(response.status_code, 302)

        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("50000.00"))
        self.assertEqual(invoice.status, INVOICE_STATUS_PAID)

        # Verify Payment and Receipt
        payment = Payment.objects.get(invoice=invoice, reference="pstk_test_123456")
        self.assertEqual(payment.status, PAYMENT_STATUS_SUCCESSFUL)

        # View Printable Receipt
        self.client.force_login(self.staff_user)
        receipt_res = self.client.get(f"/finance/receipt/{payment.id}/", HTTP_HOST="grace.localhost")
        self.assertEqual(receipt_res.status_code, 200)
        self.assertContains(receipt_res, "Official School Fee Receipt")
        self.assertContains(receipt_res, "Bisi Akande")
        self.assertContains(receipt_res, payment.receipt_number)

    def test_invoice_management_views(self):
        """Staff can list invoices, view details, and record manual payments."""
        invoice = create_student_invoice(
            school=self.school,
            student=self.student_profile1,
            session=self.session,
            term=self.term,
            title="Tuition",
            items_data=[{"description": "Tuition", "amount": Decimal("30000.00")}],
        )

        self.client.force_login(self.staff_user)

        # 1. Invoice List View
        list_res = self.client.get("/finance/invoices/", HTTP_HOST="grace.localhost")
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, invoice.invoice_number)
        self.assertContains(list_res, "Total Billed")

        # 2. Invoice Detail View
        detail_res = self.client.get(f"/finance/invoices/{invoice.id}/", HTTP_HOST="grace.localhost")
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "Fee Breakdown")

        # 3. Record Offline Payment POST
        pay_res = self.client.post(
            f"/finance/invoices/{invoice.id}/pay/",
            {"amount": "30000.00", "method": "pos", "reference": "POS-TX-9988"},
            HTTP_HOST="grace.localhost",
        )
        self.assertEqual(pay_res.status_code, 302)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, INVOICE_STATUS_PAID)
