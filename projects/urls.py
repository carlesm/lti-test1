"""URL patterns for the projects app."""

from django.urls import path

from projects import views

app_name = "projects"

urlpatterns = [
    path("professor/", views.professor_dashboard, name="professor_dashboard"),
    path("professor/projects/create/", views.project_create, name="project_create"),
    path("professor/projects/<int:project_id>/edit/", views.project_edit, name="project_edit"),
    path("professor/projects/<int:project_id>/delete/", views.project_delete, name="project_delete"),
    path("student/", views.student_view, name="student_view"),
]
