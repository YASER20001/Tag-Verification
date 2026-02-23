from django.contrib import admin
from .models import VerificationSession, VerificationResult


class VerificationResultInline(admin.TabularInline):
    model = VerificationResult
    extra = 0
    fields = ["tag_number", "verification_status", "ctdb_description", "page_number", "is_shorthand"]
    readonly_fields = ["tag_number", "verification_status", "ctdb_description", "page_number", "is_shorthand"]
    can_delete = False
    max_num = 200
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(VerificationSession)
class VerificationSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id", "document_revision", "overall_result", "total_tags_found",
        "tags_valid_active", "tags_valid_void", "tags_not_found",
        "extraction_method", "duration_seconds", "started_at",
    ]
    list_filter = ["overall_result", "status", "extraction_method"]
    search_fields = ["document_revision__document__document_number"]
    readonly_fields = [
        "started_at", "completed_at", "duration_seconds",
        "total_tags_found", "tags_valid_active", "tags_valid_void",
        "tags_not_found", "tags_shorthand", "overall_result",
    ]
    inlines = [VerificationResultInline]

    def has_add_permission(self, request):
        return False
