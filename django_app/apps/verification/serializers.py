from rest_framework import serializers
from .models import VerificationSession, VerificationResult


class VerificationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationResult
        fields = [
            "id", "tag_number", "raw_text", "is_shorthand", "original_shorthand",
            "page_number", "confidence", "verification_status",
            "ctdb_description", "ctdb_discipline",
        ]


class VerificationSessionSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(
        source="document_revision.document.document_number", read_only=True
    )
    revision_number = serializers.CharField(
        source="document_revision.revision_number", read_only=True
    )
    results = VerificationResultSerializer(many=True, read_only=True)

    class Meta:
        model = VerificationSession
        fields = [
            "id", "document_revision", "document_number", "revision_number",
            "status", "extraction_method", "page_count",
            "started_at", "completed_at", "duration_seconds",
            "total_tags_found", "tags_valid_active", "tags_valid_void",
            "tags_not_found", "tags_shorthand", "overall_result",
            "error_message", "results",
        ]
