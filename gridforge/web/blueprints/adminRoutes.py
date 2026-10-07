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
from gridforge.repositoryBundle import AppRepositories
from gridforge.web.auth.roleGuards import PROJECT_REVIEW_ROLES, roleRequired


def createAdminBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates minimal internal admin routes.

    Args:
        repositories: Repository bundle used to list workflow projects.

    Returns:
        A Flask Blueprint containing admin routes.
    """
    admin_routes = Blueprint("admin", __name__)

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
        intakes = repositories.intake_repo.listByProject(project.id)
        audit_events = repositories.audit_event_repo.listByProject(project.id)
        return cast(
            str,
            render_template(
                "admin/project_detail.html",
                audit_events=audit_events,
                intakes=intakes,
                organization=organization,
                project=project,
            ),
        )

    return admin_routes
