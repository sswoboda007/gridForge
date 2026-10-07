# -*- coding: utf-8 -*-
# gridforge/web/blueprints/adminRoutes.py
"""
Defines minimal internal admin routes for project review.

These routes expose created customer workflow projects to internal reviewers using
server-side Phase 3 role guards.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import cast

# 2) Third-party imports (alphabetized)
from flask import Blueprint, abort, render_template

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import UserRole
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.dashboardMetricService import DashboardMetricService
from gridforge.web.auth.roleGuards import PROJECT_REVIEW_ROLES, getCurrentUserRoles, roleRequired


def createAdminBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates minimal internal admin routes.

    Args:
        repositories: Repository bundle used to list workflow projects.

    Returns:
        A Flask Blueprint containing admin routes.
    """
    admin_routes = Blueprint("admin", __name__)
    dashboard_metric_service = DashboardMetricService(repositories)

    @admin_routes.get("/admin")
    @roleRequired(*PROJECT_REVIEW_ROLES)
    def dashboard() -> str:
        """
        Renders the internal command-center dashboard.

        Returns:
            Rendered command-center dashboard HTML.
        """
        current_roles = getCurrentUserRoles()
        return cast(
            str,
            render_template(
                "admin/dashboard.html",
                can_view_admin_sections=UserRole.PLATFORM_ADMIN in current_roles,
                metrics=dashboard_metric_service.buildDashboardMetrics(),
                roles=current_roles,
            ),
        )

    @admin_routes.get("/admin/audit-log")
    @roleRequired(UserRole.PLATFORM_ADMIN)
    def auditLog() -> str:
        """
        Renders the internal audit log page.

        Returns:
            Rendered audit log HTML.
        """
        audit_events = tuple(
            sorted(
                repositories.audit_event_repo.listRecords(),
                key=lambda event: event.created_at_ms,
                reverse=True,
            )
        )
        return cast(str, render_template("admin/audit_log.html", audit_events=audit_events))

    @admin_routes.get("/admin/role-matrix")
    @roleRequired(*PROJECT_REVIEW_ROLES)
    def roleMatrix() -> str:
        """
        Renders role-scoped capability guidance.

        Returns:
            Rendered role matrix HTML.
        """
        return cast(str, render_template("admin/role_matrix.html", user_roles=tuple(UserRole)))

    @admin_routes.get("/admin/projects")
    @roleRequired(*PROJECT_REVIEW_ROLES)
    def projectList() -> str:
        """
        Renders the internal project list.

        Returns:
            Rendered internal project list HTML.
        """
        projects = repositories.workflow_project_repo.listRecords()
        organizations = {
            organization.id: organization
            for organization in repositories.organization_repo.listRecords()
        }
        return cast(
            str,
            render_template(
                "admin/project_list.html",
                organizations=organizations,
                projects=projects,
            ),
        )

    @admin_routes.get("/admin/projects/<project_id>")
    @roleRequired(*PROJECT_REVIEW_ROLES)
    def projectDetail(project_id: str) -> str:
        """
        Renders one internal project detail page.

        Args:
            project_id: Workflow project identifier.

        Returns:
            Rendered internal project detail HTML.
        """
        project = repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            abort(404)
            raise RuntimeError("unreachable")
        organization = repositories.organization_repo.getRecord(project.organization_id)
        blueprints = repositories.blueprint_repo.listByProject(project.id)
        intakes = repositories.intake_repo.listByProject(project.id)
        audit_events = repositories.audit_event_repo.listByProject(project.id)
        return cast(
            str,
            render_template(
                "admin/project_detail.html",
                audit_events=audit_events,
                blueprints=blueprints,
                intakes=intakes,
                organization=organization,
                project=project,
            ),
        )

    return admin_routes
