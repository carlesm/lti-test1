"""Service functions for course phase transitions."""

from datetime import datetime
import hashlib
import random

from django.utils import timezone

from projects.models import Assignment, Course, Preference, StudentEnrollment


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
