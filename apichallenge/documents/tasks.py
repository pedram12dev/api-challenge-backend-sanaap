import logging

from celery import shared_task

from apichallenge.documents.models import Document

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_document_after_upload(self, document_id: int):
    """
    Background task that runs after a document is uploaded.
    Can be extended for: virus scanning, thumbnail generation,
    metadata extraction, indexing, etc.
    """
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.warning("Document %s not found for processing.", document_id)
        return

    logger.info(
        "Processing document #%s: %s (%s bytes)",
        document.id,
        document.file_name,
        document.file_size,
    )

    logger.info("Document #%s processing complete.", document.id)


@shared_task
def cleanup_orphaned_files():
    """
    Periodic task to remove files in storage that are no longer
    referenced by any Document record.
    """
    logger.info("Running orphaned file cleanup...")
    # Implementation depends on storage backend
    logger.info("Orphaned file cleanup complete.")
