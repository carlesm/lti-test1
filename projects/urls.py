"""URL patterns for the projects app."""

from django.urls import path

from projects import views

app_name = "projects"

urlpatterns = [
    path("professor/", views.professor_dashboard, name="professor_dashboard"),
    path("student/", views.student_view, name="student_view"),
]
