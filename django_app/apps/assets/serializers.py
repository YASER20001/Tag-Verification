from rest_framework import serializers
from .models import (
    Plant, Area, Unit, System,
    Discipline, TagClass, CriticalityLevel,
    Tag, TagStatusHistory, TagAttribute, TagGroup, TagGroupMembership,
    ChangeRequest, ChangeRequestItem, ChangeApproval,
    ImportBatch, ImportBatchItem,
)


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = ["id", "code", "name", "location", "country", "operator", "is_active", "created_at"]


class AreaSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source="plant.code", read_only=True)
    class Meta:
        model = Area
        fields = ["id", "plant", "plant_code", "code", "name", "description"]


class UnitSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True)
    class Meta:
        model = Unit
        fields = ["id", "area", "area_name", "number", "name", "process_type"]


class DisciplineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discipline
        fields = ["id", "code", "name", "abbreviation", "colour", "is_active"]


class TagClassSerializer(serializers.ModelSerializer):
    discipline_name = serializers.CharField(source="discipline.name", read_only=True)
    class Meta:
        model = TagClass
        fields = ["id", "discipline", "discipline_name", "code", "name", "requires_safety_review", "is_active"]


class CriticalityLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriticalityLevel
        fields = ["id", "code", "name", "level", "colour", "requires_sil_study"]


class TagAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagAttribute
        fields = ["id", "attribute_name", "attribute_value", "attribute_type", "unit_of_measure"]


class TagStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source="changed_by.username", read_only=True)
    class Meta:
        model = TagStatusHistory
        fields = ["id", "old_status", "new_status", "changed_at", "changed_by_username", "reason"]


class TagListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    discipline_name = serializers.CharField(source="discipline.name", read_only=True)
    class Meta:
        model = Tag
        fields = [
            "id", "tag_number", "tag_description", "discipline_name",
            "status", "is_safety_critical", "created_at", "updated_at",
        ]


class TagDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail / create / update."""
    discipline_name = serializers.CharField(source="discipline.name", read_only=True)
    tag_class_name = serializers.CharField(source="tag_class.name", read_only=True)
    criticality_name = serializers.CharField(source="criticality_level.name", read_only=True)
    plant_code = serializers.CharField(source="plant.code", read_only=True)
    unit_number = serializers.IntegerField(source="unit.number", read_only=True)
    attributes = TagAttributeSerializer(many=True, read_only=True)
    status_history = TagStatusHistorySerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Tag
        fields = [
            "id", "tag_number", "tag_description", "alias", "service_description", "notes",
            # Hierarchy
            "plant", "plant_code", "area", "unit", "unit_number", "system",
            # Classification
            "discipline", "discipline_name", "tag_class", "tag_class_name",
            "criticality_level", "criticality_name",
            # Status
            "status", "status_reason", "status_changed_at",
            # Engineering
            "line_number", "drawing_number", "p_and_id_number", "spec_number",
            "purchase_order_number", "work_order_number",
            # Physical
            "manufacturer", "model_number", "serial_number", "size_rating",
            "design_pressure_barg", "design_temperature_c",
            # Safety
            "is_safety_critical", "is_pressure_vessel", "is_atex_rated", "sil_level",
            # Lifecycle
            "designed_at", "installed_at", "commissioned_at",
            "last_inspected_at", "next_inspection_due", "decommissioned_at", "voided_at",
            # Maintenance
            "maintenance_strategy", "maintenance_interval_days",
            # Metadata
            "created_at", "updated_at", "created_by_username",
            # Related
            "attributes", "status_history",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "voided_at", "status_changed_at"]


class TagGroupSerializer(serializers.ModelSerializer):
    tag_count = serializers.SerializerMethodField()

    class Meta:
        model = TagGroup
        fields = ["id", "name", "code", "group_type", "description", "is_active", "tag_count"]

    def get_tag_count(self, obj):
        return obj.tags.count()


class ChangeRequestSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    tag_number = serializers.CharField(source="tag.tag_number", read_only=True)

    class Meta:
        model = ChangeRequest
        fields = [
            "id", "reference_number", "request_type", "tag", "tag_number",
            "proposed_tag_number", "title", "justification", "priority",
            "status", "submitted_at", "implemented_at", "rejection_reason",
            "created_at", "created_by_username",
        ]
        read_only_fields = ["id", "reference_number", "created_at"]


class ImportBatchSerializer(serializers.ModelSerializer):
    initiated_by_username = serializers.CharField(source="initiated_by.username", read_only=True)

    class Meta:
        model = ImportBatch
        fields = [
            "id", "batch_type", "filename", "status",
            "total_rows", "created_count", "updated_count", "skipped_count", "failed_count",
            "started_at", "completed_at", "initiated_by_username", "error_log",
        ]
