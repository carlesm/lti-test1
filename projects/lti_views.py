"""LTI launch views for the projects app."""

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect

from lti_tool.lti_core.constants import ContextRole
from lti_tool.models import LtiLaunch
from lti_tool.views import LtiLaunchBaseView

from projects.models import Course, StudentEnrollment

# Session keys for LTI claims
LTI_SUB_KEY = "lti_sub"
LTI_NAME_KEY = "lti_name"
LTI_ROLES_KEY = "lti_roles"
LTI_CONTEXT_ID_KEY = "lti_context_id"
LTI_CONTEXT_TITLE_KEY = "lti_context_title"
LTI_LINEITEM_URL_KEY = "lti_lineitem_url"

INSTRUCTOR_ROLE = ContextRole.INSTRUCTOR.value
LEARNER_ROLE = ContextRole.LEARNER.value


class ProjectLtiLaunchView(LtiLaunchBaseView):
    """Handles LTI 1.3 resource link launches with role detection and session setup."""

    def handle_resource_launch(
        self, request: HttpRequest, lti_launch: LtiLaunch
    ) -> HttpResponse:
        # Extract LTI claims
        sub: str = lti_launch.get_claim("sub") or ""
        name: str = lti_launch.get_claim("name") or ""
        roles: list = lti_launch.roles_claim or []
        context_claim: dict = lti_launch.context_claim or {}
        context_id: str = context_claim.get("id", "")
        context_title: str = context_claim.get("title", "")

        ags_claim: dict = lti_launch.ags_claim or {}
        lineitem_url: str | None = ags_claim.get("lineitem") or None

        # Store LTI claims in Django session
        request.session[LTI_SUB_KEY] = sub
        request.session[LTI_NAME_KEY] = name
        request.session[LTI_ROLES_KEY] = roles
        request.session[LTI_CONTEXT_ID_KEY] = context_id
        request.session[LTI_CONTEXT_TITLE_KEY] = context_title
        request.session[LTI_LINEITEM_URL_KEY] = lineitem_url

        # Create or update Course record
        Course.objects.update_or_create(
            context_id=context_id,
            defaults={"title": context_title, "lineitem_url": lineitem_url},
        )

        is_instructor = INSTRUCTOR_ROLE in roles
        is_learner = LEARNER_ROLE in roles

        # Auto-create StudentEnrollment for learners
        if is_learner:
            course = Course.objects.get(context_id=context_id)
            StudentEnrollment.objects.update_or_create(
                course=course,
                lti_sub=sub,
                defaults={"name": name},
            )

        # Redirect based on role
        if is_instructor:
            return redirect("projects:professor_dashboard")
        if is_learner:
            return redirect("projects:student_view")

        return HttpResponseForbidden("Unrecognized LTI role.")
