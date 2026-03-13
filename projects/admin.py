"""Admin configuration for the projects app."""

from django.contrib import admin

from projects.models import Assignment, Course, Preference, Project, StudentEnrollment

admin.site.register(Course)
admin.site.register(Project)
admin.site.register(StudentEnrollment)
admin.site.register(Preference)
admin.site.register(Assignment)
