import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class DocumentNotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer that broadcasts notifications to all connected
    users when a document is created or updated.

    Connect: ws://<host>/ws/documents/
    """

    GROUP_NAME = "document_notifications"

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Client messages are not expected; ignore them.
        pass

    async def document_notification(self, event):
        """Handler for messages sent to the group."""
        await self.send_json(
            {
                "type": event["action"],
                "document": event["document"],
                "user": event["user"],
                "timestamp": event["timestamp"],
            }
        )
