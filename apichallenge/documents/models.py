import uuid

from django.conf import settings
from django.db import models

from apichallenge.common.models import BaseModel


def document_upload_path(instance, filename):
    """Generate unique upload path for documents."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"documents/{instance.uploaded_by_id}/{uuid.uuid4().hex}.{ext}"


class Document(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    file = models.FileField(upload_to=document_upload_path)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.file_name})"


class AuditLog(models.Model):
    """Tracks all access and modifications to documents."""

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        READ = "read", "Read"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        DOWNLOAD = "download", "Download"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    document_title = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.action}] {self.document_title} by {self.user} @ {self.timestamp}"
