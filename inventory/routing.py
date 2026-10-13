from django.urls import path

from .consumers import StockConsumer

# WebSocket routes for the ASGI application.
websocket_urlpatterns = [
    path("ws/stock/", StockConsumer.as_asgi()),
]
