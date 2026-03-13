"""Service functions for course phase transitions."""

from datetime import datetime
import hashlib
import logging
import random

from django.utils import timezone

from projects.models import Assignment, Course, Preference, StudentEnrollment

logger = logging.getLogger(__name__)


def open_selection(course: Course, deadline: datetime | None = None) -> None:
    """Transition course from setup → open.

    Raises ValueError if the course is not in 'setup' phase.
    """
    if course.phase != Course.PHASE_SETUP:
        raise ValueError(
            f"Cannot open selection: course is in '{course.phase}' phase, expected 'setup'."
        )
    course.phase = Course.PHASE_OPEN
    course.deadline = deadline
    course.save(update_fields=["phase", "deadline"])


def close_selection(course: Course) -> None:
    """Transition course from open → closed.

    Raises ValueError if the course is not in 'open' phase.
    """
    if course.phase != Course.PHASE_OPEN:
        raise ValueError(
            f"Cannot close selection: course is in '{course.phase}' phase, expected 'open'."
        )
    course.phase = Course.PHASE_CLOSED
    course.save(update_fields=["phase"])


def extend_deadline(course: Course, new_deadline: datetime) -> None:
    """Update the deadline for an open course.

    Raises ValueError if the course is not in 'open' phase.
    """
    if course.phase != Course.PHASE_OPEN:
        raise ValueError(
            f"Cannot extend deadline: course is in '{course.phase}' phase, expected 'open'."
        )
    course.deadline = new_deadline
    course.save(update_fields=["deadline"])


def run_assignment(course: Course) -> dict[int, int | None]:
    """Assign projects to students using a greedy algorithm.

    Shuffles enrollments with a seed derived from context_id for reproducibility,
    then assigns each student their highest-ranked available project.
    Students with no preferences get Assignment.project = None.

    Returns dict of {enrollment_id: project_id_or_None}.
    Transitions phase to 'assigned'.
    """
    # Delete all existing Assignment records for this course
    Assignment.objects.filter(enrollment__course=course).delete()

    # Get all enrollments for the course
    enrollments = list(StudentEnrollment.objects.filter(course=course))

    # Deterministic shuffle: seed from context_id hash
    seed = int(hashlib.md5(course.context_id.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    rng.shuffle(enrollments)

    # Build a dict of enrollment -> ordered_project_ids
    preferences: dict[int, list[int]] = {}
    for pref in Preference.objects.filter(enrollment__in=enrollments):
        preferences[pref.enrollment_id] = list(pref.ordered_project_ids)

    # Track which project IDs have been assigned
    assigned_project_ids: set[int] = set()

    result: dict[int, int | None] = {}

    for enrollment in enrollments:
        ranked_ids = preferences.get(enrollment.pk, [])
        assigned_project = None
        for project_id in ranked_ids:
            if project_id not in assigned_project_ids:
                assigned_project_ids.add(project_id)
                assigned_project = project_id
                break
        Assignment.objects.create(
            enrollment=enrollment,
            project_id=assigned_project,
        )
        result[enrollment.pk] = assigned_project

    # Transition phase to 'assigned'
    course.phase = Course.PHASE_ASSIGNED
    course.save(update_fields=["phase"])

    return result


def publish_results(course: Course) -> None:
    """Transition course from assigned → published and send AGS grade passback.

    For each student with a non-null Assignment, sends a score of 1.0/1.0
    to the LMS via AGS. Students with no assignment receive no AGS call.
    If lineitem_url is null, logs a warning and skips all AGS calls.

    Raises ValueError if the course is not in 'assigned' phase.
    """
    if course.phase != Course.PHASE_ASSIGNED:
        raise ValueError(
            f"Cannot publish results: course is in '{course.phase}' phase, expected 'assigned'."
        )

    assignments = list(
        Assignment.objects.filter(enrollment__course=course)
        .select_related("enrollment")
    )

    if course.lineitem_url:
        _send_ags_grades(course, assignments)
    else:
        logger.warning(
            "Course %s has no lineitem_url; skipping AGS grade passback.", course.context_id
        )

    course.phase = Course.PHASE_PUBLISHED
    course.save(update_fields=["phase"])


def _send_ags_grades(course: Course, assignments: list[Assignment]) -> None:
    """Send AGS score of 1.0 for each assigned student."""
    try:
        from lti_tool.models import LtiContext
        from pylti1p3.service_connector import ServiceConnector
        from pylti1p3.assignments_grades import AssignmentsGradesService
        from pylti1p3.grade import Grade
    except ImportError as exc:
        logger.warning("AGS dependencies unavailable (%s); skipping grade passback.", exc)
        return

    try:
        lti_context = LtiContext.objects.filter(id_on_platform=course.context_id).first()
        if lti_context is None:
            logger.warning(
                "No LtiContext found for context_id=%s; skipping AGS calls.", course.context_id
            )
            return

        registration_obj = lti_context.deployment.registration.to_registration()
        connector = ServiceConnector(registration_obj)
        ags_endpoint = {
            "scope": ["https://purl.imsglobal.org/spec/lti-ags/scope/score"],
            "lineitem": course.lineitem_url,
        }
        ags = AssignmentsGradesService(connector, ags_endpoint)
    except Exception as exc:
        logger.warning("Failed to initialise AGS service: %s; skipping grade passback.", exc)
        return

    timestamp = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    for assignment in assignments:
        if assignment.project_id is None:
            continue  # Unassigned students get no AGS call
        try:
            grade = Grade()
            grade.set_score_given(1.0)
            grade.set_score_maximum(1.0)
            grade.set_user_id(assignment.enrollment.lti_sub)
            grade.set_grading_progress("FullyGraded")
            grade.set_activity_progress("Completed")
            grade.set_timestamp(timestamp)
            ags.put_grade(grade)
        except Exception as exc:
            logger.warning(
                "AGS grade passback failed for enrollment %s: %s",
                assignment.enrollment_id,
                exc,
            )


def auto_close_if_deadline_passed(course: Course) -> bool:
    """Close selection if deadline has passed. Returns True if closed."""
    if (
        course.phase == Course.PHASE_OPEN
        and course.deadline is not None
        and timezone.now() >= course.deadline
    ):
        course.phase = Course.PHASE_CLOSED
        course.save(update_fields=["phase"])
        return True
    return False
