from django.contrib import admin
from .models import DocumentType, Document, DocumentRevision, DocumentFile, TagDocumentLink


class DocumentRevisionInline(admin.TabularInline):
    model = DocumentRevision
    extra = 0
    fields = ["revision_number", "status", "verification_status", "tags_found", "created_at"]
    readonly_fields = ["created_at"]
    show_change_link = True


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "requires_tag_verification", "is_active"]
    list_editable = ["is_active"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        "document_number", "title", "document_type", "is_active",
        "current_revision_display", "created_at",
    ]
    list_filter = ["is_active", "document_type", "discipline"]
    search_fields = ["document_number", "title", "project_number"]
    inlines = [DocumentRevisionInline]

    def current_revision_display(self, obj):
        if obj.current_revision:
            return f"Rev {obj.current_revision.revision_number} — {obj.current_revision.verification_status}"
        return "—"
    current_revision_display.short_description = "Current Revision"


@admin.register(DocumentRevision)
class DocumentRevisionAdmin(admin.ModelAdmin):
    list_display = [
        "document", "revision_number", "status", "verification_status",
        "tags_found", "approved_by", "created_at",
    ]
    list_filter = ["status", "verification_status"]
    search_fields = ["document__document_number", "document__title"]
    readonly_fields = ["created_at", "updated_at", "approved_at"]


@admin.register(TagDocumentLink)
class TagDocumentLinkAdmin(admin.ModelAdmin):
    list_display = [
        "tag", "document_revision", "verification_status", "page_number", "is_shorthand", "created_at",
    ]
    list_filter = ["verification_status", "is_shorthand"]
    search_fields = ["tag__tag_number", "document_revision__document__document_number"]
    raw_id_fields = ["tag", "document_revision"]
