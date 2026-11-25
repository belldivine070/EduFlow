"""
Staff admin configuration.
"""
from django.contrib import admin
from staff.models import StaffProfile


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "designation", "school", "qualification", "specialization", "created_at"]
    list_filter = ["school", "designation", "gender"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "user__email", "designation"]
    raw_id_fields = ["user", "school"]
