"""
Verification Models
====================
Tracks every verification session and per-tag result.
"""
from django.db import models
from django.contrib.auth.models import User

from apps.assets.models import Tag, TimeStampedModel
from apps.documents.models import DocumentRevision


class SessionStatus(models.TextChoices):
    STARTED   = "started",   "Started"
    COMPLETED = "completed", "Completed"
    FAILED    = "failed",    "Failed"


class VerificationSession(TimeStampedModel):
    """
    One full verification run against a DocumentRevision.
    Records timing, extraction method, and aggregate results.
    """
    document_revision = models.ForeignKey(
        DocumentRevision, on_delete=models.CASCADE, related_name="verification_sessions"
    )
    status = models.CharField(
        max_length=20, choices=SessionStatus.choices, default=SessionStatus.STARTED
    )
    extraction_method = models.CharField(max_length=30, blank=True)
    page_count = models.PositiveSmallIntegerField(default=0)
    initiated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="verification_sessions"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Aggregate counts
    total_tags_found = models.PositiveIntegerField(default=0)
    tags_valid_active = models.PositiveIntegerField(default=0)
    tags_valid_void = models.PositiveIntegerField(default=0)
    tags_not_found = models.PositiveIntegerField(default=0)
    tags_shorthand = models.PositiveIntegerField(default=0)
    overall_result = models.CharField(
        max_length=20,
        choices=[("pass", "Pass"), ("issues", "Has Issues"), ("pending", "Pending")],
        default="pending",
    )
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Verification Session"

    def __str__(self):
        rev = self.document_revision
        return f"Session {self.id} — {rev.document.document_number} Rev {rev.revision_number} ({self.overall_result})"


class VerificationResult(TimeStampedModel):
    """
    Per-tag result within a VerificationSession.
    One row per unique tag number encountered in the document.
    """
    session = models.ForeignKey(
        VerificationSession, on_delete=models.CASCADE, related_name="results"
    )
    tag_number = models.CharField(max_length=50, db_index=True)
    raw_text = models.CharField(max_length=200, blank=True)
    is_shorthand = models.BooleanField(default=False)
    original_shorthand = models.CharField(max_length=200, blank=True)
    page_number = models.PositiveSmallIntegerField(null=True, blank=True)
    confidence = models.FloatField(default=1.0)

    verification_status = models.CharField(
        max_length=30,
        choices=[
            ("valid_active",       "Valid — Active"),
            ("valid_void",         "Valid — Void (flag)"),
            ("not_found",          "Not Found"),
            ("shorthand_detected", "Shorthand Detected"),
        ],
    )
    ctdb_description = models.TextField(blank=True)
    ctdb_discipline = models.CharField(max_length=100, blank=True)
    tag = models.ForeignKey(
        Tag, null=True, blank=True, on_delete=models.SET_NULL, related_name="verification_results"
    )

    class Meta:
        ordering = ["session", "tag_number"]
        verbose_name = "Verification Result"
        indexes = [
            models.Index(fields=["session", "verification_status"]),
            models.Index(fields=["tag_number"]),
        ]

    def __str__(self):
        return f"{self.tag_number} — {self.verification_status} (Session {self.session_id})"
