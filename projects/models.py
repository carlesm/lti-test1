"""Models for the projects app."""

from django.db import models


class Course(models.Model):
    PHASE_SETUP = "setup"
    PHASE_OPEN = "open"
    PHASE_CLOSED = "closed"
    PHASE_ASSIGNED = "assigned"
    PHASE_PUBLISHED = "published"

    PHASE_CHOICES = [
        (PHASE_SETUP, "Setup"),
        (PHASE_OPEN, "Open"),
        (PHASE_CLOSED, "Closed"),
        (PHASE_ASSIGNED, "Assigned"),
        (PHASE_PUBLISHED, "Published"),
    ]

    context_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default=PHASE_SETUP)
    deadline = models.DateTimeField(null=True, blank=True)
    lineitem_url = models.URLField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.title} ({self.context_id})"


class Project(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=255)
    description = models.TextField()
    tags = models.TextField(blank=True, default="")
    is_deleted = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class StudentEnrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    lti_sub = models.CharField(max_length=255)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("course", "lti_sub")

    def __str__(self) -> str:
        return f"{self.name} in {self.course}"


class Preference(models.Model):
    enrollment = models.OneToOneField(
        StudentEnrollment, on_delete=models.CASCADE, related_name="preference"
    )
    ordered_project_ids = models.JSONField(default=list)

    def __str__(self) -> str:
        return f"Preferences for {self.enrollment}"


class Assignment(models.Model):
    enrollment = models.OneToOneField(
        StudentEnrollment, on_delete=models.CASCADE, related_name="assignment"
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="assignments"
    )

    def __str__(self) -> str:
        project_title = self.project.title if self.project else "Unassigned"
        return f"{self.enrollment} → {project_title}"
