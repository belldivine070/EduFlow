"""
ASGI config for EduFlow.

Exposes the ASGI callable as a module-level variable named ``application``.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.routing import application  # noqa: F401, E402
