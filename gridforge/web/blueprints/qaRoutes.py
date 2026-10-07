# -*- coding: utf-8 -*-
# gridforge/web/blueprints/qaRoutes.py
"""
Defines QA validation routes for GridForge.

The routes allow QA reviewers and platform admins to view project QA state, add QA
items, and update QA results while the services enforce lifecycle side effects.

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
from gridforge.domain.records import QaValidationItem
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.qaValidationService import (
    QaValidationService,
    createQaValidationErrorPayload,
)
from gridforge.web.auth.roleGuards import getCurrentUserId, roleRequired

QA_ROLES = (UserRole.PLATFORM_ADMIN, UserRole.QA_REVIEWER)


def createQaBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates QA validation routes.

    Args:
        repositories: Repository bundle used by QA services.

    Returns:
        A Flask Blueprint containing QA routes.
    """
    qa_routes = Blueprint("qa", __name__)
    qa_validation_service = QaValidationService(repositories)

    @qa_routes.get("/qa/projects/<project_id>")
    @roleRequired(*QA_ROLES)
    def qaProject(project_id: str) -> str:
        """
        Renders QA validation state for a project.

        Args:
            project_id: Project id.

        Returns:
            Rendered QA project HTML.
        """
        project = repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            abort(404)
            raise RuntimeError("unreachable")
        slices = repositories.implementation_slice_repo.listByProject(project.id)
        qa_items = repositories.qa_validation_repo.listByProject(project.id)
        return cast(
            str,
            render_template(
                "qa/qa_project.html",
                project=project,
                qa_items=qa_items,
                slices=slices,
            ),
        )

    @qa_routes.post("/qa/projects/<project_id>/items")
    @roleRequired(*QA_ROLES)
    def createQaItem(project_id: str) -> tuple[Response, int]:
        """
        Creates a manual QA validation item.

        Args:
            project_id: Project id.

        Returns:
            JSON response and HTTP status code.
        """
        payload = getRequestPayload()
        result = qa_validation_service.createQaItem(
            project_id,
            title=str(payload.get("title", "")),
            actor_user_id=getCurrentUserId(),
            implementation_slice_id=optionalString(payload.get("sliceId")),
            acceptance_criterion=str(payload.get("acceptanceCriterion", "")),
            expected_behavior=str(payload.get("expectedBehavior", "")),
            severity=str(payload.get("severity", "medium")),
        )
        if not result.ok or result.qa_item is None:
            return jsonify(createQaValidationErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "qaItemId": result.qa_item.id,
                "status": result.qa_item.status.value,
            }
        ), result.status_code

    @qa_routes.post("/qa/items/<qa_item_id>/status")
    @roleRequired(*QA_ROLES)
    def updateQaItemStatus(qa_item_id: str) -> tuple[Response, int]:
        """
        Updates a QA validation item status.

        Args:
            qa_item_id: QA item id.

        Returns:
            JSON response and HTTP status code.
        """
        payload = getRequestPayload()
        result = qa_validation_service.updateQaItemStatus(
            qa_item_id,
            status_value=str(payload.get("status", "")),
            actor_user_id=getCurrentUserId(),
            actual_behavior=str(payload.get("actualBehavior", "")),
            evidence_link=str(payload.get("evidenceLink", "")),
            resolution_notes=str(payload.get("resolutionNotes", "")),
        )
        if not result.ok or result.qa_item is None:
            return jsonify(createQaValidationErrorPayload(result)), result.status_code
        return jsonify(
            {
                "ok": True,
                "qaItemId": result.qa_item.id,
                "status": result.qa_item.status.value,
            }
        ), result.status_code

    return qa_routes


def getQaItemOr404(repositories: AppRepositories, qa_item_id: str) -> QaValidationItem:
    """
    Looks up a QA item or aborts with 404.

    Args:
        repositories: Repository bundle.
        qa_item_id: QA item id.

    Returns:
        Found QaValidationItem.
    """
    qa_item = repositories.qa_validation_repo.getRecord(qa_item_id)
    if qa_item is None:
        abort(404)
        raise RuntimeError("unreachable")
    return qa_item


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


def optionalString(value: object) -> str | None:
    """
    Normalizes optional string payload values.

    Args:
        value: Raw payload value.

    Returns:
        Stripped string or None.
    """
    if value is None:
        return None
    normalized_value = str(value).strip()
    return normalized_value or None
