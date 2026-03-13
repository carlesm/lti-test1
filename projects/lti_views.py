"""LTI launch views for the projects app."""

from django.http import HttpRequest, HttpResponse

from lti_tool.models import LtiLaunch
from lti_tool.views import LtiLaunchBaseView


class ProjectLtiLaunchView(LtiLaunchBaseView):
    """Handles LTI 1.3 resource link launches.

    Role detection and session setup are implemented in US-004.
    """

    def handle_resource_launch(
        self, request: HttpRequest, lti_launch: LtiLaunch
    ) -> HttpResponse:
        # Full implementation in US-004; return a placeholder for now.
        return HttpResponse("LTI launch received. Full handler coming in US-004.")
