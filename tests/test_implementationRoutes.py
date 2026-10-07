# -*- coding: utf-8 -*-
# tests/test_implementationRoutes.py
"""
Tests GridForge implementation-slice routes.

The tests verify developer-only route guards, slice creation from approved developer
plans, slice status updates, blocker handling, and project state/audit effects.

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
from gridforge.domain.enums import ProjectStatus, SliceStatus
from gridforge.repositoryBundle import AppRepositories
from tests.test_blueprintRoutes import loginDemoRole, logoutWithClientSession
from tests.test_developerRoutes import createDeveloperPlanViaRoutes


def test_implementationRoutesRequireDeveloperAndCreateSlices(
    app: Flask,
    client: FlaskClient,
) -> None:
    """
    Verifies slices can be created only after developer-plan approval.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, developer_plan_id = createDeveloperPlanViaRoutes(client)

    logoutWithClientSession(client)
    anonymous_response = client.post(f"/developer/projects/{project_id}/slices")
    loginDemoRole(client, "demo_customer_contact")
    customer_response = client.post(f"/developer/projects/{project_id}/slices")
    loginDemoRole(client, "demo_developer")
    unapproved_response = client.post(f"/developer/projects/{project_id}/slices")
    approveDeveloperPlanViaRoute(client, developer_plan_id)
    created_response = client.post(f"/developer/projects/{project_id}/slices")
    payload = cast(dict[str, Any], created_response.get_json())
    project = repositories.workflow_project_repo.getRecord(project_id)
    audit_events = repositories.audit_event_repo.listByProject(project_id)

    assert anonymous_response.status_code == 403
    assert customer_response.status_code == 403
    assert unapproved_response.status_code == 409
    assert created_response.status_code == 201
    assert len(payload["sliceIds"]) == 2
    assert len(payload["qaItemIds"]) == 3
    assert project is not None
    assert project.status == ProjectStatus.BUILD_QUEUED
    assert any(event.event_type == "implementation_slices_created" for event in audit_events)


def test_implementationRoutesRenderAndUpdateSliceStatus(
    app: Flask,
    client: FlaskClient,
) -> None:
    """
    Verifies slice list rendering and developer status updates.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, slice_ids, _ = createSlicesViaRoutes(client)

    list_response = client.get(f"/developer/projects/{project_id}/slices")
    invalid_response = client.post(
        f"/developer/slices/{slice_ids[0]}/status",
        json={"status": "complete"},
    )
    active_response = client.post(
        f"/developer/slices/{slice_ids[0]}/status",
        json={"status": "active"},
    )
    needs_qa_response = client.post(
        f"/developer/slices/{slice_ids[0]}/status",
        json={"status": "needs_qa"},
    )
    updated_slice = repositories.implementation_slice_repo.getRecord(slice_ids[0])
    project = repositories.workflow_project_repo.getRecord(project_id)
    body = list_response.get_data(as_text=True)

    assert list_response.status_code == 200
    assert "Implementation Slices" in body
    assert "Developer-only implementation workflow" in body
    assert invalid_response.status_code == 400
    assert active_response.status_code == 200
    assert needs_qa_response.status_code == 200
    assert updated_slice is not None
    assert updated_slice.status == SliceStatus.NEEDS_QA
    assert project is not None
    assert project.status == ProjectStatus.QA_VALIDATION


def test_implementationRoutesBlockersRequireNotes(app: Flask, client: FlaskClient) -> None:
    """
    Verifies blocker endpoint requires a note and records blockers.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, slice_ids, _ = createSlicesViaRoutes(client)

    missing_note_response = client.post(
        f"/developer/slices/{slice_ids[0]}/blockers",
        json={"blockerNote": ""},
    )
    blocker_response = client.post(
        f"/developer/slices/{slice_ids[0]}/blockers",
        json={"blockerNote": "Waiting for credentials."},
    )
    payload = cast(dict[str, Any], blocker_response.get_json())
    updated_slice = repositories.implementation_slice_repo.getRecord(slice_ids[0])
    project = repositories.workflow_project_repo.getRecord(project_id)

    assert missing_note_response.status_code == 400
    assert blocker_response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["blockerCount"] == 1
    assert updated_slice is not None
    assert "Waiting for credentials." in updated_slice.blockers_json
    assert project is not None
    assert project.status == ProjectStatus.BUILD_BLOCKED


def createSlicesViaRoutes(client: FlaskClient) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """
    Creates approved developer-plan slices through route handlers.

    Args:
        client: Flask test client fixture.

    Returns:
        Tuple of project id, slice ids, and QA item ids.
    """
    project_id, developer_plan_id = createDeveloperPlanViaRoutes(client)
    approveDeveloperPlanViaRoute(client, developer_plan_id)
    response = client.post(f"/developer/projects/{project_id}/slices")
    payload = cast(dict[str, Any], response.get_json())

    assert response.status_code == 201
    return project_id, tuple(payload["sliceIds"]), tuple(payload["qaItemIds"])


def approveDeveloperPlanViaRoute(client: FlaskClient, developer_plan_id: str) -> None:
    """
    Approves a developer plan through the review route.

    Args:
        client: Flask test client fixture.
        developer_plan_id: Developer plan id.

    Returns:
        None.
    """
    loginDemoRole(client, "demo_developer")
    response = client.post(
        f"/developer/plans/{developer_plan_id}/review",
        json={"action": "approve"},
    )

    assert response.status_code == 200
