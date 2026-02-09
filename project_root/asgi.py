import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_root.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from match.middleware import JwtAuthMiddlewareStack


django_asgi_app = get_asgi_application()


import match.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddlewareStack(
        URLRouter(match.routing.websocket_urlpatterns)
    ),
})
