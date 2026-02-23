"""
Asset Registry (CTDB) — Advanced Database Models
=================================================
Full plant-asset hierarchy with complete tag lifecycle management,
change tracking, custom attributes, grouping, and import auditing.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator


# ---------------------------------------------------------------------------
# Shared abstract bases
# ---------------------------------------------------------------------------

class TimeStampedModel(models.Model):
    """Abstract base: created_at / updated_at on every record."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditedModel(TimeStampedModel):
    """Abstract base: timestamps + who created/last-modified."""
    created_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract base: soft-delete instead of physical DELETE."""
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Plant / Facility Hierarchy
# ---------------------------------------------------------------------------

class Plant(AuditedModel, SoftDeleteModel):
    """Top-level plant or facility (e.g. Onshore Gas Plant — Site A)."""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=100, blank=True)
    operator = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Plant / Facility"
        verbose_name_plural = "Plants / Facilities"

    def __str__(self):
        return f"{self.code} — {self.name}"


class Area(AuditedModel, SoftDeleteModel):
    """Geographical or process area within a plant (e.g. Area 10 — Feed Preparation)."""
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="areas")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["plant", "code"]
        unique_together = [("plant", "code")]
        verbose_name = "Area"

    def __str__(self):
        return f"{self.plant.code}-{self.code} — {self.name}"


class Unit(AuditedModel, SoftDeleteModel):
    """Process unit within an area (e.g. Unit 10, Unit 20)."""
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="units")
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    process_type = models.CharField(max_length=100, blank=True)  # e.g. Compression, Separation

    class Meta:
        ordering = ["area", "number"]
        unique_together = [("area", "number")]
        verbose_name = "Process Unit"

    def __str__(self):
        return f"Unit {self.number} — {self.name}"


class System(AuditedModel):
    """Subsystem within a unit (e.g. Lube Oil System, Seal Gas System)."""
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="systems")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    system_number = models.CharField(max_length=20, blank=True)  # e.g. 10-SYS-001

    class Meta:
        ordering = ["unit", "code"]
        unique_together = [("unit", "code")]
        verbose_name = "System"

    def __str__(self):
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Classification Lookups
# ---------------------------------------------------------------------------

class Discipline(TimeStampedModel):
    """Engineering discipline (Mechanical, Instrumentation, Electrical, Piping, Civil)."""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=5, blank=True)
    colour = models.CharField(max_length=7, blank=True, help_text="Hex colour, e.g. #FF5733")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Discipline"

    def __str__(self):
        return self.name


class TagClass(TimeStampedModel):
    """Equipment/instrument class (Pump, Valve, Transmitter, Heat Exchanger …)."""
    discipline = models.ForeignKey(
        Discipline, on_delete=models.SET_NULL, null=True, blank=True, related_name="tag_classes"
    )
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=5, blank=True)
    description = models.TextField(blank=True)
    typical_tag_pattern = models.CharField(
        max_length=50, blank=True, help_text="Regex pattern for tag numbers of this class"
    )
    requires_safety_review = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["discipline", "name"]
        verbose_name = "Tag Class"
        verbose_name_plural = "Tag Classes"

    def __str__(self):
        return f"{self.code} — {self.name}"


class CriticalityLevel(TimeStampedModel):
    """
    Criticality / safety integrity level.
    e.g. Safety-Critical (SIL), Production-Critical, Asset-Critical, Non-Critical
    """
    CRITICALITY_CHOICES = [
        ("safety_sil3", "Safety Critical — SIL 3"),
        ("safety_sil2", "Safety Critical — SIL 2"),
        ("safety_sil1", "Safety Critical — SIL 1"),
        ("production",  "Production Critical"),
        ("asset",       "Asset Critical"),
        ("non_critical","Non-Critical"),
    ]
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=CRITICALITY_CHOICES, default="non_critical")
    colour = models.CharField(max_length=7, blank=True)
    requires_rcm = models.BooleanField(default=False, help_text="Reliability-Centred Maintenance")
    requires_sil_study = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["level", "name"]
        verbose_name = "Criticality Level"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Core Tag Model
# ---------------------------------------------------------------------------

class TagStatus(models.TextChoices):
    ACTIVE      = "Active",      "Active"
    VOID        = "Void",        "Void"
    PROVISIONAL = "Provisional", "Provisional"
    OBSOLETE    = "Obsolete",    "Obsolete"
    RESERVED    = "Reserved",    "Reserved"


tag_number_validator = RegexValidator(
    regex=r'^[A-Z0-9][A-Z0-9\-]{1,30}$',
    message="Tag number must be uppercase alphanumeric with hyphens, 2-31 chars.",
)


class Tag(AuditedModel, SoftDeleteModel):
    """
    Master tag / equipment record (the CTDB row).

    Full schema covering identity, hierarchy, classification, physical
    attributes, engineering references, lifecycle dates, and safety flags.
    """

    # ---- Identity ----------------------------------------------------------
    tag_number = models.CharField(
        max_length=50, unique=True, db_index=True,
        validators=[tag_number_validator],
        help_text="Unique tag number, e.g. 10-P-101A",
    )
    tag_description = models.TextField(blank=True)
    alias = models.CharField(max_length=100, blank=True, help_text="Alternative name / nickname")
    abbreviation = models.CharField(max_length=20, blank=True)
    service_description = models.TextField(blank=True, help_text="Process service description")
    notes = models.TextField(blank=True)

    # ---- Hierarchy (all optional — some tags predate hierarchy) ------------
    plant = models.ForeignKey(
        Plant, null=True, blank=True, on_delete=models.SET_NULL, related_name="tags"
    )
    area = models.ForeignKey(
        Area, null=True, blank=True, on_delete=models.SET_NULL, related_name="tags"
    )
    unit = models.ForeignKey(
        Unit, null=True, blank=True, on_delete=models.SET_NULL, related_name="tags"
    )
    system = models.ForeignKey(
        System, null=True, blank=True, on_delete=models.SET_NULL, related_name="tags"
    )

    # ---- Classification ----------------------------------------------------
    discipline = models.ForeignKey(
        Discipline, null=True, blank=True, on_delete=models.SET_NULL, related_name="tags"
    )
    tag_class = models.ForeignKey(
        TagClass, null=True, blank=True, on_delete=models.SET_NULL, related_name="tags"
    )
    criticality_level = models.ForeignKey(
        CriticalityLevel, null=True, blank=True, on_delete=models.SET_NULL, related_name="tags"
    )

    # ---- Status & Lifecycle ------------------------------------------------
    status = models.CharField(
        max_length=20, choices=TagStatus.choices, default=TagStatus.ACTIVE, db_index=True
    )
    status_reason = models.TextField(blank=True, help_text="Reason for current status")
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="status_changes"
    )

    # ---- Engineering References --------------------------------------------
    line_number = models.CharField(max_length=50, blank=True)
    drawing_number = models.CharField(max_length=100, blank=True)
    p_and_id_number = models.CharField(max_length=50, blank=True, verbose_name="P&ID Number")
    spec_number = models.CharField(max_length=50, blank=True)
    datasheet_number = models.CharField(max_length=50, blank=True)
    purchase_order_number = models.CharField(max_length=50, blank=True)
    work_order_number = models.CharField(max_length=50, blank=True)

    # ---- Physical Attributes -----------------------------------------------
    manufacturer = models.CharField(max_length=200, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True, db_index=True)
    material = models.CharField(max_length=100, blank=True)
    size_rating = models.CharField(max_length=50, blank=True, help_text="e.g. 4\" Class 300")
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    design_pressure_barg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Design Pressure (barg)"
    )
    design_temperature_c = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Design Temperature (°C)"
    )

    # ---- Safety Flags ------------------------------------------------------
    is_safety_critical = models.BooleanField(default=False, db_index=True)
    is_pressure_vessel = models.BooleanField(default=False)
    is_lifting_equipment = models.BooleanField(default=False)
    is_atex_rated = models.BooleanField(default=False, verbose_name="ATEX Rated")
    sil_level = models.CharField(max_length=10, blank=True, help_text="SIL 1 / SIL 2 / SIL 3 / SIL 4")

    # ---- Lifecycle Dates ---------------------------------------------------
    designed_at = models.DateField(null=True, blank=True)
    fabricated_at = models.DateField(null=True, blank=True)
    installed_at = models.DateField(null=True, blank=True)
    commissioned_at = models.DateField(null=True, blank=True)
    last_inspected_at = models.DateField(null=True, blank=True)
    next_inspection_due = models.DateField(null=True, blank=True)
    decommissioned_at = models.DateField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)

    # ---- Maintenance -------------------------------------------------------
    maintenance_strategy = models.CharField(
        max_length=50, blank=True,
        help_text="PM / PdM / RCM / Run-to-Failure",
    )
    maintenance_interval_days = models.PositiveIntegerField(null=True, blank=True)
    spare_parts_available = models.BooleanField(default=False)

    class Meta:
        ordering = ["tag_number"]
        verbose_name = "Tag"
        verbose_name_plural = "Tags (CTDB)"
        indexes = [
            models.Index(fields=["tag_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["discipline"]),
            models.Index(fields=["plant", "unit"]),
            models.Index(fields=["is_safety_critical"]),
            models.Index(fields=["is_deleted"]),
        ]

    def __str__(self):
        return f"{self.tag_number} ({self.status})"

    def toggle_status(self, user=None, reason=""):
        """Toggle Active ↔ Void and record the history."""
        old_status = self.status
        self.status = TagStatus.VOID if self.status == TagStatus.ACTIVE else TagStatus.ACTIVE
        self.status_changed_at = timezone.now()
        self.status_changed_by = user
        self.status_reason = reason
        if self.status == TagStatus.VOID:
            self.voided_at = timezone.now()
        else:
            self.voided_at = None
        self.save()
        TagStatusHistory.objects.create(
            tag=self,
            old_status=old_status,
            new_status=self.status,
            changed_by=user,
            reason=reason,
        )
        return self.status

    def get_discipline_name(self):
        return self.discipline.name if self.discipline else ""

    @property
    def is_active(self):
        return self.status == TagStatus.ACTIVE


# ---------------------------------------------------------------------------
# Tag Status History — immutable audit trail for status changes
# ---------------------------------------------------------------------------

class TagStatusHistory(models.Model):
    """Immutable record of every Tag status change."""
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    change_request_ref = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "Tag Status History"
        verbose_name_plural = "Tag Status Histories"

    def __str__(self):
        return f"{self.tag.tag_number}: {self.old_status} → {self.new_status} @ {self.changed_at:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# Tag Attributes — flexible custom key-value pairs per tag
# ---------------------------------------------------------------------------

class AttributeType(models.TextChoices):
    TEXT    = "text",    "Text"
    NUMBER  = "number",  "Number"
    DATE    = "date",    "Date"
    BOOLEAN = "boolean", "Boolean"
    URL     = "url",     "URL"


class TagAttribute(TimeStampedModel):
    """Custom key-value attribute attached to a tag."""
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="attributes")
    attribute_name = models.CharField(max_length=100)
    attribute_value = models.TextField()
    attribute_type = models.CharField(
        max_length=10, choices=AttributeType.choices, default=AttributeType.TEXT
    )
    unit_of_measure = models.CharField(max_length=30, blank=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["attribute_name"]
        unique_together = [("tag", "attribute_name")]
        verbose_name = "Tag Attribute"

    def __str__(self):
        return f"{self.tag.tag_number} | {self.attribute_name} = {self.attribute_value}"


# ---------------------------------------------------------------------------
# Tag Groups — named collections (process loops, shutdown keys, P&IDs, etc.)
# ---------------------------------------------------------------------------

class GroupType(models.TextChoices):
    LOOP            = "loop",             "Process Loop"
    SHUTDOWN_KEY    = "shutdown_key",     "Shutdown Key"
    CAUSE_EFFECT    = "cause_effect",     "Cause & Effect"
    P_AND_ID        = "p_and_id",         "P&ID"
    MAINTENANCE_PLAN= "maintenance_plan", "Maintenance Plan"
    INSPECTION_GROUP= "inspection_group", "Inspection Group"
    OTHER           = "other",            "Other"


class TagGroup(AuditedModel):
    """Named group of tags (loop, shutdown key, P&ID area, etc.)."""
    plant = models.ForeignKey(
        Plant, null=True, blank=True, on_delete=models.SET_NULL, related_name="tag_groups"
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, blank=True, db_index=True)
    group_type = models.CharField(
        max_length=20, choices=GroupType.choices, default=GroupType.OTHER
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    tags = models.ManyToManyField(
        Tag, through="TagGroupMembership", related_name="groups"
    )

    class Meta:
        ordering = ["group_type", "name"]
        verbose_name = "Tag Group"

    def __str__(self):
        return f"{self.code or self.name} ({self.get_group_type_display()})"


class TagGroupMembership(TimeStampedModel):
    """Through-model: Tag ↔ TagGroup with role / notes."""
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    group = models.ForeignKey(TagGroup, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, blank=True, help_text="e.g. Initiator, Final Element")
    sequence = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)
    added_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["group", "sequence"]
        unique_together = [("tag", "group")]
        verbose_name = "Tag Group Membership"

    def __str__(self):
        return f"{self.tag.tag_number} in {self.group}"


# ---------------------------------------------------------------------------
# Change Requests — structured workflow for tag changes
# ---------------------------------------------------------------------------

class ChangeRequestStatus(models.TextChoices):
    DRAFT          = "draft",          "Draft"
    SUBMITTED      = "submitted",      "Submitted"
    UNDER_REVIEW   = "under_review",   "Under Review"
    APPROVED       = "approved",       "Approved"
    REJECTED       = "rejected",       "Rejected"
    IMPLEMENTED    = "implemented",    "Implemented"
    WITHDRAWN      = "withdrawn",      "Withdrawn"


class ChangeRequestType(models.TextChoices):
    CREATE     = "create",     "Create New Tag"
    UPDATE     = "update",     "Update Tag Details"
    VOID       = "void",       "Void Tag"
    REACTIVATE = "reactivate", "Reactivate Tag"
    OBSOLETE   = "obsolete",   "Mark Obsolete"
    DELETE     = "delete",     "Delete Tag"


class ChangeRequest(AuditedModel):
    """Formal change request for tag create/update/void/delete."""
    reference_number = models.CharField(max_length=30, unique=True, blank=True)
    request_type = models.CharField(max_length=20, choices=ChangeRequestType.choices)
    tag = models.ForeignKey(
        Tag, null=True, blank=True, on_delete=models.SET_NULL, related_name="change_requests"
    )
    proposed_tag_number = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=200)
    justification = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=[("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")],
        default="normal",
    )
    status = models.CharField(
        max_length=20, choices=ChangeRequestStatus.choices, default=ChangeRequestStatus.DRAFT
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    implemented_at = models.DateTimeField(null=True, blank=True)
    implemented_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="implemented_changes"
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Change Request"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            # Auto-generate: CR-YYYYMM-XXXX
            from django.utils import timezone
            import random, string
            ts = timezone.now().strftime("%Y%m")
            suffix = ''.join(random.choices(string.digits, k=4))
            self.reference_number = f"CR-{ts}-{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_number} — {self.title}"


class ChangeRequestItem(models.Model):
    """Individual field-level change within a ChangeRequest."""
    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="items")
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["field_name"]
        verbose_name = "Change Request Item"

    def __str__(self):
        return f"{self.change_request.reference_number} | {self.field_name}"


class ChangeApproval(TimeStampedModel):
    """Multi-step approval record for a ChangeRequest."""
    DECISION_CHOICES = [
        ("approved",  "Approved"),
        ("rejected",  "Rejected"),
        ("escalated", "Escalated"),
        ("info_required", "Information Required"),
    ]
    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="approvals")
    approver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="approvals")
    sequence_number = models.PositiveSmallIntegerField(default=1)
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    decided_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ["change_request", "sequence_number"]
        verbose_name = "Change Approval"

    def __str__(self):
        return f"{self.change_request.reference_number} — {self.approver.username}: {self.decision}"


# ---------------------------------------------------------------------------
# Import Batch — tracks bulk tag imports (CSV / API)
# ---------------------------------------------------------------------------

class ImportStatus(models.TextChoices):
    PENDING    = "pending",    "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED  = "completed",  "Completed"
    FAILED     = "failed",     "Failed"
    PARTIAL    = "partial",    "Partial (some rows failed)"


class ImportBatch(TimeStampedModel):
    """Tracks a bulk import operation."""
    batch_type = models.CharField(
        max_length=20,
        choices=[("csv", "CSV Upload"), ("excel", "Excel Upload"), ("api", "API Import"), ("seed", "System Seed")],
        default="csv",
    )
    filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=ImportStatus.choices, default=ImportStatus.PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    initiated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="import_batches"
    )
    error_log = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Import Batch"
        verbose_name_plural = "Import Batches"

    def __str__(self):
        return f"Batch {self.id} ({self.batch_type}) — {self.status} @ {self.created_at:%Y-%m-%d %H:%M}"


class ImportBatchItem(models.Model):
    """Individual row result within an ImportBatch."""
    ITEM_STATUS_CHOICES = [
        ("created",  "Created"),
        ("updated",  "Updated"),
        ("skipped",  "Skipped (duplicate)"),
        ("failed",   "Failed"),
    ]
    ITEM_ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("skip",   "Skip"),
    ]
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="items")
    row_number = models.PositiveIntegerField()
    tag_number = models.CharField(max_length=50, blank=True)
    action = models.CharField(max_length=10, choices=ITEM_ACTION_CHOICES)
    status = models.CharField(max_length=10, choices=ITEM_STATUS_CHOICES)
    error_message = models.TextField(blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    tag = models.ForeignKey(
        Tag, null=True, blank=True, on_delete=models.SET_NULL, related_name="import_items"
    )

    class Meta:
        ordering = ["batch", "row_number"]
        verbose_name = "Import Batch Item"

    def __str__(self):
        return f"Batch {self.batch_id} row {self.row_number}: {self.tag_number} ({self.status})"
