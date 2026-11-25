from django.test import TestCase, Client
from django.urls import reverse
from schools.models import School, SchoolDomain
from accounts.services import create_school_user
from core.constants import (
    ROLE_DIRECTOR,
    ROLE_TEACHING_STAFF,
    ROLE_PARENT,
    ROLE_STUDENT,
)
from communications.models import (
    Announcement,
    Notification,
    AUDIENCE_ALL,
    AUDIENCE_TEACHING_STAFF,
    AUDIENCE_PARENTS,
)
from communications.services import publish_announcement


class CommunicationsTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Heritage Academy",
            slug="heritage",
            code="HA",
            student_id_prefix="HA-STD-",
            is_active=True,
        )
        SchoolDomain.objects.create(
            school=self.school,
            domain="heritage.localhost",
            is_primary=True,
            is_verified=True,
        )
        self.director, _ = create_school_user(
            school=self.school,
            role=ROLE_DIRECTOR,
            first_name="Chinedu",
            last_name="Okafor",
            email="director@heritage.edu.ng",
            password="Password123!",
        )
        self.teacher, _ = create_school_user(
            school=self.school,
            role=ROLE_TEACHING_STAFF,
            first_name="Amina",
            last_name="Bello",
            email="teacher@heritage.edu.ng",
            password="Password123!",
        )
        self.parent, _ = create_school_user(
            school=self.school,
            role=ROLE_PARENT,
            first_name="Tunde",
            last_name="Adeyemi",
            email="parent@heritage.edu.ng",
            password="Password123!",
        )
        self.student, _ = create_school_user(
            school=self.school,
            role=ROLE_STUDENT,
            first_name="Kemi",
            last_name="Adeyemi",
            email="student@heritage.edu.ng",
            password="Password123!",
        )
        self.client = Client(HTTP_HOST="heritage.localhost")

    def test_publish_announcement_fans_out_targeted_notifications(self):
        announcement = publish_announcement(
            school=self.school,
            title="PTA Meeting Notice",
            content="All parents are invited for the termly PTA meeting on Friday.",
            target_audience=AUDIENCE_PARENTS,
            created_by=self.director,
        )
        self.assertEqual(Announcement.objects.filter(school=self.school).count(), 1)
        # Only the parent should receive an in-app notification
        self.assertEqual(Notification.objects.filter(school=self.school, announcement=announcement).count(), 1)
        self.assertTrue(Notification.objects.filter(recipient=self.parent, announcement=announcement).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.student, announcement=announcement).exists())

    def test_announcement_create_view_restricted_to_admin_and_creates_notice(self):
        # Parent cannot create announcement
        self.client.force_login(self.parent)
        res_denied = self.client.get(reverse("communications:announcement_create"))
        self.assertEqual(res_denied.status_code, 302)

        # Director can create announcement for ALL
        self.client.force_login(self.director)
        res = self.client.post(
            reverse("communications:announcement_create"),
            {
                "title": "Mid-Term Break",
                "content": "School closes on Wednesday for mid-term break.",
                "target_audience": AUDIENCE_ALL,
                "message_type": "announcement",
                "channel": "in_app",
            },
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Announcement.objects.filter(school=self.school, title="Mid-Term Break").count(), 1)
        # All 4 users receive notification
        self.assertEqual(Notification.objects.filter(school=self.school).count(), 4)

    def test_announcement_list_audience_isolation(self):
        publish_announcement(
            school=self.school,
            title="Staff Briefing",
            content="Mandatory briefing in staff room.",
            target_audience=AUDIENCE_TEACHING_STAFF,
            created_by=self.director,
        )
        publish_announcement(
            school=self.school,
            title="General Holiday",
            content="Public holiday tomorrow.",
            target_audience=AUDIENCE_ALL,
            created_by=self.director,
        )

        # Student sees only 'General Holiday'
        self.client.force_login(self.student)
        res = self.client.get(reverse("communications:announcement_list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "General Holiday")
        self.assertNotContains(res, "Staff Briefing")

        # Teacher sees both
        self.client.force_login(self.teacher)
        res_teacher = self.client.get(reverse("communications:announcement_list"))
        self.assertContains(res_teacher, "General Holiday")
        self.assertContains(res_teacher, "Staff Briefing")

    def test_notifications_mark_read_and_mark_all_read(self):
        publish_announcement(
            school=self.school,
            title="Fee Reminder",
            content="Please settle term fees.",
            target_audience=AUDIENCE_PARENTS,
            created_by=self.director,
        )
        publish_announcement(
            school=self.school,
            title="Sports Day",
            content="Inter-house sports next week.",
            target_audience=AUDIENCE_ALL,
            created_by=self.director,
        )

        self.client.force_login(self.parent)
        notes = Notification.objects.filter(recipient=self.parent, is_read=False)
        self.assertEqual(notes.count(), 2)

        # Mark one as read
        first_note = notes.first()
        res = self.client.post(reverse("communications:notification_mark_read", args=[first_note.id]))
        self.assertEqual(res.status_code, 302)
        first_note.refresh_from_db()
        self.assertTrue(first_note.is_read)

        # Mark all remaining as read
        res_all = self.client.post(reverse("communications:notification_mark_all_read"))
        self.assertEqual(res_all.status_code, 302)
        self.assertEqual(Notification.objects.filter(recipient=self.parent, is_read=False).count(), 0)
