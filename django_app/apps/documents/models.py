"""
Document Management Models
===========================
Full document lifecycle with revisions, files, and tag linking.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from apps.assets.models import Tag, Plant, Discipline, TimeStampedModel, AuditedModel


# ---------------------------------------------------------------------------
# Document Type Lookup
# ---------------------------------------------------------------------------

class DocumentType(TimeStampedModel):
    """
    Document type lookup (P&ID, PFD, Datasheet, Equipment List, etc.)
    """
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    requires_tag_verification = models.BooleanField(
        default=True, help_text="Does this document type require tag verification?"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Document Type"

    def __str__(self):
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Master Document Record
# ---------------------------------------------------------------------------

class Document(AuditedModel):
    """
    Master document record. One document can have many revisions.
    """
    document_number = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    document_type = models.ForeignKey(
        DocumentType, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    plant = models.ForeignKey(
        Plant, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    discipline = models.ForeignKey(
        Discipline, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    contractor = models.CharField(max_length=200, blank=True)
    project_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    current_revision = models.OneToOneField(
        "DocumentRevision",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="current_for_document",
    )

    class Meta:
        ordering = ["document_number"]
        verbose_name = "Document"
        indexes = [
            models.Index(fields=["document_number"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.document_number} — {self.title}"

    def get_latest_revision(self):
        return self.revisions.order_by("-created_at").first()


# ---------------------------------------------------------------------------
# Document Revision — each revision is a first-class record
# ---------------------------------------------------------------------------

class RevisionStatus(models.TextChoices):
    DRAFT     = "draft",     "Draft"
    IFR       = "ifr",       "Issued for Review (IFR)"
    IFC       = "ifc",       "Issued for Construction (IFC)"
    AFC       = "afc",       "Approved for Construction (AFC)"
    APPROVED  = "approved",  "Approved"
    SUPERSEDED= "superseded","Superseded"
    CANCELLED = "cancelled", "Cancelled"


class DocumentRevision(AuditedModel):
    """
    A specific revision of a document.
    Stores verification summary and links to uploaded file.
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.CharField(max_length=10, help_text='e.g. 0, A, B, 1, 2, P1')
    title = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20, choices=RevisionStatus.choices, default=RevisionStatus.DRAFT
    )

    # Verification summary (populated after verification)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ("pending",  "Pending"),
            ("pass",     "Pass"),
            ("issues",   "Has Issues"),
            ("approved", "Approved with Override"),
            ("skipped",  "Verification Skipped"),
        ],
        default="pending",
    )
    tags_found = models.PositiveIntegerField(default=0)
    tags_valid_active = models.PositiveIntegerField(default=0)
    tags_valid_void = models.PositiveIntegerField(default=0)
    tags_not_found = models.PositiveIntegerField(default=0)
    tags_shorthand = models.PositiveIntegerField(default=0)

    # Approval / override
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_revisions"
    )
    override_justification = models.TextField(blank=True)

    # Revision metadata
    revision_date = models.DateField(null=True, blank=True)
    revision_purpose = models.TextField(blank=True)
    author = models.CharField(max_length=200, blank=True)
    checker = models.CharField(max_length=200, blank=True)
    approver_name = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["document", "-created_at"]
        unique_together = [("document", "revision_number")]
        verbose_name = "Document Revision"

    def __str__(self):
        return f"{self.document.document_number} Rev {self.revision_number}"

    def approve(self, user=None, justification=""):
        self.verification_status = "approved"
        self.approved_at = timezone.now()
        self.approved_by = user
        self.override_justification = justification
        self.save()


# ---------------------------------------------------------------------------
# Document File — physical file storage reference per revision
# ---------------------------------------------------------------------------

class DocumentFile(TimeStampedModel):
    """Physical file attached to a DocumentRevision."""
    revision = models.OneToOneField(
        DocumentRevision, on_delete=models.CASCADE, related_name="file"
    )
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveBigIntegerField(default=0, help_text="File size in bytes")
    mime_type = models.CharField(max_length=100, blank=True)
    checksum_md5 = models.CharField(max_length=32, blank=True)
    extraction_method = models.CharField(
        max_length=30, blank=True,
        help_text="pymupdf / pdfplumber / pypdf / ocr / image_ocr",
    )
    page_count = models.PositiveSmallIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_files"
    )

    class Meta:
        verbose_name = "Document File"

    def __str__(self):
        return self.filename

    @property
    def file_size_human(self):
        size = self.file_size
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# ---------------------------------------------------------------------------
# Tag ↔ Document Link — confirmed relationship from verification
# ---------------------------------------------------------------------------

class TagDocumentLink(TimeStampedModel):
    """
    Confirmed link between a Tag and a DocumentRevision.
    Created (or updated) each time verification is saved.
    """
    tag = models.ForeignKey(
        Tag, on_delete=models.CASCADE, related_name="document_links"
    )
    document_revision = models.ForeignKey(
        DocumentRevision, on_delete=models.CASCADE, related_name="tag_links"
    )
    verification_status = models.CharField(
        max_length=30,
        choices=[
            ("valid_active",       "Valid (Active)"),
            ("valid_void",         "Valid (Void — flag)"),
            ("not_found",          "Not Found in CTDB"),
            ("shorthand_detected", "Shorthand Detected"),
        ],
    )
    raw_text = models.CharField(max_length=200, blank=True)
    page_number = models.PositiveSmallIntegerField(null=True, blank=True)
    is_shorthand = models.BooleanField(default=False)
    original_shorthand = models.CharField(max_length=200, blank=True)
    linked_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["tag__tag_number"]
        unique_together = [("tag", "document_revision")]
        verbose_name = "Tag-Document Link"
        indexes = [
            models.Index(fields=["tag", "verification_status"]),
            models.Index(fields=["document_revision"]),
        ]

    def __str__(self):
        return f"{self.tag.tag_number} ↔ {self.document_revision}"
