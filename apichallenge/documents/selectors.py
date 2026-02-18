import hashlib
import logging

from django.core.cache import cache
from django.db.models import QuerySet

from apichallenge.documents.models import Document, AuditLog
from apichallenge.documents.filters import DocumentFilter

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 15  # 15 minutes


def _build_list_cache_key(filters: dict | None) -> str:
    """Build a deterministic cache key from query filters."""
    if not filters:
        return "documents:list:all"
    sorted_params = sorted(filters.items())
    raw = "&".join(f"{k}={v}" for k, v in sorted_params if v)
    hashed = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"documents:list:{hashed}"


def document_list(*, filters: dict | None = None) -> QuerySet[Document]:
    """Return filtered queryset of documents (list cache)."""
    cache_key = _build_list_cache_key(filters)
    cached_ids = cache.get(cache_key)

    if cached_ids is not None:
        logger.debug("Cache HIT for %s", cache_key)
        # Preserve ordering from cached IDs
        qs = Document.objects.select_related("uploaded_by").filter(id__in=cached_ids)
        return qs

    logger.debug("Cache MISS for %s", cache_key)
    qs = Document.objects.select_related("uploaded_by").all()

    if filters:
        qs = DocumentFilter(filters, queryset=qs).qs

    # Cache the list of document IDs
    doc_ids = list(qs.values_list("id", flat=True))
    cache.set(cache_key, doc_ids, CACHE_TTL)

    return qs


def document_get(*, pk: int) -> Document | None:
    """Get a single document by pk (cached)."""
    cache_key = f"documents:detail:{pk}"
    cached = cache.get(cache_key)

    if cached is not None:
        logger.debug("Cache HIT for %s", cache_key)
        return cached

    logger.debug("Cache MISS for %s", cache_key)
    try:
        doc = Document.objects.select_related("uploaded_by").get(pk=pk)
        cache.set(cache_key, doc, CACHE_TTL)
        return doc
    except Document.DoesNotExist:
        return None


def invalidate_document_cache(document_id: int | None = None) -> None:
    """Invalidate document caches after create/update/delete."""
    # Always invalidate list caches (prefix-based)
    # django-redis supports delete_pattern
    try:
        cache.delete_pattern("documents:list:*")
    except AttributeError:
        # Fallback for non-redis cache backends (e.g. in tests)
        cache.clear()

    # Invalidate specific document detail cache
    if document_id is not None:
        cache.delete(f"documents:detail:{document_id}")


def audit_log_list(*, document_id: int | None = None) -> QuerySet[AuditLog]:
    """Return audit logs, optionally filtered by document."""
    qs = AuditLog.objects.select_related("user", "document").all()

    if document_id is not None:
        qs = qs.filter(document_id=document_id)

    return qs
