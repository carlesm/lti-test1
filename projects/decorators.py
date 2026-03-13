"""Decorators for the projects app."""

from functools import wraps
from typing import Callable

from django.http import HttpRequest, HttpResponseForbidden

from projects.lti_views import LTI_CONTEXT_ID_KEY


def lti_required(view_func: Callable) -> Callable:
    """Raises 403 if no valid LTI session exists."""

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if LTI_CONTEXT_ID_KEY not in request.session:
            return HttpResponseForbidden("LTI session required.")
        return view_func(request, *args, **kwargs)

    return wrapper
