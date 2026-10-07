# -*- coding: utf-8 -*-
# tests/test_supportRequestService.py
"""
Tests GridForge support request service behavior.

The tests verify support requests require handoff/support-ready projects, update
project support state, validate required input, update statuses, and record audit
events.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import replace

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import ProjectStatus, SupportStatus
from gridforge.services.supportRequestService import SupportRequestService
from tests.fakes import createFakeRepositories
from tests.test_developerPlanService import CURRENT_TIME_MS
from tests.test_implementationSliceService import createApprovedDeveloperPlan


def test_supportRequestServiceRequiresHandoffReadyProject() -> None:
    """
    Verifies support requests are blocked before handoff/support readiness.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)

    result = SupportRequestService(repositories).createSupportRequest(
        project_id,
        title="Support item",
        customer_description="Help after launch.",
        actor_user_id="demo_support_manager",
        current_time_ms=CURRENT_TIME_MS + 7,
    )

    assert result.status_code == 409
    assert result.errors == ("Support requests require handoff or support-ready project status.",)
    assert repositories.support_request_repo.listRecords() == ()


def test_supportRequestServiceCreatesRequestAndUpdatesProject() -> None:
    """
    Verifies valid support requests update project support-retainer state.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    project = repositories.workflow_project_repo.getRecord(project_id)
    assert project is not None
    repositories.workflow_project_repo.updateRecord(
        replace(project, status=ProjectStatus.HANDOFF_READY)
    )

    missing_title_result = SupportRequestService(repositories).createSupportRequest(
        project_id,
        title=" ",
        customer_description="Help after launch.",
        actor_user_id="demo_support_manager",
    )
    result = SupportRequestService(repositories).createSupportRequest(
        project_id,
        title="Support item",
        customer_description="Help after launch.",
        actor_user_id="demo_support_manager",
        request_type="enhancement",
        priority="high",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    updated_project = repositories.workflow_project_repo.getRecord(project_id)

    assert missing_title_result.status_code == 400
    assert result.status_code == 201
    assert result.support_request is not None
    assert result.support_request.status == SupportStatus.OPEN
    assert result.support_request.request_type == "enhancement"
    assert updated_project is not None
    assert updated_project.status == ProjectStatus.SUPPORT_RETAINER
    assert result.audit_events[0].event_type == "support_request_created"


def test_supportRequestServiceUpdatesStatusAndRejectsInvalidStatus() -> None:
    """
    Verifies support request status updates and validation errors.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    project = repositories.workflow_project_repo.getRecord(project_id)
    assert project is not None
    repositories.workflow_project_repo.updateRecord(
        replace(project, status=ProjectStatus.HANDOFF_READY)
    )
    create_result = SupportRequestService(repositories).createSupportRequest(
        project_id,
        title="Support item",
        customer_description="Help after launch.",
        actor_user_id="demo_support_manager",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    assert create_result.support_request is not None
    service = SupportRequestService(repositories)

    invalid_result = service.updateSupportRequestStatus(
        create_result.support_request.id,
        status_value="done",
        actor_user_id="demo_support_manager",
    )
    resolved_result = service.updateSupportRequestStatus(
        create_result.support_request.id,
        status_value="resolved",
        actor_user_id="demo_support_manager",
        internal_notes="Fixed internally.",
        customer_visible_response="Resolved for your team.",
        current_time_ms=CURRENT_TIME_MS + 8,
    )

    assert invalid_result.status_code == 400
    assert resolved_result.status_code == 200
    assert resolved_result.support_request is not None
    assert resolved_result.support_request.status == SupportStatus.RESOLVED
    assert resolved_result.support_request.resolved_at_ms == CURRENT_TIME_MS + 8
    assert resolved_result.support_request.internal_notes == "Fixed internally."
    assert resolved_result.audit_events[0].event_type == "support_request_status_changed"
