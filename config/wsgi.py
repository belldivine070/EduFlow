"""
WSGI config for EduFlow.

Exposes the WSGI callable as a module-level variable named ``application``.
Daphne is the preferred ASGI server; this WSGI file exists for compatibility
with traditional WSGI hosting if needed.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
