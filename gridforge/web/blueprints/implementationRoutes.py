# -*- coding: utf-8 -*-
# gridforge/web/blueprints/implementationRoutes.py
"""
Defines internal implementation-slice routes for GridForge.

The routes let internal developers create implementation slices from approved
developer plans, update slice status, and add blockers while preserving audit
history and server-side role guards.

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
from gridforge.domain.records import ImplementationSlice
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.implementationSliceService import (
    ImplementationSliceService,
    createImplementationSliceErrorPayload,
)
from gridforge.web.auth.roleGuards import getCurrentUserId, roleRequired

IMPLEMENTATION_ROLES = (UserRole.PLATFORM_ADMIN, UserRole.DEVELOPER)


def createImplementationBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates implementation-slice routes.

    Args:
        repositories: Repository bundle used by implementation services.

    Returns:
        A Flask Blueprint containing implementation routes.
    """
    implementation_routes = Blueprint("implementation", __name__)
    implementation_service = ImplementationSliceService(repositories)

    @implementation_routes.get("/developer/projects/<project_id>/slices")
    @roleRequired(*IMPLEMENTATION_ROLES)
    def projectSlices(project_id: str) -> str:
        """
        Renders implementation slices for a project.

        Args:
            project_id: Project id.

        Returns:
            Rendered implementation slices HTML.
        """
        project = repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            abort(404)
            raise RuntimeError("unreachable")
        developer_plan = None
        if project.active_developer_plan_id:
            developer_plan = repositories.developer_plan_repo.getRecord(
                project.active_developer_plan_id
            )
        slices = repositories.implementation_slice_repo.listByProject(project.id)
        qa_items = repositories.qa_validation_repo.listByProject(project.id)
        return cast(
            str,
            render_template(
                "developer/implementation_slices.html",
                developer_plan=developer_plan,
                project=project,
                qa_items=qa_items,
                slices=slices,
            ),
        )

    @implementation_routes.post("/developer/projects/<project_id>/slices")
    @roleRequired(*IMPLEMENTATION_ROLES)
    def createProjectSlices(project_id: str) -> tuple[Response, int]:
        """
        Creates implementation slices from the approved active developer plan.

        Args:
            project_id: Project id.

        Returns:
            JSON response and HTTP status code.
        """
        result = implementation_service.createSlicesFromApprovedPlan(
            project_id,
            actor_user_id=getCurrentUserId(),
        )
        if not result.ok:
            return jsonify(createImplementationSliceErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "projectId": project_id,
                "sliceIds": [implementation_slice.id for implementation_slice in result.slices],
                "qaItemIds": [qa_item.id for qa_item in result.qa_items],
            }
        ), result.status_code

    @implementation_routes.post("/developer/slices/<slice_id>/status")
    @roleRequired(*IMPLEMENTATION_ROLES)
    def updateSliceStatus(slice_id: str) -> tuple[Response, int]:
        """
        Updates an implementation slice status.

        Args:
            slice_id: Implementation slice id.

        Returns:
            JSON response and HTTP status code.
        """
        payload = getRequestPayload()
        result = implementation_service.updateSliceStatus(
            slice_id,
            status_value=str(payload.get("status", "")),
            actor_user_id=getCurrentUserId(),
        )
        if not result.ok or not result.slices:
            return jsonify(createImplementationSliceErrorPayload(result)), result.status_code
        updated_slice = result.slices[0]
        return jsonify(
            {
                "ok": True,
                "sliceId": updated_slice.id,
                "status": updated_slice.status.value,
            }
        ), result.status_code

    @implementation_routes.post("/developer/slices/<slice_id>/blockers")
    @roleRequired(*IMPLEMENTATION_ROLES)
    def addSliceBlocker(slice_id: str) -> tuple[Response, int]:
        """
        Adds a blocker to an implementation slice.

        Args:
            slice_id: Implementation slice id.

        Returns:
            JSON response and HTTP status code.
        """
        payload = getRequestPayload()
        result = implementation_service.addSliceBlocker(
            slice_id,
            blocker_note=str(payload.get("blockerNote", "")),
            actor_user_id=getCurrentUserId(),
        )
        if not result.ok or not result.slices:
            return jsonify(createImplementationSliceErrorPayload(result)), result.status_code
        updated_slice = result.slices[0]
        return jsonify(
            {
                "ok": True,
                "sliceId": updated_slice.id,
                "status": updated_slice.status.value,
                "blockerCount": len(updated_slice.blockers_json),
            }
        ), result.status_code

    return implementation_routes


def getImplementationSliceOr404(
    repositories: AppRepositories,
    slice_id: str,
) -> ImplementationSlice:
    """
    Looks up an implementation slice or aborts with 404.

    Args:
        repositories: Repository bundle.
        slice_id: Implementation slice id.

    Returns:
        Found ImplementationSlice.
    """
    implementation_slice = repositories.implementation_slice_repo.getRecord(slice_id)
    if implementation_slice is None:
        abort(404)
        raise RuntimeError("unreachable")
    return implementation_slice


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
