"""URL configuration for lti_project_selection project."""

from django.contrib import admin
from django.urls import include, path

from lti_tool.views import OIDCLoginInitView, jwks
from projects.lti_views import ProjectLtiLaunchView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("projects/", include("projects.urls")),
    # LTI 1.3 endpoints
    path("lti/login/", OIDCLoginInitView.as_view(), name="lti-login"),
    path(
        "lti/login/<uuid:registration_uuid>/",
        OIDCLoginInitView.as_view(),
        name="lti-login-registration",
    ),
    path("lti/launch/", ProjectLtiLaunchView.as_view(), name="lti-launch"),
    path(".well-known/jwks.json", jwks, name="lti-jwks"),
]
