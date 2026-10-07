# -*- coding: utf-8 -*-
# tests/test_implementationSliceService.py
"""
Tests GridForge implementation slice service behavior.

The tests verify slice creation from approved developer plans, QA item generation,
developer status transitions, blocker handling, project lifecycle updates, and
audit events.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import ProjectStatus, QaStatus, SliceStatus
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.developerPlanService import DeveloperPlanService
from gridforge.services.implementationSliceService import ImplementationSliceService
from tests.fakes import createFakeRepositories
from tests.test_developerPlanService import CURRENT_TIME_MS, createDeveloperPlan


def test_implementationSliceServiceCreatesSlicesAndQaItemsFromApprovedPlan() -> None:
    """
    Verifies approved developer plans create slices, QA items, and audit events.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, developer_plan_id = createApprovedDeveloperPlan(repositories)

    result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    duplicate_result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 8,
    )
    project = repositories.workflow_project_repo.getRecord(project_id)

    assert result.ok is True
    assert result.status_code == 201
    assert len(result.slices) == 2
    assert len(result.qa_items) == 3
    assert result.slices[0].developer_plan_id == developer_plan_id
    assert result.slices[0].status == SliceStatus.READY
    assert result.qa_items[0].status == QaStatus.OPEN
    assert result.audit_events[0].event_type == "implementation_slices_created"
    assert result.audit_events[1].event_type == "qa_items_generated"
    assert project is not None
    assert project.status == ProjectStatus.BUILD_QUEUED
    assert duplicate_result.status_code == 409
    assert duplicate_result.errors == ("Project already has implementation slices.",)


def test_implementationSliceServiceRejectsUnapprovedDeveloperPlan() -> None:
    """
    Verifies slice creation requires an approved developer plan.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    developer_plan_id = createDeveloperPlan(repositories)
    developer_plan = repositories.developer_plan_repo.getRecord(developer_plan_id)
    assert developer_plan is not None

    result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        developer_plan.project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )

    assert result.ok is False
    assert result.status_code == 409
    assert result.errors == ("Developer plan must be approved before creating slices.",)
    assert repositories.implementation_slice_repo.listRecords() == ()


def test_implementationSliceServiceUpdatesStatusAndBlockers() -> None:
    """
    Verifies developer status transitions and blockers update project state.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    create_result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    slice_id = create_result.slices[0].id
    service = ImplementationSliceService(repositories)

    active_result = service.updateSliceStatus(
        slice_id,
        status_value="active",
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 8,
    )
    needs_qa_result = service.updateSliceStatus(
        slice_id,
        status_value="needs_qa",
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 9,
    )
    invalid_result = service.updateSliceStatus(
        slice_id,
        status_value="complete",
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 10,
    )
    missing_blocker_result = service.addSliceBlocker(
        slice_id,
        blocker_note=" ",
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 11,
    )
    blocker_result = service.addSliceBlocker(
        slice_id,
        blocker_note="Waiting on repository access.",
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 12,
    )
    project = repositories.workflow_project_repo.getRecord(project_id)

    assert active_result.slices[0].status == SliceStatus.ACTIVE
    assert active_result.slices[0].started_at_ms == CURRENT_TIME_MS + 8
    assert needs_qa_result.slices[0].status == SliceStatus.NEEDS_QA
    assert invalid_result.status_code == 400
    assert invalid_result.errors == ("Unsupported slice status.",)
    assert missing_blocker_result.status_code == 400
    assert blocker_result.slices[0].status == SliceStatus.BLOCKED
    assert "Waiting on repository access." in blocker_result.slices[0].blockers_json
    assert project is not None
    assert project.status == ProjectStatus.BUILD_BLOCKED
    assert blocker_result.audit_events[0].event_type == "implementation_slice_blocked"


def createApprovedDeveloperPlan(repositories: AppRepositories) -> tuple[str, str]:
    """
    Creates and approves a developer plan.

    Args:
        repositories: Repository bundle.

    Returns:
        Tuple of project id and developer plan id.
    """
    developer_plan_id = createDeveloperPlan(repositories)
    review_result = DeveloperPlanService(repositories).reviewDeveloperPlan(
        developer_plan_id,
        action="approve",
        reviewer_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 6,
    )
    assert review_result.developer_plan is not None
    return review_result.developer_plan.project_id, developer_plan_id
