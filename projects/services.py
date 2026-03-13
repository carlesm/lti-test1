"""Service functions for course phase transitions."""

from datetime import datetime

from django.utils import timezone

from projects.models import Course


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
