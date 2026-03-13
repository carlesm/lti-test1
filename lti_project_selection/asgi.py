"""ASGI config for lti_project_selection project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lti_project_selection.settings")

application = get_asgi_application()
