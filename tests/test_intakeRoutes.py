# -*- coding: utf-8 -*-
# tests/test_intakeRoutes.py
"""
Tests GridForge Phase 2 intake and internal project review routes.

The tests verify public intake submission, route validation errors, role-guarded
admin access, internal project listing, and escaped rendering of customer-provided
text.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Any, cast

# 2) Third-party imports (alphabetized)
from flask import Flask
from flask.testing import FlaskClient

# 3) Application-specific imports (alphabetized)
from gridforge.repositoryBundle import AppRepositories


def test_startPageRendersIntakeForm(client: FlaskClient) -> None:
    """
    Verifies the start page renders the Phase 2 intake form.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.get("/start")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Submit the first version of a Customer Workflow Project" in body
    assert 'name="organizationName"' in body
    assert 'action="/api/intake"' in body


def test_createIntakeApiStoresRecordsAndReturnsCoverage(app: Flask, client: FlaskClient) -> None:
    """
    Verifies the public intake API stores project records and returns IDs.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.post("/api/intake", json=createValidRoutePayload())
    payload = cast(dict[str, Any], response.get_json())
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])

    assert response.status_code == 201
    assert payload["ok"] is True
    assert payload["coverageCount"] == 7
    assert payload["coverageTotal"] == 7
    assert payload["completionPercent"] == 100
    assert payload["missingDetailCategories"] == []
    assert payload["organizationId"].startswith("org_")
    assert payload["projectId"].startswith("project_")
    assert payload["intakeId"].startswith("intake_")
    assert repositories.workflow_project_repo.getRecord(payload["projectId"]) is not None
    assert repositories.intake_repo.getRecord(payload["intakeId"]) is not None
    assert repositories.audit_event_repo.listByProject(payload["projectId"])[0].event_type == (
        "intake_submitted"
    )


def test_createIntakeApiRejectsMissingFields(client: FlaskClient) -> None:
    """
    Verifies intake API validation failures return field errors.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.post("/api/intake", json={"organizationName": "Example Co"})
    payload = cast(dict[str, Any], response.get_json())

    assert response.status_code == 400
    assert payload["ok"] is False
    assert "primaryContactName" in payload["errors"]
    assert "primaryContactEmail" in payload["errors"]
    assert "aiConsentAccepted" in payload["errors"]


def test_createIntakeApiAcceptsFormPayload(client: FlaskClient) -> None:
    """
    Verifies form-encoded intake submissions are supported.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.post("/api/intake", data=createValidRoutePayload())
    payload = cast(dict[str, Any], response.get_json())

    assert response.status_code == 201
    assert payload["ok"] is True
    assert payload["status"] == "intake_ready_for_blueprint"


def test_adminProjectsFailClosedWithoutLogin(client: FlaskClient) -> None:
    """
    Verifies internal project list access fails closed without a logged-in user.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.get("/admin/projects")

    assert response.status_code == 403


def test_adminProjectsShowSubmittedIntakeWithEscapedText(client: FlaskClient) -> None:
    """
    Verifies admins can review submitted projects and customer text is escaped.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    payload = createValidRoutePayload()
    payload["workflowDescription"] = "Need <script>alert('x')</script> workflow help."
    create_response = client.post("/api/intake", json=payload)
    create_payload = cast(dict[str, Any], create_response.get_json())
    loginAsPlatformAdmin(client)

    list_response = client.get("/admin/projects")
    detail_response = client.get(f"/admin/projects/{create_payload['projectId']}")
    list_body = list_response.get_data(as_text=True)
    detail_body = detail_response.get_data(as_text=True)

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert "GridForge Systems" in list_body
    assert "GridForge Systems — Customer discovery" in detail_body
    assert "Need &lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt; workflow help." in detail_body
    assert "<script>alert('x')</script>" not in detail_body
    assert "intake_submitted" in detail_body


def test_adminProjectDetailReturnsNotFoundForMissingProject(client: FlaskClient) -> None:
    """
    Verifies missing admin project detail routes return 404 for admins.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    loginAsPlatformAdmin(client)

    response = client.get("/admin/projects/project_missing")

    assert response.status_code == 404


def loginAsPlatformAdmin(client: FlaskClient) -> None:
    """
    Logs into the test client as the local demo platform admin.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.post(
        "/auth/demo-login",
        data={"userId": "demo_platform_admin", "next": "/admin/projects"},
    )

    assert response.status_code == 302


def createValidRoutePayload() -> dict[str, object]:
    """
    Creates a complete sample route payload.

    Returns:
        Valid route payload.
    """
    return {
        "organizationName": "GridForge Systems",
        "primaryContactName": "Sean Swoboda",
        "primaryContactEmail": "sean@example.test",
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
