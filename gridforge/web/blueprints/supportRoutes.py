# -*- coding: utf-8 -*-
# gridforge/web/blueprints/supportRoutes.py
"""
Defines support request routes for GridForge.

The routes let support managers view handoff/support projects, create support or
enhancement requests after handoff, and update support request statuses.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Any, Mapping, cast

# 2) Third-party imports (alphabetized)
from flask import Blueprint, Response, abort, jsonify, render_template, request

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import UserRole
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.supportRequestService import (
    SupportRequestService,
    createSupportRequestErrorPayload,
)
from gridforge.web.auth.roleGuards import getCurrentUserId, roleRequired

SUPPORT_ROLES = (UserRole.PLATFORM_ADMIN, UserRole.SUPPORT_MANAGER)


def createSupportBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates support request routes.

    Args:
        repositories: Repository bundle used by support services.

    Returns:
        A Flask Blueprint containing support routes.
    """
    support_routes = Blueprint("support", __name__)
    support_request_service = SupportRequestService(repositories)

    @support_routes.get("/support/projects/<project_id>")
    @roleRequired(*SUPPORT_ROLES)
    def supportProject(project_id: str) -> str:
        """
        Renders support requests for a project.

        Args:
            project_id: Project id.

        Returns:
            Rendered support project HTML.
        """
        project = repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            abort(404)
            raise RuntimeError("unreachable")
        support_requests = repositories.support_request_repo.listByProject(project.id)
        audit_events = repositories.audit_event_repo.listByProject(project.id)
        return cast(
            str,
            render_template(
                "support/support_project.html",
                audit_events=audit_events,
                project=project,
                support_requests=support_requests,
            ),
        )

    @support_routes.post("/support/projects/<project_id>/requests")
    @roleRequired(*SUPPORT_ROLES)
    def createSupportRequest(project_id: str) -> tuple[Response, int]:
        """
        Creates a support request for a support-ready project.

        Args:
            project_id: Project id.

        Returns:
            JSON response and HTTP status code.
        """
        payload = getRequestPayload()
        result = support_request_service.createSupportRequest(
            project_id,
            title=str(payload.get("title", "")),
            customer_description=str(payload.get("customerDescription", "")),
            actor_user_id=getCurrentUserId(),
            request_type=str(payload.get("requestType", "support")),
            priority=str(payload.get("priority", "medium")),
        )
        if not result.ok or result.support_request is None:
            return jsonify(createSupportRequestErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "supportRequestId": result.support_request.id,
                "status": result.support_request.status.value,
            }
        ), result.status_code

    @support_routes.post("/support/requests/<request_id>/status")
    @roleRequired(*SUPPORT_ROLES)
    def updateSupportRequestStatus(request_id: str) -> tuple[Response, int]:
        """
        Updates support request status.

        Args:
            request_id: Support request id.

        Returns:
            JSON response and HTTP status code.
        """
        payload = getRequestPayload()
        result = support_request_service.updateSupportRequestStatus(
            request_id,
            status_value=str(payload.get("status", "")),
            actor_user_id=getCurrentUserId(),
            internal_notes=str(payload.get("internalNotes", "")),
            customer_visible_response=str(payload.get("customerVisibleResponse", "")),
        )
        if not result.ok or result.support_request is None:
            return jsonify(createSupportRequestErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "supportRequestId": result.support_request.id,
                "status": result.support_request.status.value,
            }
        ), result.status_code

    return support_routes


def getRequestPayload() -> Mapping[str, Any]:
    """
    Reads JSON or form-encoded request payloads.

    Returns:
        Request payload mapping.
    """
    json_payload = request.get_json(silent=True)
    if isinstance(json_payload, Mapping):
        return json_payload
    return cast(Mapping[str, Any], request.form.to_dict(flat=True))
