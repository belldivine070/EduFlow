"""
ASGI WebSocket URL routing.

WebSocket consumers are registered here.
HTTP requests are routed through the standard ASGI Django application.
"""
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

# Consumer URL patterns will be added here as modules are built.
websocket_urlpatterns = []

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
