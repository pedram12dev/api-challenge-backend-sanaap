from django.contrib import admin

from apichallenge.documents.models import Document, AuditLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "file_name", "file_size", "uploaded_by", "created_at")
    list_filter = ("content_type", "created_at")
    search_fields = ("title", "file_name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "action", "document_title", "user", "ip_address", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("document_title", "details")
    readonly_fields = ("timestamp",)
