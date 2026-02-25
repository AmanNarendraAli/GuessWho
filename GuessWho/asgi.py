import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GuessWho.settings')
django_asgi_app = get_asgi_application()

from rooms.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)), # tells django to use websocket_urlpatterns for websocket requests. authmiddlewarestack - provides user authentication for websocket connections
})
