from django.urls import path
from support.views import (
    SupportTicketListView,
    SupportTicketCreateView,
    SupportTicketDetailView,
)

app_name = "support"

urlpatterns = [
    path("", SupportTicketListView.as_view(), name="ticket_list"),
    path("create/", SupportTicketCreateView.as_view(), name="ticket_create"),
    path("<uuid:pk>/", SupportTicketDetailView.as_view(), name="ticket_detail"),
]
