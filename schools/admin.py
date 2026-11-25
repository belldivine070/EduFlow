from django.contrib import admin
from schools.models import School, SchoolDomain, AppVariable


class SchoolDomainInline(admin.TabularInline):
    model = SchoolDomain
    extra = 1


class AppVariableInline(admin.TabularInline):
    model = AppVariable
    extra = 1


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "slug")
    inlines = [SchoolDomainInline, AppVariableInline]


@admin.register(SchoolDomain)
class SchoolDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "school", "domain_type", "is_primary", "is_verified", "is_active")
    list_filter = ("domain_type", "is_primary", "is_verified", "is_active")
    search_fields = ("domain", "school__name", "school__code")


@admin.register(AppVariable)
class AppVariableAdmin(admin.ModelAdmin):
    list_display = ("var_name", "school", "var_value", "isreadonly", "lastupdated")
    list_filter = ("isreadonly", "school")
    search_fields = ("var_name", "var_value", "description")
