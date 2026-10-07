# -*- coding: utf-8 -*-
# tests/test_developerRoutes.py
"""
Tests GridForge developer-plan routes.

The tests verify generation after blueprint approval, internal-only route guards,
customer denial, developer-plan detail rendering, QA limited view, and technical
review actions.

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
from gridforge.domain.enums import ProjectStatus
from gridforge.repositoryBundle import AppRepositories
from tests.test_blueprintRoutes import createValidBlueprintRoutePayload, loginDemoRole


def test_generateDeveloperPlanRouteRequiresApprovedBlueprintAndInternalRole(
    client: FlaskClient,
) -> None:
    """
    Verifies developer-plan generation is guarded and requires approved blueprint.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    blueprint_id = createReviewedBlueprintViaRoutes(client)

    anonymous_response = client.post(f"/admin/blueprints/{blueprint_id}/generate-developer-plan")
    loginDemoRole(client, "demo_customer_contact")
    customer_response = client.post(f"/admin/blueprints/{blueprint_id}/generate-developer-plan")
    loginDemoRole(client, "demo_developer")
    unapproved_response = client.post(f"/admin/blueprints/{blueprint_id}/generate-developer-plan")
    approveBlueprintViaRoutes(client, blueprint_id)
    loginDemoRole(client, "demo_developer")
    generated_response = client.post(f"/admin/blueprints/{blueprint_id}/generate-developer-plan")
    payload = cast(dict[str, Any], generated_response.get_json())

    assert anonymous_response.status_code == 403
    assert customer_response.status_code == 403
    assert unapproved_response.status_code == 409
    assert generated_response.status_code == 201
    assert payload["ok"] is True
    assert payload["developerPlanId"].startswith("developer_plan_")
    assert payload["status"] == "needs_technical_review"


def test_developerPlanDetailIsDeveloperOnlyAndShowsImplementationSlices(
    client: FlaskClient,
) -> None:
    """
    Verifies customer users cannot view developer plans and internal roles can.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    _, developer_plan_id = createDeveloperPlanViaRoutes(client)

    loginDemoRole(client, "demo_customer_contact")
    customer_response = client.get(f"/developer/plans/{developer_plan_id}")
    loginDemoRole(client, "demo_qa_reviewer")
    qa_response = client.get(f"/developer/plans/{developer_plan_id}")
    loginDemoRole(client, "demo_developer")
    developer_response = client.get(f"/developer/plans/{developer_plan_id}")
    developer_body = developer_response.get_data(as_text=True)

    assert customer_response.status_code == 403
    assert qa_response.status_code == 200
    assert developer_response.status_code == 200
    assert "Developer-only content" in developer_body
    assert "Implementation slice specs" in developer_body
    assert "Developer plan workflow" in developer_body
    assert "Do not share this implementation plan with customer users." in developer_body


def test_developerPlanReviewRequiresDeveloperAndUpdatesProject(
    app: Flask,
    client: FlaskClient,
) -> None:
    """
    Verifies technical review actions require developer/admin and update state.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, developer_plan_id = createDeveloperPlanViaRoutes(client)

    loginDemoRole(client, "demo_customer_contact")
    customer_response = client.post(
        f"/developer/plans/{developer_plan_id}/review",
        json={"action": "approve"},
    )
    loginDemoRole(client, "demo_qa_reviewer")
    qa_response = client.post(
        f"/developer/plans/{developer_plan_id}/review",
        json={"action": "approve"},
    )
    loginDemoRole(client, "demo_developer")
    missing_reason_response = client.post(
        f"/developer/plans/{developer_plan_id}/review",
        json={"action": "block", "blockerReason": ""},
    )
    approve_response = client.post(
        f"/developer/plans/{developer_plan_id}/review",
        json={"action": "approve"},
    )
    payload = cast(dict[str, Any], approve_response.get_json())
    project = repositories.workflow_project_repo.getRecord(project_id)
    audit_events = repositories.audit_event_repo.listByProject(project_id)

    assert customer_response.status_code == 403
    assert qa_response.status_code == 403
    assert missing_reason_response.status_code == 400
    assert approve_response.status_code == 200
    assert payload["status"] == "approved"
    assert project is not None
    assert project.status == ProjectStatus.DEVELOPER_PLAN_APPROVED
    assert any(event.event_type == "developer_plan_approved" for event in audit_events)


