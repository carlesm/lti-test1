"""Views for the projects app."""

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render

from projects.decorators import lti_required
from projects.lti_views import INSTRUCTOR_ROLE, LTI_CONTEXT_ID_KEY, LTI_ROLES_KEY
from projects.models import Course


@lti_required
def professor_dashboard(request: HttpRequest) -> HttpResponse:
    """Professor dashboard — shows course info and project list."""
    roles = request.session.get(LTI_ROLES_KEY, [])
    if INSTRUCTOR_ROLE not in roles:
        return HttpResponseForbidden("Instructor role required.")

    context_id = request.session[LTI_CONTEXT_ID_KEY]
    course = Course.objects.get(context_id=context_id)
    projects = course.projects.filter(is_deleted=False)

    return render(
        request,
        "projects/professor_dashboard.html",
        {"course": course, "projects": projects},
    )


@lti_required
def student_view(request: HttpRequest) -> HttpResponse:
    """Student project list view — placeholder; full implementation in US-009."""
    return render(request, "projects/student_view.html")
