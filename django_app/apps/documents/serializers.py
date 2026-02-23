from rest_framework import serializers
from .models import DocumentType, Document, DocumentRevision, DocumentFile, TagDocumentLink


class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ["id", "code", "name", "requires_tag_verification", "is_active"]


class DocumentRevisionSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source="document.document_number", read_only=True)
    approved_by_username = serializers.CharField(source="approved_by.username", read_only=True)

    class Meta:
        model = DocumentRevision
        fields = [
            "id", "document", "document_number", "revision_number", "title", "status",
            "verification_status", "tags_found", "tags_valid_active", "tags_valid_void",
            "tags_not_found", "tags_shorthand",
            "approved_at", "approved_by_username", "override_justification",
            "revision_date", "author", "created_at",
        ]
        read_only_fields = ["id", "created_at", "approved_at"]


class DocumentListSerializer(serializers.ModelSerializer):
    document_type_name = serializers.CharField(source="document_type.name", read_only=True)
    current_revision_number = serializers.CharField(
        source="current_revision.revision_number", read_only=True
    )
    current_verification_status = serializers.CharField(
        source="current_revision.verification_status", read_only=True
    )

    class Meta:
        model = Document
        fields = [
            "id", "document_number", "title", "document_type_name",
            "current_revision_number", "current_verification_status",
            "is_active", "created_at",
        ]


class DocumentDetailSerializer(serializers.ModelSerializer):
    document_type_name = serializers.CharField(source="document_type.name", read_only=True)
    revisions = DocumentRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "document_number", "title", "document_type", "document_type_name",
            "plant", "discipline", "contractor", "project_number", "is_active",
            "created_at", "updated_at", "revisions",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TagDocumentLinkSerializer(serializers.ModelSerializer):
    tag_number = serializers.CharField(source="tag.tag_number", read_only=True)
    tag_description = serializers.CharField(source="tag.tag_description", read_only=True)
    document_number = serializers.CharField(
        source="document_revision.document.document_number", read_only=True
    )
    revision_number = serializers.CharField(
        source="document_revision.revision_number", read_only=True
    )

    class Meta:
        model = TagDocumentLink
        fields = [
            "id", "tag", "tag_number", "tag_description",
            "document_revision", "document_number", "revision_number",
            "verification_status", "page_number", "is_shorthand",
            "original_shorthand", "created_at",
        ]
