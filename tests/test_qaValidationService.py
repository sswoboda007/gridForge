# -*- coding: utf-8 -*-
# tests/test_qaValidationService.py
"""
Tests GridForge QA validation service behavior.

The tests verify manual QA item creation, QA status enforcement, failed QA blocking
demo readiness, and passed QA enabling demo-ready project state.

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
from gridforge.services.implementationSliceService import ImplementationSliceService
from gridforge.services.qaValidationService import QaValidationService
from tests.fakes import createFakeRepositories
from tests.test_developerPlanService import CURRENT_TIME_MS
from tests.test_implementationSliceService import createApprovedDeveloperPlan


def test_qaValidationServiceCreatesManualItemsAndRejectsInvalidInput() -> None:
    """
    Verifies manual QA item creation and validation errors.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    slice_result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    service = QaValidationService(repositories)

    missing_title_result = service.createQaItem(
        project_id,
        title=" ",
        actor_user_id="demo_qa_reviewer",
    )
    invalid_slice_result = service.createQaItem(
        project_id,
        title="Manual QA",
        actor_user_id="demo_qa_reviewer",
        implementation_slice_id="missing",
    )
    created_result = service.createQaItem(
        project_id,
        title="Manual QA",
        actor_user_id="demo_qa_reviewer",
        implementation_slice_id=slice_result.slices[0].id,
        acceptance_criterion="Manual check passes.",
        expected_behavior="Visible demo evidence.",
        current_time_ms=CURRENT_TIME_MS + 8,
    )

    assert missing_title_result.status_code == 400
    assert invalid_slice_result.status_code == 404
    assert created_result.status_code == 201
    assert created_result.qa_item is not None
    assert created_result.qa_item.status == QaStatus.OPEN
    assert created_result.audit_events[0].event_type == "qa_item_created"


def test_qaValidationServiceFailureBlocksDemoReadiness() -> None:
    """
    Verifies failed QA updates linked slice and project state.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    slice_result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    qa_item = slice_result.qa_items[0]

    result = QaValidationService(repositories).updateQaItemStatus(
        qa_item.id,
        status_value="failed",
        actor_user_id="demo_qa_reviewer",
        actual_behavior="Customer detail leaked into internal view.",
        current_time_ms=CURRENT_TIME_MS + 8,
    )
    updated_slice = repositories.implementation_slice_repo.getRecord(slice_result.slices[0].id)
    project = repositories.workflow_project_repo.getRecord(project_id)

    assert result.status_code == 200
    assert result.qa_item is not None
    assert result.qa_item.status == QaStatus.FAILED
    assert updated_slice is not None
    assert updated_slice.status == SliceStatus.QA_FAILED
    assert updated_slice.qa_status == QaStatus.FAILED
    assert project is not None
    assert project.status == ProjectStatus.QA_FAILED_NEEDS_FIXES
    assert result.audit_events[0].event_type == "qa_item_status_changed"


def test_qaValidationServicePassingAllRequiredQaEnablesDemoReady() -> None:
    """
    Verifies all-passing QA completes slices and marks project demo-ready.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    slice_result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    service = QaValidationService(repositories)

    for index, qa_item in enumerate(slice_result.qa_items, start=1):
        service.updateQaItemStatus(
            qa_item.id,
            status_value="passed",
            actor_user_id="demo_qa_reviewer",
            actual_behavior="Passed",
            current_time_ms=CURRENT_TIME_MS + 10 + index,
        )

    project = repositories.workflow_project_repo.getRecord(project_id)
    slices = repositories.implementation_slice_repo.listByProject(project_id)
    qa_items = repositories.qa_validation_repo.listByProject(project_id)

    assert project is not None
    assert project.status == ProjectStatus.DEMO_READY
    assert all(
        implementation_slice.status == SliceStatus.COMPLETE for implementation_slice in slices
    )
    assert all(implementation_slice.qa_status == QaStatus.PASSED for implementation_slice in slices)
    assert all(qa_item.status == QaStatus.PASSED for qa_item in qa_items)


def test_qaValidationServiceRejectsUnsupportedStatus() -> None:
    """
    Verifies invalid QA statuses fail safely.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    slice_result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )

    result = QaValidationService(repositories).updateQaItemStatus(
        slice_result.qa_items[0].id,
        status_value="demo_ready",
        actor_user_id="demo_qa_reviewer",
        current_time_ms=CURRENT_TIME_MS + 8,
    )

    assert result.status_code == 400
    assert result.errors == ("Unsupported QA status.",)
