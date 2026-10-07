# -*- coding: utf-8 -*-
# tests/test_blueprintRoutes.py
"""
Tests GridForge customer blueprint generation and review routes.

The tests verify server-side role guards, fake-AI blueprint generation, internal
review gating, customer project scope, customer-safe rendering, approval, and
change-request behavior.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from collections.abc import MutableMapping
from typing import Any, cast

# 2) Third-party imports (alphabetized)
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import ProjectStatus, UserRole
from gridforge.repositoryBundle import AppRepositories
from gridforge.web.auth.roleGuards import loginDemoUser, logoutDemoUser


def test_generateBlueprintRouteRequiresInternalAnalystOrAdmin(client: FlaskClient) -> None:
    """
    Verifies anonymous/customer users cannot generate customer blueprints.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    project_id = createReadyProjectViaRoute(client)

    anonymous_response = client.post(f"/admin/projects/{project_id}/generate-blueprint")
    loginScopedDemoUser(client, UserRole.CUSTOMER_CONTACT, project_id)
    customer_response = client.post(f"/admin/projects/{project_id}/generate-blueprint")
    loginDemoRole(client, "demo_workflow_analyst")
    analyst_response = client.post(f"/admin/projects/{project_id}/generate-blueprint")
    payload = cast(dict[str, Any], analyst_response.get_json())

    assert anonymous_response.status_code == 403
    assert customer_response.status_code == 403
    assert analyst_response.status_code == 201
    assert payload["ok"] is True
    assert payload["blueprintId"].startswith("blueprint_")
    assert payload["status"] == "needs_internal_review"


def test_blueprintRoutesReviewGateAndCustomerSafeRendering(app: Flask, client: FlaskClient) -> None:
    """
    Verifies internal review is required before customer-safe blueprint display.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id = createReadyProjectViaRoute(client)
    loginDemoRole(client, "demo_workflow_analyst")
    blueprint_id = generateBlueprintViaRoute(client, project_id)

    review_queue_response = client.get("/admin/review-queue")
    admin_detail_response = client.get(f"/admin/blueprints/{blueprint_id}")
    draft_customer_response = client.get(f"/customer/blueprints/{blueprint_id}")
    review_response = client.post(
        f"/admin/blueprints/{blueprint_id}/review",
        json={"action": "ready_for_customer_review", "reviewerNotes": "Share with customer."},
    )
    wrong_project_response = getCustomerBlueprintAsScopedUser(
        client,
        blueprint_id,
        project_id="project_wrong",
        role=UserRole.CUSTOMER_CONTACT,
    )
    customer_response = getCustomerBlueprintAsScopedUser(
        client,
        blueprint_id,
        project_id=project_id,
        role=UserRole.CUSTOMER_CONTACT,
    )
    customer_body = customer_response.get_data(as_text=True)

    assert review_queue_response.status_code == 200
    assert "Blueprint Review Queue" in review_queue_response.get_data(as_text=True)
    assert admin_detail_response.status_code == 200
    assert "Internal-only metadata" in admin_detail_response.get_data(as_text=True)
    assert draft_customer_response.status_code == 403
    assert review_response.status_code == 200
    assert wrong_project_response.status_code == 403
    assert customer_response.status_code == 200
    assert "Customer blueprint" in customer_body
    assert "Prompt version" not in customer_body
    assert "Raw response ref" not in customer_body
    assert "fake-customer-blueprint-v1" not in customer_body
    reviewed_blueprint = repositories.blueprint_repo.getRecord(blueprint_id)
    assert reviewed_blueprint is not None
    assert reviewed_blueprint.internal_reviewer_notes == "Share with customer."


def test_customerBlueprintApprovalRequiresStakeholderAndUpdatesProject(
    app: Flask,
    client: FlaskClient,
) -> None:
    """
    Verifies only stakeholders/admins can approve ready customer blueprints.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id = createReadyProjectViaRoute(client)
    blueprint_id = generateAndReviewBlueprint(client, project_id)

    loginScopedDemoUser(client, UserRole.CUSTOMER_CONTACT, project_id)
    customer_contact_response = client.post(f"/customer/blueprints/{blueprint_id}/approve")
    loginScopedDemoUser(client, UserRole.CLIENT_STAKEHOLDER, project_id)
    stakeholder_response = client.post(f"/customer/blueprints/{blueprint_id}/approve")
    payload = cast(dict[str, Any], stakeholder_response.get_json())
    updated_project = repositories.workflow_project_repo.getRecord(project_id)
    audit_events = repositories.audit_event_repo.listByProject(project_id)

    assert customer_contact_response.status_code == 403
    assert stakeholder_response.status_code == 200
    assert payload["status"] == "approved"
    assert updated_project is not None
    assert updated_project.status == ProjectStatus.BLUEPRINT_APPROVED
    assert updated_project.approved_blueprint_id == blueprint_id
    assert any(event.event_type == "blueprint_approved" for event in audit_events)


