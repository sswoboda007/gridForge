# -*- coding: utf-8 -*-
# tests/test_qaRoutes.py
"""
Tests GridForge QA validation routes.

The tests verify QA route guards, manual QA item creation, QA failure lifecycle
updates, all-passing QA demo readiness, and audit creation.

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
from tests.test_blueprintRoutes import loginDemoRole
from tests.test_implementationRoutes import createSlicesViaRoutes


def test_qaRoutesRequireQaRoleAndRenderProject(client: FlaskClient) -> None:
    """
    Verifies QA project view is guarded and renders QA state.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    project_id, _, _ = createSlicesViaRoutes(client)

    loginDemoRole(client, "demo_developer")
    developer_response = client.get(f"/qa/projects/{project_id}")
    loginDemoRole(client, "demo_qa_reviewer")
    qa_response = client.get(f"/qa/projects/{project_id}")
    body = qa_response.get_data(as_text=True)

    assert developer_response.status_code == 403
    assert qa_response.status_code == 200
    assert "QA Validation" in body
    assert "QA failures block demo" in body


def test_qaRoutesCreateManualQaItem(app: Flask, client: FlaskClient) -> None:
    """
    Verifies QA reviewers can add manual QA items.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, slice_ids, _ = createSlicesViaRoutes(client)
    loginDemoRole(client, "demo_qa_reviewer")

    missing_title_response = client.post(f"/qa/projects/{project_id}/items", json={"title": ""})
    created_response = client.post(
        f"/qa/projects/{project_id}/items",
        json={
            "title": "Manual smoke QA",
            "sliceId": slice_ids[0],
            "acceptanceCriterion": "Manual QA passes.",
            "expectedBehavior": "Evidence captured.",
        },
    )
    payload = cast(dict[str, Any], created_response.get_json())
    audit_events = repositories.audit_event_repo.listByProject(project_id)

    assert missing_title_response.status_code == 400
    assert created_response.status_code == 201
    assert payload["status"] == "open"
    assert any(event.event_type == "qa_item_created" for event in audit_events)


def test_qaRoutesFailureBlocksDemoReadiness(app: Flask, client: FlaskClient) -> None:
    """
    Verifies failed QA updates project and blocks demo readiness.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, _, qa_item_ids = createSlicesViaRoutes(client)
    loginDemoRole(client, "demo_qa_reviewer")

    response = client.post(
        f"/qa/items/{qa_item_ids[0]}/status",
        json={"status": "failed", "actualBehavior": "Observed failure."},
    )
    payload = cast(dict[str, Any], response.get_json())
    project = repositories.workflow_project_repo.getRecord(project_id)
    audit_events = repositories.audit_event_repo.listByProject(project_id)

    assert response.status_code == 200
    assert payload["status"] == "failed"
    assert project is not None
    assert project.status == ProjectStatus.QA_FAILED_NEEDS_FIXES
    assert any(event.event_type == "qa_item_status_changed" for event in audit_events)


def test_qaRoutesPassingAllChecksEnablesDemoReady(app: Flask, client: FlaskClient) -> None:
    """
    Verifies passing all generated QA items marks the project demo-ready.

    Args:
        app: Test Flask app fixture.
        client: Flask test client fixture.

    Returns:
        None.
    """
    repositories = cast(AppRepositories, app.extensions["gridforge_repositories"])
    project_id, _, qa_item_ids = createSlicesViaRoutes(client)
    loginDemoRole(client, "demo_qa_reviewer")

    for qa_item_id in qa_item_ids:
        response = client.post(
            f"/qa/items/{qa_item_id}/status",
            json={"status": "passed", "actualBehavior": "Passed."},
        )
        assert response.status_code == 200

    project = repositories.workflow_project_repo.getRecord(project_id)

    assert project is not None
    assert project.status == ProjectStatus.DEMO_READY


def test_qaRoutesRejectUnsupportedStatus(client: FlaskClient) -> None:
    """
    Verifies unsupported QA status values fail safely.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    _, _, qa_item_ids = createSlicesViaRoutes(client)
    loginDemoRole(client, "demo_qa_reviewer")

    response = client.post(
        f"/qa/items/{qa_item_ids[0]}/status",
        json={"status": "ready_to_ship"},
    )

    assert response.status_code == 400
    assert cast(dict[str, Any], response.get_json())["errors"] == ["Unsupported QA status."]
