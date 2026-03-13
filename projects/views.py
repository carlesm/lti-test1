"""Views for the projects app."""

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from projects.decorators import lti_required
from projects.forms import ProjectForm
from projects.lti_views import INSTRUCTOR_ROLE, LTI_CONTEXT_ID_KEY, LTI_ROLES_KEY
from projects.models import Course, Project


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


@lti_required
def student_view(request: HttpRequest) -> HttpResponse:
    """Student project list view — placeholder; full implementation in US-009."""
    return render(request, "projects/student_view.html")
