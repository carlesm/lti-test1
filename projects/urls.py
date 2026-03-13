"""URL patterns for the projects app."""

from django.urls import path

from projects import views

app_name = "projects"

urlpatterns = [
    path("professor/", views.professor_dashboard, name="professor_dashboard"),
    path("professor/projects/create/", views.project_create, name="project_create"),
    path("professor/projects/<int:project_id>/edit/", views.project_edit, name="project_edit"),
    path("professor/projects/<int:project_id>/delete/", views.project_delete, name="project_delete"),
    path("professor/open-selection/", views.open_selection_view, name="open_selection"),
    path("professor/close-selection/", views.close_selection_view, name="close_selection"),
    path("professor/extend-deadline/", views.extend_deadline_view, name="extend_deadline"),
    path("professor/run-assignment/", views.run_assignment_view, name="run_assignment"),
    path("professor/assignments/", views.assignment_results_view, name="assignment_results"),
    path("professor/publish/", views.publish_results_view, name="publish_results"),
    path("student/", views.student_view, name="student_view"),
    path("student/result/", views.student_result, name="student_result"),
]
