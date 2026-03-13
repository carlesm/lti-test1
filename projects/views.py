"""Views for the projects app."""

from datetime import datetime

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from django.http import HttpResponseBadRequest
from django.contrib import messages

from projects.decorators import lti_required
from projects.forms import ProjectForm
from projects.lti_views import INSTRUCTOR_ROLE, LEARNER_ROLE, LTI_CONTEXT_ID_KEY, LTI_ROLES_KEY, LTI_SUB_KEY
from projects.models import Assignment, Course, Preference, Project, StudentEnrollment
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
    """Assignment results page — shows table of student assignments."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    if course.phase != Course.PHASE_ASSIGNED:
        return redirect("projects:professor_dashboard")
    assignments = list(
        Assignment.objects.filter(enrollment__course=course)
        .select_related("enrollment", "project")
        .order_by("enrollment__name")
    )
    all_projects = list(course.projects.filter(is_deleted=False))
    all_assigned_ids = {a.project_id for a in assignments if a.project_id is not None}

    assignments_data = []
    for a in assignments:
        taken_by_others = all_assigned_ids - ({a.project_id} if a.project_id else set())
        available = [p for p in all_projects if p.pk not in taken_by_others]
        assignments_data.append({"assignment": a, "available_projects": available})

    return render(
        request,
        "projects/assignment_results.html",
        {"course": course, "assignments_data": assignments_data},
    )


@lti_required
def override_assignment_view(request: HttpRequest, enrollment_id: int) -> HttpResponse:
    """POST: override a student's assignment. Returns 403 if phase is not 'assigned'."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    if course.phase != Course.PHASE_ASSIGNED:
        return HttpResponseForbidden("Overrides only allowed during 'assigned' phase.")
    if request.method != "POST":
        return redirect("projects:assignment_results")

    enrollment = get_object_or_404(StudentEnrollment, pk=enrollment_id, course=course)
    assignment = get_object_or_404(Assignment, enrollment=enrollment)

    new_project_id_raw = request.POST.get("project_id", "")
    if new_project_id_raw == "" or new_project_id_raw == "unassigned":
        new_project: Project | None = None
    else:
        try:
            new_project = get_object_or_404(Project, pk=int(new_project_id_raw), course=course, is_deleted=False)
        except (ValueError, TypeError):
            return HttpResponseBadRequest("Invalid project ID.")

    assignment.project = new_project
    assignment.save(update_fields=["project"])
    return redirect("projects:assignment_results")


@lti_required
def run_assignment_view(request: HttpRequest) -> HttpResponse:
    """POST: run the assignment algorithm and redirect to assignment results."""
    course, err = _get_instructor_course(request)
    if err:
        return err
    if request.method == "POST":
        services.run_assignment(course)
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
    """Student project list view."""
    roles = request.session.get(LTI_ROLES_KEY, [])
    if LEARNER_ROLE not in roles:
        return HttpResponseForbidden("Learner role required.")

    context_id = request.session[LTI_CONTEXT_ID_KEY]
    course = Course.objects.get(context_id=context_id)

    # Auto-close if deadline passed
    # (middleware already handles this, but refresh from DB)
    course.refresh_from_db()

    if course.phase == Course.PHASE_PUBLISHED:
        return redirect("projects:student_result")

    if course.phase in (Course.PHASE_SETUP, Course.PHASE_CLOSED):
        return render(
            request,
            "projects/student_view.html",
            {"course": course, "message": "Selection is not open yet."},
        )

    if course.phase == Course.PHASE_ASSIGNED:
        return render(
            request,
            "projects/student_view.html",
            {"course": course, "message": "Assignments are being finalized."},
        )

    # Phase is OPEN — show project cards with Taken/Available status
    lti_sub = request.session[LTI_SUB_KEY]
    enrollment = get_object_or_404(StudentEnrollment, course=course, lti_sub=lti_sub)

    projects = list(course.projects.filter(is_deleted=False))
    assigned_project_ids = set(
        Assignment.objects.filter(enrollment__course=course, project__isnull=False)
        .values_list("project_id", flat=True)
    )

    projects_with_status = [
        {"project": p, "taken": p.pk in assigned_project_ids}
        for p in projects
    ]

    # Build the ranked list pre-populated with existing preferences
    try:
        existing_pref_ids: list[int] = list(enrollment.preference.ordered_project_ids)
    except Preference.DoesNotExist:
        existing_pref_ids = []

    project_map = {p.pk: p for p in projects}
    ranked_projects = [project_map[pk] for pk in existing_pref_ids if pk in project_map]
    unranked_projects = [p for p in projects if p.pk not in set(existing_pref_ids)]

    return render(
        request,
        "projects/student_view.html",
        {
            "course": course,
            "projects_with_status": projects_with_status,
            "ranked_projects": ranked_projects,
            "unranked_projects": unranked_projects,
        },
    )


@lti_required
def submit_preferences(request: HttpRequest) -> HttpResponse:
    """POST: save ranked project preferences for a student."""
    roles = request.session.get(LTI_ROLES_KEY, [])
    if LEARNER_ROLE not in roles:
        return HttpResponseForbidden("Learner role required.")

    context_id = request.session[LTI_CONTEXT_ID_KEY]
    course = Course.objects.get(context_id=context_id)
    course.refresh_from_db()

    if course.phase != Course.PHASE_OPEN:
        return HttpResponseBadRequest("Selection is not open.")

    if request.method != "POST":
        return redirect("projects:student_view")

    # Parse submitted project PKs (ordered list from form)
    project_ids_raw = request.POST.getlist("project_ids")
    try:
        project_ids = [int(pk) for pk in project_ids_raw]
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid project IDs.")

    # Validate all PKs belong to current course
    valid_ids = set(course.projects.filter(is_deleted=False).values_list("pk", flat=True))
    if not all(pk in valid_ids for pk in project_ids):
        return HttpResponseBadRequest("Some projects do not belong to this course.")

    # Validate ranking count
    total_projects = len(valid_ids)
    if total_projects > 3:
        if len(project_ids) < 3:
            return HttpResponseBadRequest("You must rank at least 3 projects.")
    else:
        if len(project_ids) < total_projects:
            return HttpResponseBadRequest("You must rank all projects.")

    # Get enrollment
    lti_sub = request.session[LTI_SUB_KEY]
    enrollment = get_object_or_404(StudentEnrollment, course=course, lti_sub=lti_sub)

    # Create or update preference
    Preference.objects.update_or_create(
        enrollment=enrollment,
        defaults={"ordered_project_ids": project_ids},
    )

    messages.success(request, "Your preferences have been saved.")
    return redirect("projects:student_view")


@lti_required
def student_result(request: HttpRequest) -> HttpResponse:
    """Student result view — stub; full implementation in US-016."""
    roles = request.session.get(LTI_ROLES_KEY, [])
    if LEARNER_ROLE not in roles:
        return HttpResponseForbidden("Learner role required.")
    context_id = request.session[LTI_CONTEXT_ID_KEY]
    course = Course.objects.get(context_id=context_id)
    return render(request, "projects/student_result.html", {"course": course})
