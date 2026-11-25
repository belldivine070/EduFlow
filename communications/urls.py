from django.urls import path
from communications.views import (
    AnnouncementListView,
    AnnouncementCreateView,
    NotificationListView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
)

app_name = "communications"

urlpatterns = [
    path("announcements/", AnnouncementListView.as_view(), name="announcement_list"),
    path("announcements/create/", AnnouncementCreateView.as_view(), name="announcement_create"),
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path("notifications/mark-read/<uuid:pk>/", NotificationMarkReadView.as_view(), name="notification_mark_read"),
    path("notifications/mark-all-read/", NotificationMarkAllReadView.as_view(), name="notification_mark_all_read"),
]