def test_developerPlanReviewCanBlockWithReason(client: FlaskClient) -> None:
    """
    Verifies developer can block a plan with a required reason.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    _, developer_plan_id = createDeveloperPlanViaRoutes(client)
    loginDemoRole(client, "demo_developer")

    response = client.post(
        f"/developer/plans/{developer_plan_id}/review",
        json={"action": "block", "blockerReason": "Confirm target repository."},
    )
    payload = cast(dict[str, Any], response.get_json())

    assert response.status_code == 200
    assert payload["status"] == "blocked"


def test_developerPlanReviewRejectsUnsupportedAction(client: FlaskClient) -> None:
    """
    Verifies unsupported technical review actions fail safely.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    _, developer_plan_id = createDeveloperPlanViaRoutes(client)
    loginDemoRole(client, "demo_developer")

    response = client.post(
        f"/developer/plans/{developer_plan_id}/review",
        json={"action": "ship"},
    )

    assert response.status_code == 400
    assert cast(dict[str, Any], response.get_json())["errors"] == ["Unsupported review action."]


def createDeveloperPlanViaRoutes(client: FlaskClient) -> tuple[str, str]:
    """
    Creates an internal developer plan through live route handlers.

    Args:
        client: Flask test client fixture.

    Returns:
        Tuple of project id and developer plan id.
    """
    project_id, blueprint_id = createApprovedBlueprintViaRoutes(client)
    loginDemoRole(client, "demo_developer")
    response = client.post(f"/admin/blueprints/{blueprint_id}/generate-developer-plan")
    payload = cast(dict[str, Any], response.get_json())

    assert response.status_code == 201
    return project_id, str(payload["developerPlanId"])


def createApprovedBlueprintViaRoutes(client: FlaskClient) -> tuple[str, str]:
    """
    Creates an approved customer blueprint through routes.

    Args:
        client: Flask test client fixture.

    Returns:
        Tuple of project id and blueprint id.
    """
    project_id, blueprint_id = createReviewedBlueprintWithProjectViaRoutes(client)
    approveBlueprintViaRoutes(client, blueprint_id)
    return project_id, blueprint_id


def createReviewedBlueprintViaRoutes(client: FlaskClient) -> str:
    """
    Creates a blueprint ready for customer review through routes.

    Args:
        client: Flask test client fixture.

    Returns:
        Reviewed blueprint id.
    """
    _, blueprint_id = createReviewedBlueprintWithProjectViaRoutes(client)
    return blueprint_id


def createReviewedBlueprintWithProjectViaRoutes(client: FlaskClient) -> tuple[str, str]:
    """
    Creates a generated and internally reviewed blueprint through routes.

    Args:
        client: Flask test client fixture.

    Returns:
        Tuple of project id and blueprint id.
    """
    intake_response = client.post("/api/intake", json=createValidBlueprintRoutePayload())
    intake_payload = cast(dict[str, Any], intake_response.get_json())
    project_id = str(intake_payload["projectId"])
    loginDemoRole(client, "demo_workflow_analyst")
    generation_response = client.post(f"/admin/projects/{project_id}/generate-blueprint")
    generation_payload = cast(dict[str, Any], generation_response.get_json())
    blueprint_id = str(generation_payload["blueprintId"])
    review_response = client.post(
        f"/admin/blueprints/{blueprint_id}/review",
        json={"action": "ready_for_customer_review"},
    )

    assert intake_response.status_code == 201
    assert generation_response.status_code == 201
    assert review_response.status_code == 200
    return project_id, blueprint_id


def approveBlueprintViaRoutes(client: FlaskClient, blueprint_id: str) -> None:
    """
    Approves a customer blueprint using the admin override route.

    Args:
        client: Flask test client fixture.
        blueprint_id: Blueprint id.

    Returns:
        None.
    """
    loginDemoRole(client, "demo_platform_admin")
    response = client.post(f"/customer/blueprints/{blueprint_id}/approve")

    assert response.status_code == 200
