"""
Audit Trail
============
System-wide immutable audit log.
"""
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class AuditAction(models.TextChoices):
    CREATE  = "create",  "Create"
    UPDATE  = "update",  "Update"
    DELETE  = "delete",  "Delete"
    VIEW    = "view",    "View"
    EXPORT  = "export",  "Export"
    IMPORT  = "import",  "Import"
    APPROVE = "approve", "Approve"
    REJECT  = "reject",  "Reject"
    LOGIN   = "login",   "Login"
    LOGOUT  = "logout",  "Logout"


class AuditLog(models.Model):
    """
    Immutable system-wide audit entry.
    Records who did what to which object, and what changed.
    """
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=20, choices=AuditAction.choices)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Generic FK to any model
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL
    )
    object_id = models.CharField(max_length=50, blank=True, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(max_length=300, blank=True)

    # Field-level diff
    changes = models.JSONField(
        default=dict, blank=True,
        help_text="Dict of {field: [old_value, new_value]}",
    )

    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    extra = models.JSONField(default=dict, blank=True, help_text="Extra context data")

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        username = self.user.username if self.user else "anonymous"
        return f"{username} {self.action} {self.object_repr} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"
