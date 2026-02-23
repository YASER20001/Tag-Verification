from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Plant, Area, Unit, System,
    Discipline, TagClass, CriticalityLevel,
    Tag, TagStatusHistory, TagAttribute, TagGroup, TagGroupMembership,
    ChangeRequest, ChangeRequestItem, ChangeApproval,
    ImportBatch, ImportBatchItem,
)


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------

@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "location", "country", "operator", "is_active"]
    list_filter = ["is_active", "country"]
    search_fields = ["code", "name", "operator"]


class AreaInline(admin.TabularInline):
    model = Area
    extra = 0
    fields = ["code", "name"]


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["__str__", "plant", "code", "name"]
    list_filter = ["plant"]
    search_fields = ["code", "name"]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ["__str__", "area", "number", "name", "process_type"]
    list_filter = ["area__plant"]
    search_fields = ["name", "process_type"]


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "abbreviation", "colour_swatch", "is_active"]
    list_editable = ["is_active"]

    def colour_swatch(self, obj):
        if obj.colour:
            return format_html(
                '<span style="background:{};padding:2px 12px;border-radius:3px;">&nbsp;</span>',
                obj.colour,
            )
        return "-"
    colour_swatch.short_description = "Colour"


@admin.register(TagClass)
class TagClassAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "discipline", "requires_safety_review", "is_active"]
    list_filter = ["discipline", "is_active", "requires_safety_review"]


@admin.register(CriticalityLevel)
class CriticalityLevelAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "level", "requires_sil_study", "requires_rcm"]
    list_filter = ["level"]


# ---------------------------------------------------------------------------
# Tag (the big one)
# ---------------------------------------------------------------------------

class TagAttributeInline(admin.TabularInline):
    model = TagAttribute
    extra = 0
    fields = ["attribute_name", "attribute_value", "attribute_type", "unit_of_measure"]


class TagStatusHistoryInline(admin.TabularInline):
    model = TagStatusHistory
    extra = 0
    readonly_fields = ["old_status", "new_status", "changed_at", "changed_by", "reason"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = [
        "tag_number", "tag_description", "discipline", "status",
        "plant", "is_safety_critical", "updated_at",
    ]
    list_filter = [
        "status", "discipline", "plant", "is_safety_critical",
        "is_pressure_vessel", "is_atex_rated",
    ]
    search_fields = ["tag_number", "tag_description", "serial_number", "manufacturer"]
    readonly_fields = ["created_at", "updated_at", "voided_at", "status_changed_at"]
    inlines = [TagAttributeInline, TagStatusHistoryInline]
    fieldsets = [
        ("Identity", {
            "fields": ["tag_number", "tag_description", "alias", "service_description", "notes"],
        }),
        ("Hierarchy", {
            "fields": ["plant", "area", "unit", "system"],
            "classes": ["collapse"],
        }),
        ("Classification", {
            "fields": ["discipline", "tag_class", "criticality_level"],
        }),
        ("Status & Lifecycle", {
            "fields": [
                "status", "status_reason", "status_changed_at", "status_changed_by",
                "designed_at", "installed_at", "commissioned_at",
                "last_inspected_at", "next_inspection_due",
                "decommissioned_at", "voided_at",
            ],
        }),
        ("Engineering References", {
            "fields": [
                "line_number", "drawing_number", "p_and_id_number",
                "spec_number", "purchase_order_number", "work_order_number",
            ],
            "classes": ["collapse"],
        }),
        ("Physical Attributes", {
            "fields": [
                "manufacturer", "model_number", "serial_number",
                "material", "size_rating", "weight_kg",
                "design_pressure_barg", "design_temperature_c",
            ],
            "classes": ["collapse"],
        }),
        ("Safety Flags", {
            "fields": [
                "is_safety_critical", "is_pressure_vessel",
                "is_lifting_equipment", "is_atex_rated", "sil_level",
            ],
        }),
        ("Maintenance", {
            "fields": ["maintenance_strategy", "maintenance_interval_days", "spare_parts_available"],
            "classes": ["collapse"],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at", "created_by", "updated_by"],
            "classes": ["collapse"],
        }),
    ]
    actions = ["mark_void", "mark_active"]

    def mark_void(self, request, queryset):
        for tag in queryset:
            if tag.status != "Void":
                tag.toggle_status(user=request.user, reason="Bulk void via admin")
        self.message_user(request, f"Marked {queryset.count()} tags as Void.")
    mark_void.short_description = "Mark selected tags as Void"

    def mark_active(self, request, queryset):
        for tag in queryset:
            if tag.status != "Active":
                tag.toggle_status(user=request.user, reason="Bulk reactivate via admin")
        self.message_user(request, f"Marked {queryset.count()} tags as Active.")
    mark_active.short_description = "Mark selected tags as Active"


@admin.register(TagStatusHistory)
class TagStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["tag", "old_status", "new_status", "changed_at", "changed_by", "reason"]
    list_filter = ["old_status", "new_status"]
    search_fields = ["tag__tag_number", "reason"]
    readonly_fields = ["tag", "old_status", "new_status", "changed_at", "changed_by"]

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Tag Groups
# ---------------------------------------------------------------------------

class TagGroupMembershipInline(admin.TabularInline):
    model = TagGroupMembership
    extra = 0
    raw_id_fields = ["tag"]
    fields = ["tag", "role", "sequence", "notes"]


@admin.register(TagGroup)
class TagGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "group_type", "plant", "is_active"]
    list_filter = ["group_type", "is_active", "plant"]
    search_fields = ["name", "code"]
    inlines = [TagGroupMembershipInline]


# ---------------------------------------------------------------------------
# Change Requests
# ---------------------------------------------------------------------------

class ChangeRequestItemInline(admin.TabularInline):
    model = ChangeRequestItem
    extra = 0
    fields = ["field_name", "old_value", "new_value", "notes"]


class ChangeApprovalInline(admin.TabularInline):
    model = ChangeApproval
    extra = 0
    readonly_fields = ["approver", "decision", "decided_at", "comments"]
    can_delete = False


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = [
        "reference_number", "request_type", "tag", "title", "priority", "status", "created_at",
    ]
    list_filter = ["status", "request_type", "priority"]
    search_fields = ["reference_number", "title", "tag__tag_number"]
    readonly_fields = ["reference_number", "created_at", "updated_at"]
    inlines = [ChangeRequestItemInline, ChangeApprovalInline]


# ---------------------------------------------------------------------------
# Import Batches
# ---------------------------------------------------------------------------

class ImportBatchItemInline(admin.TabularInline):
    model = ImportBatchItem
    extra = 0
    readonly_fields = ["row_number", "tag_number", "action", "status", "error_message"]
    can_delete = False
    max_num = 100
    show_change_link = False


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = [
        "id", "batch_type", "filename", "status",
        "total_rows", "created_count", "skipped_count", "failed_count",
        "created_at",
    ]
    list_filter = ["status", "batch_type"]
    readonly_fields = [
        "created_at", "updated_at", "started_at", "completed_at",
        "total_rows", "created_count", "updated_count", "skipped_count", "failed_count",
    ]
    inlines = [ImportBatchItemInline]

    def has_add_permission(self, request):
        return False
