from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Shared helpers for pushing live stock changes to connected WebSocket clients.
STOCK_GROUP = "stock_updates"


def serialize_product(product):
    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "category": product.category.name if product.category else "Uncategorized",
        "quantity": product.quantity,
        "unit": product.unit,
        "min_stock_level": product.min_stock_level,
        "is_low_stock": product.is_low_stock,
    }


def broadcast_stock_update(product):
    """Push a single product's new state to every connected stock client."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        STOCK_GROUP,
        {"type": "stock.update", "product": serialize_product(product)},
    )


def broadcast_event(event):
    """Notify connected clients that something changed (e.g. a sale or return)."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        STOCK_GROUP,
        {"type": "notify", "event": event},
    )
