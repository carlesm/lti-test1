"""Middleware for the projects app."""

from typing import Callable

from django.http import HttpRequest, HttpResponse

from projects.lti_views import LTI_CONTEXT_ID_KEY


class AutoCloseDeadlineMiddleware:
    """Checks on each request if the current course's deadline has passed and closes selection."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        context_id = request.session.get(LTI_CONTEXT_ID_KEY)
        if context_id:
            try:
                from projects.models import Course
                from projects.services import auto_close_if_deadline_passed

                course = Course.objects.get(context_id=context_id)
                auto_close_if_deadline_passed(course)
            except Exception:
                pass  # Never block a request due to auto-close errors

        return self.get_response(request)
