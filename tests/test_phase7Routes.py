# -*- coding: utf-8 -*-
# tests/test_phase7Routes.py
"""
Tests GridForge Phase 7 dashboard, export, and support routes.

The tests verify command-center role scoping, customer-safe CSV redaction,
internal export guards, support request lifecycle routes, and audit/export records.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import replace
from typing import Any, cast

# 2) Third-party imports (alphabetized)
from flask import Flask
from flask.testing import FlaskClient

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import ProjectStatus, UserRole
from gridforge.repositoryBundle import AppRepositories
from tests.test_blueprintRoutes import loginDemoRole, loginScopedDemoUser, logoutWithClientSession
from tests.test_implementationRoutes import createSlicesViaRoutes


def test_adminDashboardRoutesAreInternalAndRoleScoped(
    app: Flask,
    client: FlaskClient,
) -> None:
    """
    Verifies dashboard guards and admin-only dashboard sections.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    project_id, _, _ = createSlicesViaRoutes(client)

    logoutWithClientSession(client)
    anonymous_response = client.get("/admin")
    loginScopedDemoUser(client, UserRole.CUSTOMER_CONTACT, project_id)
    customer_response = client.get("/admin")
    loginDemoRole(client, "demo_read_only_executive")
    executive_response = client.get("/admin")
    executive_body = executive_response.get_data(as_text=True)
    audit_denied_response = client.get("/admin/audit-log")
    loginDemoRole(client, "demo_platform_admin")
    admin_response = client.get("/admin")
    admin_body = admin_response.get_data(as_text=True)
    audit_response = client.get("/admin/audit-log")
    role_matrix_response = client.get("/admin/role-matrix")

    assert app.extensions["gridforge_repositories"] is not None
    assert anonymous_response.status_code == 403
    assert customer_response.status_code == 403
    assert executive_response.status_code == 200
    assert "GridForge Admin Dashboard" in executive_body
    assert "Admin audit controls" not in executive_body
    assert audit_denied_response.status_code == 403
    assert admin_response.status_code == 200
    assert "Total active projects" in admin_body
    assert "Admin audit controls" in admin_body
    assert audit_response.status_code == 200
    assert role_matrix_response.status_code == 200
    assert "Role Matrix" in role_matrix_response.get_data(as_text=True)


def test_exportRoutesRedactCustomerSafeExportsAndRequireInternalRole(
    app: Flask,
    client: FlaskClient,
) -> None:
    """
    Verifies export route guards, redaction, and audit/export records.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, _, _ = createSlicesViaRoutes(client)

    loginScopedDemoUser(client, UserRole.CUSTOMER_CONTACT, project_id)
    customer_summary_response = client.get(f"/exports/project/{project_id}/customer-summary.csv")
    blueprint_summary_response = client.get(f"/exports/project/{project_id}/blueprint-summary.csv")
    customer_internal_response = client.get(
        f"/exports/project/{project_id}/developer-plan-internal.csv"
    )
    loginDemoRole(client, "demo_developer")
    internal_response = client.get(f"/exports/project/{project_id}/developer-plan-internal.csv")
    qa_response = client.get(f"/exports/project/{project_id}/qa-handoff.csv")
    audit_denied_response = client.get("/exports/audit.csv")
    loginDemoRole(client, "demo_platform_admin")
    audit_response = client.get("/exports/audit.csv")
    export_records = repositories.export_repo.listRecords()
    audit_events = repositories.audit_event_repo.listByProject(project_id)
    customer_body = customer_summary_response.get_data(as_text=True)
    blueprint_body = blueprint_summary_response.get_data(as_text=True)

    assert customer_summary_response.status_code == 200
    assert customer_summary_response.mimetype == "text/csv"
    assert "internal_notes" not in customer_body
    assert "developer_plan" not in customer_body
    assert blueprint_summary_response.status_code == 200
    assert "raw_response_ref" not in blueprint_body
    assert customer_internal_response.status_code == 403
    assert internal_response.status_code == 200
    assert "implementation_overview" in internal_response.get_data(as_text=True)
    assert qa_response.status_code == 200
    assert "acceptance_criterion" in qa_response.get_data(as_text=True)
    assert audit_denied_response.status_code == 403
    assert audit_response.status_code == 200
    assert "event_type" in audit_response.get_data(as_text=True)
    assert len(export_records) >= 5
    assert any(event.event_type == "export_downloaded" for event in audit_events)


def test_supportRoutesRequireSupportRoleAndHandoffReadyProject(
    app: Flask,
    client: FlaskClient,
) -> None:
    """
    Verifies support routes require support/admin roles and handoff-ready projects.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, _, _ = createSlicesViaRoutes(client)

    loginDemoRole(client, "demo_customer_contact")
    customer_response = client.get(f"/support/projects/{project_id}")
    loginDemoRole(client, "demo_support_manager")
    support_page_response = client.get(f"/support/projects/{project_id}")
    premature_create_response = client.post(
        f"/support/projects/{project_id}/requests",
        json={"title": "Support", "customerDescription": "Help after launch."},
    )
    markProjectHandoffReady(repositories, project_id)
    missing_title_response = client.post(
        f"/support/projects/{project_id}/requests",
        json={"title": "", "customerDescription": "Help after launch."},
    )
    create_response = client.post(
        f"/support/projects/{project_id}/requests",
        json={
            "title": "Launch support",
            "customerDescription": "Help with post-handoff workflow.",
            "requestType": "support",
            "priority": "high",
        },
    )
    payload = cast(dict[str, Any], create_response.get_json())
    status_response = client.post(
        f"/support/requests/{payload['supportRequestId']}/status",
        json={
            "status": "resolved",
            "internalNotes": "Fixed internally.",
            "customerVisibleResponse": "Resolved for your team.",
        },
    )
    status_payload = cast(dict[str, Any], status_response.get_json())
    project = repositories.workflow_project_repo.getRecord(project_id)
    audit_events = repositories.audit_event_repo.listByProject(project_id)

    assert customer_response.status_code == 403
    assert support_page_response.status_code == 200
    assert "Support Requests" in support_page_response.get_data(as_text=True)
    assert premature_create_response.status_code == 409
    assert missing_title_response.status_code == 400
    assert create_response.status_code == 201
    assert payload["status"] == "open"
    assert status_response.status_code == 200
    assert status_payload["status"] == "resolved"
    assert project is not None
    assert project.status == ProjectStatus.SUPPORT_RETAINER
    assert any(event.event_type == "support_request_created" for event in audit_events)
    assert any(event.event_type == "support_request_status_changed" for event in audit_events)


def markProjectHandoffReady(repositories: AppRepositories, project_id: str) -> None:
    """
    Marks a project handoff-ready for support route tests.

    Args:
        repositories: Repository bundle.
        project_id: Project id.

    Returns:
        None.
    """
    project = repositories.workflow_project_repo.getRecord(project_id)
    assert project is not None
    repositories.workflow_project_repo.updateRecord(
        replace(project, status=ProjectStatus.HANDOFF_READY)
    )
