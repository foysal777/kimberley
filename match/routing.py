from django.urls import re_path
from match import consumers
from match.consumers.chat_consumers import ChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    # 1-to-1 conversation chat
    re_path(r"ws/chat/(?P<conversation_id>\d+)/$", ChatConsumer.as_asgi()),
    # user notifications
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),
]
