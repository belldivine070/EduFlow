from django.test import TestCase, Client
from django.urls import reverse
from schools.models import School, SchoolDomain
from accounts.services import create_school_user
from core.constants import (
    ROLE_DIRECTOR,
    ROLE_PARENT,
    ROLE_STUDENT,
)
from support.models import (
    SupportTicket,
    TicketMessage,
    TICKET_STATUS_OPEN,
    TICKET_STATUS_RESOLVED,
)
from support.services import create_support_ticket, add_ticket_reply


class SupportTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Acumen College",
            slug="acumen",
            code="ACU",
            student_id_prefix="ACU-STD-",
            is_active=True,
        )
        SchoolDomain.objects.create(
            school=self.school,
            domain="acumen.localhost",
            is_primary=True,
            is_verified=True,
        )
        self.director, _ = create_school_user(
            school=self.school,
            role=ROLE_DIRECTOR,
            first_name="Seyi",
            last_name="Balogun",
            email="director@acumen.edu.ng",
            password="Password123!",
        )
        self.parent1, _ = create_school_user(
            school=self.school,
            role=ROLE_PARENT,
            first_name="Ngozi",
            last_name="Eze",
            email="parent1@acumen.edu.ng",
            password="Password123!",
        )
        self.parent2, _ = create_school_user(
            school=self.school,
            role=ROLE_PARENT,
            first_name="Bola",
            last_name="Tinubu",
            email="parent2@acumen.edu.ng",
            password="Password123!",
        )
        self.client = Client(HTTP_HOST="acumen.localhost")

    def test_create_ticket_and_sequential_numbering(self):
        t1 = create_support_ticket(
            school=self.school,
            user=self.parent1,
            subject="Invoice Discrepancy",
            description="Tuition was billed twice.",
            category="billing",
            priority="high",
        )
        t2 = create_support_ticket(
            school=self.school,
            user=self.parent2,
            subject="Login Issue",
            description="Cannot reset password.",
            category="technical",
            priority="medium",
        )
        self.assertTrue(t1.ticket_number.startswith("ACU-TIC-"))
        self.assertTrue(t1.ticket_number.endswith("-0001"))
        self.assertTrue(t2.ticket_number.endswith("-0002"))

    def test_ticket_isolation_between_parents(self):
        t1 = create_support_ticket(
            school=self.school,
            user=self.parent1,
            subject="Private Parent 1 Issue",
            description="Details",
            category="general",
        )
        self.client.force_login(self.parent2)
        res_list = self.client.get(reverse("support:ticket_list"))
        self.assertNotContains(res_list, "Private Parent 1 Issue")

        res_detail = self.client.get(reverse("support:ticket_detail", args=[t1.id]))
        self.assertEqual(res_detail.status_code, 404)

    def test_staff_internal_note_hidden_from_requester_and_reopen_on_reply(self):
        ticket = create_support_ticket(
            school=self.school,
            user=self.parent1,
            subject="Bus Route Change",
            description="Requesting pickup change.",
            category="general",
        )
        self.client.force_login(self.director)
        # Staff posts internal note and marks resolved
        self.client.post(
            reverse("support:ticket_detail", args=[ticket.id]),
            {
                "action": "reply",
                "message": "Internal check: verify address with bursar.",
                "is_internal_note": "true",
            },
        )
        self.client.post(
            reverse("support:ticket_detail", args=[ticket.id]),
            {
                "action": "update_status",
                "status": TICKET_STATUS_RESOLVED,
            },
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, TICKET_STATUS_RESOLVED)

        # Parent views ticket: internal note must be hidden
        self.client.force_login(self.parent1)
        res = self.client.get(reverse("support:ticket_detail", args=[ticket.id]))
        self.assertEqual(res.status_code, 200)
        self.assertNotContains(res, "Internal check: verify address with bursar.")

        # Parent replies -> ticket reopens automatically
        self.client.post(
            reverse("support:ticket_detail", args=[ticket.id]),
            {
                "action": "reply",
                "message": "Actually, we moved to Lekki Phase 1.",
            },
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, TICKET_STATUS_OPEN)