def test_customerBlueprintChangeRequestRequiresCommentAndCreatesAudit(
    app: Flask,
    client: FlaskClient,
) -> None:
    """
    Verifies customer change requests require comments and create audit events.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id = createReadyProjectViaRoute(client)
    blueprint_id = generateAndReviewBlueprint(client, project_id)
    loginScopedDemoUser(client, UserRole.CUSTOMER_CONTACT, project_id)

    missing_note_response = client.post(
        f"/customer/blueprints/{blueprint_id}/changes-requested",
        json={"changeNote": ""},
    )
    change_response = client.post(
        f"/customer/blueprints/{blueprint_id}/changes-requested",
        json={"changeNote": "Add export detail."},
    )
    payload = cast(dict[str, Any], change_response.get_json())
    updated_project = repositories.workflow_project_repo.getRecord(project_id)
    audit_events = repositories.audit_event_repo.listByProject(project_id)

    assert missing_note_response.status_code == 400
    assert change_response.status_code == 200
    assert payload["status"] == "changes_requested"
    assert updated_project is not None
    assert updated_project.status == ProjectStatus.BLUEPRINT_CHANGES_REQUESTED
    assert any(event.event_type == "blueprint_changes_requested" for event in audit_events)


def test_blueprintReviewRouteRejectsUnsupportedAction(client: FlaskClient) -> None:
    """
    Verifies unsupported internal review actions fail safely.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    project_id = createReadyProjectViaRoute(client)
    loginDemoRole(client, "demo_workflow_analyst")
    blueprint_id = generateBlueprintViaRoute(client, project_id)

    response = client.post(
        f"/admin/blueprints/{blueprint_id}/review",
        json={"action": "publish_without_review"},
    )

    assert response.status_code == 400
    assert cast(dict[str, Any], response.get_json())["errors"] == ["Unsupported review action."]


def createReadyProjectViaRoute(client: FlaskClient) -> str:
    """
    Creates a project ready for blueprint generation through the public route.

    Args:
        client: Flask test client fixture.

    Returns:
        Created project id.
    """
    logoutWithClientSession(client)
    response = client.post("/api/intake", json=createValidBlueprintRoutePayload())
    payload = cast(dict[str, Any], response.get_json())

    assert response.status_code == 201
    return str(payload["projectId"])


def generateBlueprintViaRoute(client: FlaskClient, project_id: str) -> str:
    """
    Generates a blueprint through the internal route.

    Args:
        client: Flask test client fixture.
        project_id: Project id.

    Returns:
        Created blueprint id.
    """
    response = client.post(f"/admin/projects/{project_id}/generate-blueprint")
    payload = cast(dict[str, Any], response.get_json())

    assert response.status_code == 201
    return str(payload["blueprintId"])


def generateAndReviewBlueprint(client: FlaskClient, project_id: str) -> str:
    """
    Generates and internally reviews a blueprint.

    Args:
        client: Flask test client fixture.
        project_id: Project id.

    Returns:
        Blueprint id ready for customer review.
    """
    loginDemoRole(client, "demo_workflow_analyst")
    blueprint_id = generateBlueprintViaRoute(client, project_id)
    response = client.post(
        f"/admin/blueprints/{blueprint_id}/review",
        json={"action": "ready_for_customer_review"},
    )

    assert response.status_code == 200
    return blueprint_id


def getCustomerBlueprintAsScopedUser(
    client: FlaskClient,
    blueprint_id: str,
    project_id: str,
    role: UserRole,
) -> TestResponse:
    """
    Requests a customer blueprint after setting a scoped demo user.

    Args:
        client: Flask test client fixture.
        blueprint_id: Blueprint id.
        project_id: Project id to grant.
        role: Customer-side role to use.

    Returns:
        Flask response object.
    """
    loginScopedDemoUser(client, role, project_id)
    return client.get(f"/customer/blueprints/{blueprint_id}")


def loginDemoRole(client: FlaskClient, user_id: str) -> None:
    """
    Logs in as an existing demo role through the auth route.

    Args:
        client: Flask test client fixture.
        user_id: Demo user id.

    Returns:
        None.
    """
    response = client.post("/auth/demo-login", data={"userId": user_id, "next": "/"})

    assert response.status_code == 302


def loginScopedDemoUser(client: FlaskClient, role: UserRole, project_id: str) -> None:
    """
    Stores a customer-side scoped demo user in the test session.

    Args:
        client: Flask test client fixture.
        role: Role to store.
        project_id: Project scope to grant.

    Returns:
        None.
    """
    with client.session_transaction() as session_data:
        loginDemoUser(
            cast(MutableMapping[str, Any], session_data),
            user_id=f"test_{role.value}",
            email=f"{role.value}@example.test",
            roles=(role,),
            project_ids=(project_id,),
        )


def logoutWithClientSession(client: FlaskClient) -> None:
    """
    Clears any existing demo session for deterministic route setup.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    with client.session_transaction() as session_data:
        logoutDemoUser(cast(MutableMapping[str, Any], session_data))


def createValidBlueprintRoutePayload() -> dict[str, object]:
    """
    Creates a complete intake payload for blueprint route tests.

    Returns:
        Valid intake payload.
    """
    return {
        "organizationName": "Phase 4 Blueprint Co",
        "primaryContactName": "Pat Blueprint",
        "primaryContactEmail": "pat@example.test",
        "workflowType": "Blueprint review",
        "workflowDescription": "Turn intake into a customer-safe blueprint.",
        "currentTools": "spreadsheets, email, chat",
        "desiredOutcome": "Reviewed blueprint and approved scope.",
        "successDefinition": "Customer can approve a clear MVP.",
        "usersPermissions": "Analysts review; customers approve.",
        "workflowLifecycle": "Intake to blueprint approval.",
        "statuses": "Ready, draft, review, approved.",
        "formsDataFiles": "Project, intake, blueprint.",
        "dashboardsReports": "Review queue and customer blueprint.",
        "integrationsNotifications": "AI provider boundary only.",
        "additionalContext": "Keep internal AI metadata hidden.",
        "budgetRange": "Defined later",
        "aiConsentAccepted": True,
        "termsAccepted": True,
    }
