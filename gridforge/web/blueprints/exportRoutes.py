# -*- coding: utf-8 -*-
# gridforge/web/blueprints/exportRoutes.py
"""
Defines CSV export routes for GridForge.

The routes expose customer-safe and internal CSV downloads with server-side role
checks, project scoping, and audit/export records for every download.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)
from flask import Blueprint, Response, jsonify

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import UserRole
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.exportService import ExportResult, ExportService, createExportErrorPayload
from gridforge.web.auth.roleGuards import (
    CUSTOMER_ROLES,
    INTERNAL_ROLES,
    getCurrentUserId,
    getCurrentUserRoles,
    requireProjectScope,
    roleRequired,
)

CUSTOMER_SAFE_EXPORT_ROLES = INTERNAL_ROLES + CUSTOMER_ROLES
INTERNAL_EXPORT_ROLES = INTERNAL_ROLES


def createExportBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates CSV export routes.

    Args:
        repositories: Repository bundle used by export services.

    Returns:
        A Flask Blueprint containing export routes.
    """
    export_routes = Blueprint("export", __name__)
    export_service = ExportService(repositories)

    @export_routes.get("/exports/project/<project_id>/customer-summary.csv")
    @roleRequired(*CUSTOMER_SAFE_EXPORT_ROLES)
    def customerSummary(project_id: str) -> Response | tuple[Response, int]:
        """
        Downloads a customer-safe project summary export.

        Args:
            project_id: Project id.

        Returns:
            CSV response or JSON error.
        """
        requireProjectScope(project_id)
        result = export_service.buildProjectExport(
            project_id,
            export_type="customer_summary",
            actor_user_id=getCurrentUserId(),
            actor_roles=getCurrentUserRoles(),
        )
        return createExportResponse(result)

    @export_routes.get("/exports/project/<project_id>/blueprint-summary.csv")
    @roleRequired(*CUSTOMER_SAFE_EXPORT_ROLES)
    def blueprintSummary(project_id: str) -> Response | tuple[Response, int]:
        """
        Downloads a customer-safe blueprint summary export.

        Args:
            project_id: Project id.

        Returns:
            CSV response or JSON error.
        """
        requireProjectScope(project_id)
        result = export_service.buildProjectExport(
            project_id,
            export_type="blueprint_summary",
            actor_user_id=getCurrentUserId(),
            actor_roles=getCurrentUserRoles(),
        )
        return createExportResponse(result)

    @export_routes.get("/exports/project/<project_id>/developer-plan-internal.csv")
    @roleRequired(*INTERNAL_EXPORT_ROLES)
    def developerPlanInternal(project_id: str) -> Response | tuple[Response, int]:
        """
        Downloads an internal developer-plan export.

        Args:
            project_id: Project id.

        Returns:
            CSV response or JSON error.
        """
        result = export_service.buildProjectExport(
            project_id,
            export_type="developer_plan_internal",
            actor_user_id=getCurrentUserId(),
            actor_roles=getCurrentUserRoles(),
        )
        return createExportResponse(result)

    @export_routes.get("/exports/project/<project_id>/qa-handoff.csv")
    @roleRequired(*INTERNAL_EXPORT_ROLES)
    def qaHandoff(project_id: str) -> Response | tuple[Response, int]:
        """
        Downloads an internal QA handoff export.

        Args:
            project_id: Project id.

        Returns:
            CSV response or JSON error.
        """
        result = export_service.buildProjectExport(
            project_id,
            export_type="qa_handoff",
            actor_user_id=getCurrentUserId(),
            actor_roles=getCurrentUserRoles(),
        )
        return createExportResponse(result)

    @export_routes.get("/exports/audit.csv")
    @roleRequired(UserRole.PLATFORM_ADMIN)
    def auditExport() -> Response | tuple[Response, int]:
        """
        Downloads a platform audit CSV export.

        Returns:
            CSV response or JSON error.
        """
        result = export_service.buildAuditExport(
            actor_user_id=getCurrentUserId(),
            actor_roles=getCurrentUserRoles(),
        )
        return createExportResponse(result)

    return export_routes


def createExportResponse(result: ExportResult) -> Response | tuple[Response, int]:
    """
    Converts an export result into an HTTP response.

    Args:
        result: ExportResult from the export service.

    Returns:
        CSV response or JSON error tuple.
    """
    if not result.ok:
        return jsonify(createExportErrorPayload(result)), result.status_code
    response = Response(result.content, mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={result.filename}"
    return response
