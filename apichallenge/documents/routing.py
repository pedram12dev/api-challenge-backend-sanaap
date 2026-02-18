from django.urls import path

from apichallenge.documents.consumers import DocumentNotificationConsumer

websocket_urlpatterns = [
    path("ws/documents/", DocumentNotificationConsumer.as_asgi()),
]
