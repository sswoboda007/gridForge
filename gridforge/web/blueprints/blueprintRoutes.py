# -*- coding: utf-8 -*-
# gridforge/web/blueprints/blueprintRoutes.py
"""
Defines customer-blueprint generation and review routes for GridForge.

The routes generate validated customer-facing blueprint drafts with deterministic
fake AI by default, require internal human review before customer access, and keep
raw AI metadata and validation errors internal-only.

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
from gridforge.domain.enums import BlueprintStatus, UserRole
from gridforge.domain.records import CustomerBlueprint
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.blueprintAiService import BlueprintAiService
from gridforge.services.blueprintReviewService import (
    BlueprintReviewService,
    createReviewErrorPayload,
)
from gridforge.web.auth.roleGuards import (
    CUSTOMER_ROLES,
    INTERNAL_ROLES,
    PROJECT_REVIEW_ROLES,
    canAccessProject,
    getCurrentUserId,
    hasAnyRole,
    roleRequired,
)

CUSTOMER_VISIBLE_BLUEPRINT_STATUSES = (
    BlueprintStatus.READY_FOR_CUSTOMER_REVIEW,
    BlueprintStatus.APPROVED,
)


def createBlueprintBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates customer-blueprint generation and review routes.

    Args:
        repositories: Repository bundle used by blueprint services.

    Returns:
        A Flask Blueprint containing blueprint routes.
    """
    blueprint_routes = Blueprint("blueprint", __name__)
    blueprint_ai_service = BlueprintAiService(repositories)
    blueprint_review_service = BlueprintReviewService(repositories)

    @blueprint_routes.post("/admin/projects/<project_id>/generate-blueprint")
    @roleRequired(UserRole.PLATFORM_ADMIN, UserRole.WORKFLOW_ANALYST)
    def generateBlueprint(project_id: str) -> tuple[Response, int]:
        """
        Generates a validated customer blueprint draft for internal review.

        Args:
            project_id: Workflow project id.

        Returns:
            JSON response and HTTP status code.
        """
        result = blueprint_ai_service.generateBlueprintForProject(
            project_id,
            actor_user_id=getCurrentUserId(),
        )
        if not result.ok or result.blueprint is None:
            return jsonify({"ok": False, "errors": list(result.errors)}), result.status_code
        return jsonify(
            {
                "ok": True,
                "blueprintId": result.blueprint.id,
                "projectId": result.blueprint.project_id,
                "status": result.blueprint.status.value,
            }
        ), result.status_code

    @blueprint_routes.get("/admin/review-queue")
    @roleRequired(*PROJECT_REVIEW_ROLES)
    def reviewQueue() -> str:
        """
        Renders the internal blueprint review queue.

        Returns:
            Rendered review queue HTML.
        """
        blueprints = tuple(
            blueprint
            for blueprint in repositories.blueprint_repo.listRecords()
            if blueprint.status == BlueprintStatus.NEEDS_INTERNAL_REVIEW
        )
        projects = {
            project.id: project for project in repositories.workflow_project_repo.listRecords()
        }
        organizations = {
            organization.id: organization
            for organization in repositories.organization_repo.listRecords()
        }
        return cast(
            str,
            render_template(
                "admin/review_queue.html",
                blueprints=blueprints,
                organizations=organizations,
                projects=projects,
            ),
        )

    @blueprint_routes.get("/admin/blueprints/<blueprint_id>")
    @roleRequired(*PROJECT_REVIEW_ROLES)
    def adminBlueprintDetail(blueprint_id: str) -> str:
        """
        Renders internal blueprint review details.

        Args:
            blueprint_id: Blueprint id.

        Returns:
            Rendered internal blueprint detail HTML.
        """
        blueprint = getBlueprintOr404(repositories, blueprint_id)
        project = repositories.workflow_project_repo.getRecord(blueprint.project_id)
        ai_logs = repositories.ai_request_log_repo.listByProject(blueprint.project_id)
        audit_events = repositories.audit_event_repo.listByProject(blueprint.project_id)
        return cast(
            str,
            render_template(
                "admin/blueprint_detail.html",
                ai_logs=ai_logs,
                audit_events=audit_events,
                blueprint=blueprint,
                project=project,
            ),
        )

    @blueprint_routes.post("/admin/blueprints/<blueprint_id>/review")
    @roleRequired(UserRole.PLATFORM_ADMIN, UserRole.WORKFLOW_ANALYST)
    def reviewBlueprint(blueprint_id: str) -> tuple[Response, int]:
        """
        Marks an internally reviewed blueprint ready for customer review.

        Args:
            blueprint_id: Blueprint id.

        Returns:
            JSON response and HTTP status code.
        """
        payload = getRequestPayload()
        action = str(payload.get("action", "ready_for_customer_review")).strip()
        if action != "ready_for_customer_review":
            return jsonify({"ok": False, "errors": ["Unsupported review action."]}), 400
        result = blueprint_review_service.markReadyForCustomerReview(
            blueprint_id,
            reviewer_user_id=getCurrentUserId(),
            reviewer_notes=str(payload.get("reviewerNotes", "")),
        )
        if not result.ok or result.blueprint is None:
            return jsonify(createReviewErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "blueprintId": result.blueprint.id,
                "status": result.blueprint.status.value,
            }
        ), result.status_code

    @blueprint_routes.get("/customer/blueprints/<blueprint_id>")
    @roleRequired(*CUSTOMER_ROLES, *PROJECT_REVIEW_ROLES)
    def customerBlueprintDetail(blueprint_id: str) -> str:
        """
        Renders a customer-safe blueprint detail page after internal review.

        Args:
            blueprint_id: Blueprint id.

        Returns:
            Rendered customer-safe blueprint HTML.
        """
        blueprint = getBlueprintOr404(repositories, blueprint_id)
        requireCustomerBlueprintVisibility(blueprint)
        project = repositories.workflow_project_repo.getRecord(blueprint.project_id)
        customer_safe_blueprint = blueprint_review_service.createCustomerSafeView(blueprint)
        return cast(
            str,
            render_template(
                "customer/blueprint_detail.html",
                blueprint=customer_safe_blueprint,
                project=project,
            ),
        )

    @blueprint_routes.post("/customer/blueprints/<blueprint_id>/approve")
    @roleRequired(UserRole.CLIENT_STAKEHOLDER, UserRole.PLATFORM_ADMIN)
    def approveCustomerBlueprint(blueprint_id: str) -> tuple[Response, int]:
        """
        Approves a customer blueprint and updates project state.

        Args:
            blueprint_id: Blueprint id.

        Returns:
            JSON response and HTTP status code.
        """
        blueprint = getBlueprintOr404(repositories, blueprint_id)
        requireCustomerBlueprintVisibility(blueprint)
        result = blueprint_review_service.approveBlueprint(
            blueprint_id,
            approver_user_id=getCurrentUserId(),
        )
        if not result.ok or result.blueprint is None:
            return jsonify(createReviewErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "blueprintId": result.blueprint.id,
                "status": result.blueprint.status.value,
            }
        ), result.status_code

    @blueprint_routes.post("/customer/blueprints/<blueprint_id>/changes-requested")
    @roleRequired(*CUSTOMER_ROLES, *PROJECT_REVIEW_ROLES)
    def requestCustomerBlueprintChanges(blueprint_id: str) -> tuple[Response, int]:
        """
        Records customer-requested blueprint changes.

        Args:
            blueprint_id: Blueprint id.

        Returns:
            JSON response and HTTP status code.
        """
        blueprint = getBlueprintOr404(repositories, blueprint_id)
        requireCustomerBlueprintVisibility(blueprint)
        payload = getRequestPayload()
        result = blueprint_review_service.requestBlueprintChanges(
            blueprint_id,
            requester_user_id=getCurrentUserId(),
            change_note=str(payload.get("changeNote", "")),
        )
        if not result.ok or result.blueprint is None:
            return jsonify(createReviewErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "blueprintId": result.blueprint.id,
                "status": result.blueprint.status.value,
            }
        ), result.status_code

    return blueprint_routes


def getBlueprintOr404(repositories: AppRepositories, blueprint_id: str) -> CustomerBlueprint:
    """
    Looks up a blueprint or aborts with 404.

    Args:
        repositories: Repository bundle.
        blueprint_id: Blueprint id.

    Returns:
        Found CustomerBlueprint.
    """
    blueprint = repositories.blueprint_repo.getRecord(blueprint_id)
    if blueprint is None:
        abort(404)
        raise RuntimeError("unreachable")
    return blueprint


def requireCustomerBlueprintVisibility(blueprint: CustomerBlueprint) -> None:
    """
    Enforces internal-review gate and customer project scope.

    Args:
        blueprint: Blueprint being displayed or changed.

    Returns:
        None.
    """
    if blueprint.status not in CUSTOMER_VISIBLE_BLUEPRINT_STATUSES:
        abort(403)
    if hasAnyRole(INTERNAL_ROLES):
        return
    if not canAccessProject(blueprint.project_id):
        abort(403)


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
