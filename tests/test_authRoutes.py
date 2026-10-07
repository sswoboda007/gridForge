# -*- coding: utf-8 -*-
# tests/test_authRoutes.py
"""
Tests GridForge local demo authentication routes.

The tests verify demo login rendering, safe local redirects, invalid login
rejection, logout behavior, and server-side role denial for customer users.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Any, cast

# 2) Third-party imports (alphabetized)
from flask.testing import FlaskClient

# 3) Application-specific imports (alphabetized)


def test_loginPageRendersDemoUsersAndNormalizesExternalNext(client: FlaskClient) -> None:
    """
    Verifies the demo login page lists roles and normalizes unsafe redirects.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.get("/auth/login?next=https://example.invalid/admin/projects")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Choose a local demo role" in body
    assert "GridForge Owner / Platform Admin" in body
    assert "Customer Contact" in body
    assert 'name="next" type="hidden" value="/"' in body


def test_demoLoginRedirectsToSafeLocalPathAndAllowsAdminAccess(client: FlaskClient) -> None:
    """
    Verifies demo admin login redirects locally and unlocks admin routes.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.post(
        "/auth/demo-login",
        data={"userId": "demo_platform_admin", "next": "/admin/projects"},
    )
    admin_response = client.get("/admin/projects")

    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/projects"
    assert admin_response.status_code == 200
    assert "Customer Workflow Projects" in admin_response.get_data(as_text=True)


def test_demoLoginRejectsInvalidUser(client: FlaskClient) -> None:
    """
    Verifies unknown demo user ids are rejected.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.post(
        "/auth/demo-login",
        data={"userId": "missing", "next": "/admin/projects"},
    )

    assert response.status_code == 400


def test_logoutClearsDemoAccess(client: FlaskClient) -> None:
    """
    Verifies logout removes demo access to guarded routes.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    client.post(
        "/auth/demo-login",
        data={"userId": "demo_platform_admin", "next": "/admin/projects"},
    )
    allowed_response = client.get("/admin/projects")
    logout_response = client.post("/auth/logout")
    denied_response = client.get("/admin/projects")

    assert allowed_response.status_code == 200
    assert logout_response.status_code == 302
    assert logout_response.headers["Location"] == "/"
    assert denied_response.status_code == 403


def test_customerRoleCannotAccessInternalAdminProjects(client: FlaskClient) -> None:
    """
    Verifies customer users cannot access internal project review routes.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    create_response = client.post("/api/intake", json=createValidAuthRoutePayload())
    create_payload = cast(dict[str, Any], create_response.get_json())
    login_response = client.post(
        "/auth/demo-login",
        data={"userId": "demo_customer_contact", "next": "/admin/projects"},
    )
    list_response = client.get("/admin/projects")
    detail_response = client.get(f"/admin/projects/{create_payload['projectId']}")

    assert login_response.status_code == 302
    assert list_response.status_code == 403
    assert detail_response.status_code == 403


def test_workflowAnalystCanAccessInternalAdminProjects(client: FlaskClient) -> None:
    """
    Verifies non-admin internal roles can review submitted projects.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    create_response = client.post("/api/intake", json=createValidAuthRoutePayload())
    create_payload = cast(dict[str, Any], create_response.get_json())
    client.post(
        "/auth/demo-login",
        data={"userId": "demo_workflow_analyst", "next": "/admin/projects"},
    )

    list_response = client.get("/admin/projects")
    detail_response = client.get(f"/admin/projects/{create_payload['projectId']}")

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert "Phase 3 Auth Smoke Co" in list_response.get_data(as_text=True)
    assert "intake_submitted" in detail_response.get_data(as_text=True)


def createValidAuthRoutePayload() -> dict[str, object]:
    """
    Creates a complete sample route payload for auth-route tests.

    Returns:
        Valid route payload.
    """
    return {
        "organizationName": "Phase 3 Auth Smoke Co",
        "primaryContactName": "Pat Customer",
        "primaryContactEmail": "pat@example.test",
        "workflowType": "Customer discovery",
        "workflowDescription": "Turn messy intake into a structured blueprint.",
        "currentTools": "spreadsheets, email, AI chats",
        "desiredOutcome": "A structured blueprint and support flow.",
        "successDefinition": "Clear workflow from intake to support.",
        "usersPermissions": "Admins, analysts, developers, QA, support, customers.",
        "workflowLifecycle": "Lead captured to support.",
        "statuses": "Lead, intake, blueprint, build, QA, handoff, support.",
        "formsDataFiles": "Organization, project, intake, blueprint, plan, QA.",
        "dashboardsReports": "Command center, review queue, exports.",
        "integrationsNotifications": "Email and AI provider later.",
        "additionalContext": "Cloud-first and web-first.",
        "budgetRange": "Defined later",
        "aiConsentAccepted": True,
        "termsAccepted": True,
    }
