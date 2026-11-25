from django.contrib import admin
from academics.models import Section, SchoolClass, ClassArm, AcademicSession, Term


# ==============================================================================
# Inline registrations
# ==============================================================================

class SchoolClassInline(admin.TabularInline):
    model = SchoolClass
    extra = 1
    fields = ("name", "order", "is_active")


class ClassArmInline(admin.TabularInline):
    model = ClassArm
    extra = 1
    fields = ("name", "is_active")


class TermInline(admin.TabularInline):
    model = Term
    extra = 3
    fields = ("term", "start_date", "end_date", "is_current")


# ==============================================================================
# Admin registrations
# ==============================================================================

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "section_type", "order", "is_active")
    list_filter = ("section_type", "is_active", "school")
    search_fields = ("name", "school__name")
    inlines = [SchoolClassInline]


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "section", "order", "is_active")
    list_filter = ("is_active", "section", "school")
    search_fields = ("name", "school__name")
    inlines = [ClassArmInline]


@admin.register(ClassArm)
class ClassArmAdmin(admin.ModelAdmin):
    list_display = ("name", "school_class", "school", "is_active")
    list_filter = ("is_active", "school")
    search_fields = ("name", "school_class__name", "school__name")


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "start_date", "end_date", "is_current")
    list_filter = ("is_current", "school")
    search_fields = ("name", "school__name")
    inlines = [TermInline]


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("display_name", "session", "school", "start_date", "end_date", "is_current")
    list_filter = ("term", "is_current", "school")
    search_fields = ("session__name", "school__name")

    def display_name(self, obj):
        return obj.display_name
    display_name.short_description = "Term"
