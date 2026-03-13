"""Views for the projects app."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from projects.decorators import lti_required


@lti_required
def professor_dashboard(request: HttpRequest) -> HttpResponse:
    """Professor dashboard — placeholder; full implementation in US-005."""
    return render(request, "projects/professor_dashboard.html")


@lti_required
def student_view(request: HttpRequest) -> HttpResponse:
    """Student project list view — placeholder; full implementation in US-009."""
    return render(request, "projects/student_view.html")
