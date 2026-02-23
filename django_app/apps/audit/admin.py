from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "object_repr", "ip_address", "timestamp"]
    list_filter = ["action"]
    search_fields = ["user__username", "object_repr", "request_path"]
    readonly_fields = [
        "user", "action", "timestamp", "content_type", "object_id",
        "object_repr", "changes", "ip_address", "user_agent", "request_path",
    ]

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
