from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework import serializers
from django_filters.rest_framework import DjangoFilterBackend

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    model_name = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "username", "action", "timestamp",
            "model_name", "object_id", "object_repr",
            "changes", "ip_address", "request_path",
        ]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user", "content_type").order_by("-timestamp")
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["action", "user"]
    search_fields = ["object_repr", "user__username"]
    ordering_fields = ["timestamp"]
