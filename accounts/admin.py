from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User, SchoolMembership


class SchoolMembershipInline(admin.TabularInline):
    model = SchoolMembership
    extra = 0
    fields = ("school", "role", "status", "id_number", "date_joined")
    readonly_fields = ("date_joined",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_platform_developer", "is_staff", "is_active")
    list_filter = ("is_platform_developer", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    ordering = ("-date_joined",)
    inlines = [SchoolMembershipInline]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("first_name", "middle_name", "last_name", "email", "phone_number", "avatar")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "is_platform_developer", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "last_active_at")}),
    )
    readonly_fields = ("date_joined", "last_active_at")


@admin.register(SchoolMembership)
class SchoolMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "role", "status", "id_number", "date_joined")
    list_filter = ("role", "status", "school")
    search_fields = ("user__username", "user__email", "id_number", "school__name")
