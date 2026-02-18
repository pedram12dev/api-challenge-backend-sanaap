import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def notify_document_change(*, action: str, document, user):
    """
    Send a WebSocket notification to all connected clients.
    Fails silently if channels layer is not available.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            "document_notifications",
            {
                "type": "document.notification",
                "action": action,
                "document": {
                    "id": document.id,
                    "title": document.title,
                    "file_name": document.file_name,
                },
                "user": user.username,
                "timestamp": timezone.now().isoformat(),
            },
        )
    except Exception as e:
        logger.warning("Failed to send WebSocket notification: %s", e)
