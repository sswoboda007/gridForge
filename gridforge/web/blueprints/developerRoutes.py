# -*- coding: utf-8 -*-
# gridforge/web/blueprints/developerRoutes.py
"""
Defines internal developer-plan routes for GridForge.

The routes allow approved blueprints to produce developer-only implementation
plans, enforce internal role guards, and keep technical plans inaccessible to
customer roles.

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
from gridforge.domain.records import DeveloperPlan
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.developerPlanService import (
    DeveloperPlanService,
    createDeveloperPlanErrorPayload,
)
from gridforge.web.auth.roleGuards import getCurrentUserId, roleRequired

DEVELOPER_PLAN_VIEW_ROLES = (
    UserRole.PLATFORM_ADMIN,
    UserRole.DEVELOPER,
    UserRole.QA_REVIEWER,
)
DEVELOPER_PLAN_REVIEW_ROLES = (UserRole.PLATFORM_ADMIN, UserRole.DEVELOPER)


def createDeveloperBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates internal developer-plan routes.

    Args:
        repositories: Repository bundle used by developer-plan services.

    Returns:
        A Flask Blueprint containing developer-plan routes.
    """
    developer_routes = Blueprint("developer", __name__)
    developer_plan_service = DeveloperPlanService(repositories)

    @developer_routes.post("/admin/blueprints/<blueprint_id>/generate-developer-plan")
    @roleRequired(*DEVELOPER_PLAN_REVIEW_ROLES)
    def generateDeveloperPlan(blueprint_id: str) -> tuple[Response, int]:
        """
        Generates an internal developer plan from an approved blueprint.

        Args:
            blueprint_id: Approved customer blueprint id.

        Returns:
            JSON response and HTTP status code.
        """
        result = developer_plan_service.generateDeveloperPlanForBlueprint(
            blueprint_id,
            actor_user_id=getCurrentUserId(),
        )
        if not result.ok or result.developer_plan is None:
            return jsonify(createDeveloperPlanErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "developerPlanId": result.developer_plan.id,
                "blueprintId": result.developer_plan.blueprint_id,
                "projectId": result.developer_plan.project_id,
                "status": result.developer_plan.status.value,
            }
        ), result.status_code

    @developer_routes.get("/developer/plans/<developer_plan_id>")
    @roleRequired(*DEVELOPER_PLAN_VIEW_ROLES)
    def developerPlanDetail(developer_plan_id: str) -> str:
        """
        Renders an internal developer-only plan detail page.

        Args:
            developer_plan_id: Developer plan id.

        Returns:
            Rendered developer-plan detail HTML.
        """
        developer_plan = getDeveloperPlanOr404(repositories, developer_plan_id)
        blueprint = repositories.blueprint_repo.getRecord(developer_plan.blueprint_id)
        project = repositories.workflow_project_repo.getRecord(developer_plan.project_id)
        audit_events = repositories.audit_event_repo.listByProject(developer_plan.project_id)
        return cast(
            str,
            render_template(
                "developer/plan_detail.html",
                audit_events=audit_events,
                blueprint=blueprint,
                developer_plan=developer_plan,
                project=project,
            ),
        )

    @developer_routes.post("/developer/plans/<developer_plan_id>/review")
    @roleRequired(*DEVELOPER_PLAN_REVIEW_ROLES)
    def reviewDeveloperPlan(developer_plan_id: str) -> tuple[Response, int]:
        """
        Approves or blocks a developer plan.

        Args:
            developer_plan_id: Developer plan id.

        Returns:
            JSON response and HTTP status code.
        """
        payload = getRequestPayload()
        result = developer_plan_service.reviewDeveloperPlan(
            developer_plan_id,
            action=str(payload.get("action", "")),
            reviewer_user_id=getCurrentUserId(),
            blocker_reason=str(payload.get("blockerReason", "")),
        )
        if not result.ok or result.developer_plan is None:
            return jsonify(createDeveloperPlanErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "developerPlanId": result.developer_plan.id,
                "status": result.developer_plan.status.value,
            }
        ), result.status_code

    return developer_routes


def getDeveloperPlanOr404(
    repositories: AppRepositories,
    developer_plan_id: str,
) -> DeveloperPlan:
    """
    Looks up a developer plan or aborts with 404.

    Args:
        repositories: Repository bundle.
        developer_plan_id: Developer plan id.

    Returns:
        Found DeveloperPlan.
    """
    developer_plan = repositories.developer_plan_repo.getRecord(developer_plan_id)
    if developer_plan is None:
        abort(404)
        raise RuntimeError("unreachable")
    return developer_plan


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
