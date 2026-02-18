from django.db import transaction

from apichallenge.documents.models import Document, AuditLog
from apichallenge.users.models import BaseUser


def _get_client_ip(request) -> str | None:
    """Extract client IP from request."""
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def create_audit_log(
    *,
    user: BaseUser,
    document: Document | None,
    action: str,
    request=None,
    details: str = "",
) -> AuditLog:
    """Create an audit log entry."""
    return AuditLog.objects.create(
        user=user,
        document=document,
        action=action,
        document_title=document.title if document else "",
        ip_address=_get_client_ip(request),
        details=details,
    )


@transaction.atomic
def document_create(
    *,
    title: str,
    description: str = "",
    file,
    uploaded_by: BaseUser,
    request=None,
) -> Document:
    """Create a new document and log the action."""
    document = Document(
        title=title,
        description=description,
        file=file,
        file_name=file.name,
        file_size=file.size,
        content_type=getattr(file, "content_type", ""),
        uploaded_by=uploaded_by,
    )
    document.full_clean()
    document.save()

    create_audit_log(
        user=uploaded_by,
        document=document,
        action=AuditLog.Action.CREATE,
        request=request,
        details=f"Uploaded file: {file.name} ({file.size} bytes)",
    )

    # Send real-time WebSocket notification
    from apichallenge.documents.notifications import notify_document_change

    notify_document_change(action="created", document=document, user=uploaded_by)

    # Invalidate list caches
    from apichallenge.documents.selectors import invalidate_document_cache

    invalidate_document_cache()

    return document


@transaction.atomic
def document_update(
    *,
    document: Document,
    title: str | None = None,
    description: str | None = None,
    file=None,
    updated_by: BaseUser,
    request=None,
) -> Document:
    """Update a document and log the action."""
    changes = []

    if title is not None and title != document.title:
        changes.append(f"title: '{document.title}' → '{title}'")
        document.title = title

    if description is not None and description != document.description:
        changes.append("description updated")
        document.description = description

    if file is not None:
        changes.append(f"file replaced: {document.file_name} → {file.name}")
        # Delete old file from storage
        if document.file:
            document.file.delete(save=False)
        document.file = file
        document.file_name = file.name
        document.file_size = file.size
        document.content_type = getattr(file, "content_type", "")

    if changes:
        document.full_clean()
        document.save()

        create_audit_log(
            user=updated_by,
            document=document,
            action=AuditLog.Action.UPDATE,
            request=request,
            details="; ".join(changes),
        )

        # Send real-time WebSocket notification
        from apichallenge.documents.notifications import notify_document_change

        notify_document_change(action="updated", document=document, user=updated_by)

        # Invalidate caches
        from apichallenge.documents.selectors import invalidate_document_cache

        invalidate_document_cache(document_id=document.id)

    return document


@transaction.atomic
def document_delete(
    *,
    document: Document,
    deleted_by: BaseUser,
    request=None,
) -> None:
    """Delete a document and log the action."""
    title = document.title
    file_name = document.file_name

    create_audit_log(
        user=deleted_by,
        document=None,  # document will be deleted
        action=AuditLog.Action.DELETE,
        request=request,
        details=f"Deleted document: {title} ({file_name})",
    )

    # Delete file from storage
    if document.file:
        document.file.delete(save=False)

    doc_id = document.id
    document.delete()

    # Invalidate caches
    from apichallenge.documents.selectors import invalidate_document_cache

    invalidate_document_cache(document_id=doc_id)
