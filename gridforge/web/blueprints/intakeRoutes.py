# -*- coding: utf-8 -*-
# gridforge/web/blueprints/intakeRoutes.py
"""
Defines guided intake API routes for GridForge Command Cloud.

The intake routes accept public workflow submissions and delegate validation,
record creation, missing-detail tracking, and audit logging to the service layer.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Any, Mapping, cast

# 2) Third-party imports (alphabetized)
from flask import Blueprint, Response, jsonify, request

# 3) Application-specific imports (alphabetized)
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.intakeService import IntakeService


def createIntakeBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates guided intake API routes.

    Args:
        repositories: Repository bundle used by intake services.

    Returns:
        A Flask Blueprint containing intake routes.
    """
    intake_routes = Blueprint("intake", __name__)
    intake_service = IntakeService(repositories)

    @intake_routes.post("/api/intake")
    def createIntake() -> tuple[Response, int]:
        """
        Creates a customer workflow project from a public intake submission.

        Returns:
            JSON response and HTTP status code.
        """
        result = intake_service.createPublicIntake(getRequestPayload())
        if not result.ok:
            return jsonify({"ok": False, "errors": dict(result.errors)}), result.status_code
        if result.organization is None or result.project is None or result.intake is None:
            return jsonify({"ok": False, "errors": {"intake": "Intake was not saved."}}), 500
        missing_detail_result = result.missing_detail_result
        return jsonify(
            {
                "ok": True,
                "auditEventId": result.audit_event.id if result.audit_event is not None else None,
                "coverageCount": missing_detail_result.coverage_count
                if missing_detail_result is not None
                else 0,
                "coverageTotal": missing_detail_result.coverage_total
                if missing_detail_result is not None
                else 0,
                "completionPercent": missing_detail_result.completion_percent
                if missing_detail_result is not None
                else 0,
                "intakeId": result.intake.id,
                "missingDetailCategories": list(result.intake.missing_detail_categories),
                "organizationId": result.organization.id,
                "projectId": result.project.id,
                "riskFlags": list(result.intake.risk_flags),
                "status": result.project.status.value,
            }
        ), result.status_code

    return intake_routes


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
