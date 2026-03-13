"""Views for the projects app."""

from datetime import datetime

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from projects.decorators import lti_required
from projects.forms import ProjectForm
from projects.lti_views import INSTRUCTOR_ROLE, LTI_CONTEXT_ID_KEY, LTI_ROLES_KEY
from projects.models import Course, Project
from projects import services


def _get_instructor_course(request: HttpRequest) -> tuple[Course, HttpResponse | None]:
    """Return (course, None) for valid instructor sessions, or (None, error_response)."""
    roles = request.session.get(LTI_ROLES_KEY, [])
    if INSTRUCTOR_ROLE not in roles:
        return None, HttpResponseForbidden("Instructor role required.")  # type: ignore[return-value]
    context_id = request.session[LTI_CONTEXT_ID_KEY]
    course = Course.objects.get(context_id=context_id)
    return course, None


@lti_required
def professor_dashboard(request: HttpRequest) -> HttpResponse:
    """Professor dashboard — shows course info and project list."""
    course, err = _get_instructor_course(request)
    if err:
        return err

    projects = course.projects.filter(is_deleted=False)

    return render(
        request,
        "projects/professor_dashboard.html",
        {"course": course, "projects": projects},
    )


@lti_required
def project_create(request: HttpRequest) -> HttpResponse:
    """Create a new project for the current course."""
    course, err = _get_instructor_course(request)
    if err:
        return err

    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.course = course
            project.save()
            return redirect("projects:professor_dashboard")
    else:
        form = ProjectForm()

    return render(
        request,
        "projects/project_form.html",
        {"form": form, "course": course, "action": "Create"},
    )


@lti_required
def project_edit(request: HttpRequest, project_id: int) -> HttpResponse:
    """Edit an existing project (only when phase is 'setup')."""
    course, err = _get_instructor_course(request)
    if err:
        return err

    project = get_object_or_404(Project, pk=project_id, course=course, is_deleted=False)

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect("projects:professor_dashboard")
    else:
        form = ProjectForm(instance=project)

    return render(
        request,
        "projects/project_form.html",
        {"form": form, "course": course, "action": "Edit", "project": project},
    )


@lti_required
def project_delete(request: HttpRequest, project_id: int) -> HttpResponse:
    """Delete a project — only allowed when phase is 'setup'."""
    course, err = _get_instructor_course(request)
    if err:
        return err

    project = get_object_or_404(Project, pk=project_id, course=course, is_deleted=False)

    if request.method == "POST":
        if course.phase != Course.PHASE_SETUP:
            projects = course.projects.filter(is_deleted=False)
            return render(
                request,
                "projects/professor_dashboard.html",
                {
                    "course": course,
                    "projects": projects,
                    "error": "Cannot delete projects after selection has opened",
                },
            )
        project.is_deleted = True
        project.save()
        return redirect("projects:professor_dashboard")

    return redirect("projects:professor_dashboard")


def _parse_deadline(value: str) -> datetime | None:
    """Parse a datetime-local string into an aware datetime, or return None."""
    if not value:
        return None
    try:
        naive = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        return timezone.make_aware(naive)
    except ValueError:
        return None


@lti_required
def open_selection_view(request: HttpRequest) -> HttpResponse:
    """POST: transition course setup → open."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    if request.method == "POST":
        deadline = _parse_deadline(request.POST.get("deadline", ""))
        try:
            services.open_selection(course, deadline=deadline)
        except ValueError as exc:
            projects = course.projects.filter(is_deleted=False)
            return render(
                request,
                "projects/professor_dashboard.html",
                {"course": course, "projects": projects, "error": str(exc)},
            )
    return redirect("projects:professor_dashboard")


@lti_required
def close_selection_view(request: HttpRequest) -> HttpResponse:
    """POST: transition course open → closed."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    if request.method == "POST":
        try:
            services.close_selection(course)
        except ValueError as exc:
            projects = course.projects.filter(is_deleted=False)
            return render(
                request,
                "projects/professor_dashboard.html",
                {"course": course, "projects": projects, "error": str(exc)},
            )
    return redirect("projects:professor_dashboard")


@lti_required
def extend_deadline_view(request: HttpRequest) -> HttpResponse:
    """POST: extend deadline for an open course."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    if request.method == "POST":
        deadline = _parse_deadline(request.POST.get("deadline", ""))
        if deadline is None:
            projects = course.projects.filter(is_deleted=False)
            return render(
                request,
                "projects/professor_dashboard.html",
                {"course": course, "projects": projects, "error": "A valid deadline is required."},
            )
        try:
            services.extend_deadline(course, deadline)
        except ValueError as exc:
            projects = course.projects.filter(is_deleted=False)
            return render(
                request,
                "projects/professor_dashboard.html",
                {"course": course, "projects": projects, "error": str(exc)},
            )
    return redirect("projects:professor_dashboard")


@lti_required
def assignment_results_view(request: HttpRequest) -> HttpResponse:
    """Assignment results page — stub; full implementation in US-013."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    return render(request, "projects/assignment_results.html", {"course": course})


@lti_required
def run_assignment_view(request: HttpRequest) -> HttpResponse:
    """POST: run assignment algorithm — stub; full implementation in US-012."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    return redirect("projects:assignment_results")


@lti_required
def publish_results_view(request: HttpRequest) -> HttpResponse:
    """POST: publish results — stub; full implementation in US-015."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    return redirect("projects:professor_dashboard")


@lti_required
def student_view(request: HttpRequest) -> HttpResponse:
    """Student project list view — placeholder; full implementation in US-009."""
    return render(request, "projects/student_view.html")
