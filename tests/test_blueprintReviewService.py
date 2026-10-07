# -*- coding: utf-8 -*-
# tests/test_blueprintReviewService.py
"""
Tests GridForge customer blueprint review service.

The tests verify internal review, customer approval, change-request transitions,
not-found handling, invalid status handling, and customer-safe projections.

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
from gridforge.domain.enums import ApprovalStatus, BlueprintStatus, ProjectStatus
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.blueprintAiService import BlueprintAiService
from gridforge.services.blueprintReviewService import BlueprintReviewService
from gridforge.services.intakeService import IntakeService
from tests.fakes import createFakeRepositories
from tests.test_intakeService import createValidIntakePayload

CURRENT_TIME_MS = 1000


def test_blueprintReviewServiceMarksReadyApprovesAndCreatesCustomerSafeView() -> None:
    """
    Verifies internal review and approval update blueprint/project state.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    blueprint_id = createDraftBlueprint(repositories)
    service = BlueprintReviewService(repositories)

    review_result = service.markReadyForCustomerReview(
        blueprint_id,
        reviewer_user_id="demo_workflow_analyst",
        reviewer_notes="Looks safe to share.",
        current_time_ms=CURRENT_TIME_MS + 1,
    )
    assert review_result.ok is True
    assert review_result.blueprint is not None
    assert review_result.blueprint.status == BlueprintStatus.READY_FOR_CUSTOMER_REVIEW
    assert review_result.blueprint.internal_reviewer_notes == "Looks safe to share."
    reviewed_project = repositories.workflow_project_repo.getRecord(
        review_result.blueprint.project_id
    )
    assert reviewed_project is not None
    assert reviewed_project.status == ProjectStatus.BLUEPRINT_READY_FOR_CUSTOMER_REVIEW

    customer_safe_view = service.createCustomerSafeView(review_result.blueprint)
    assert "prompt_version" not in customer_safe_view
    assert "model" not in customer_safe_view
    assert "raw_response_ref" not in customer_safe_view
    assert "internal_reviewer_notes" not in customer_safe_view

    approval_result = service.approveBlueprint(
        blueprint_id,
        approver_user_id="demo_client_stakeholder",
        current_time_ms=CURRENT_TIME_MS + 2,
    )
    assert approval_result.ok is True
    assert approval_result.blueprint is not None
    assert approval_result.blueprint.status == BlueprintStatus.APPROVED
    assert approval_result.blueprint.customer_approval_status == ApprovalStatus.APPROVED
    approved_project = repositories.workflow_project_repo.getRecord(
        review_result.blueprint.project_id
    )
    assert approved_project is not None
    assert approved_project.status == ProjectStatus.BLUEPRINT_APPROVED
    assert approved_project.approved_blueprint_id == blueprint_id


def test_blueprintReviewServiceRequestsChangesAndRequiresComment() -> None:
    """
    Verifies change requests require a note and update project status.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    blueprint_id = createReadyBlueprint(repositories)
    service = BlueprintReviewService(repositories)

    empty_result = service.requestBlueprintChanges(
        blueprint_id,
        requester_user_id="demo_customer_contact",
        change_note="  ",
        current_time_ms=CURRENT_TIME_MS + 2,
    )
    change_result = service.requestBlueprintChanges(
        blueprint_id,
        requester_user_id="demo_customer_contact",
        change_note="Add reporting detail.",
        current_time_ms=CURRENT_TIME_MS + 3,
    )

    assert empty_result.ok is False
    assert empty_result.status_code == 400
    assert empty_result.errors == ("Change note is required.",)
    assert change_result.ok is True
    assert change_result.blueprint is not None
    assert change_result.blueprint.status == BlueprintStatus.CHANGES_REQUESTED
    assert change_result.blueprint.customer_visible_notes == "Add reporting detail."
    project = repositories.workflow_project_repo.getRecord(change_result.blueprint.project_id)
    assert project is not None
    assert project.status == ProjectStatus.BLUEPRINT_CHANGES_REQUESTED


def test_blueprintReviewServiceHandlesMissingAndInvalidStatuses() -> None:
    """
    Verifies missing and invalid-status review requests fail safely.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    service = BlueprintReviewService(repositories)
    blueprint_id = createDraftBlueprint(repositories)

    missing_result = service.markReadyForCustomerReview("missing", reviewer_user_id="user")
    draft_approval_result = service.approveBlueprint(blueprint_id, approver_user_id="user")
    draft_change_result = service.requestBlueprintChanges(
        blueprint_id,
        requester_user_id="user",
        change_note="Change please.",
    )
    draft_blueprint = repositories.blueprint_repo.getRecord(blueprint_id)
    assert draft_blueprint is not None
    repositories.blueprint_repo.updateRecord(
        replace(draft_blueprint, status=BlueprintStatus.APPROVED)
    )
    invalid_review_result = service.markReadyForCustomerReview(
        blueprint_id, reviewer_user_id="user"
    )

    assert missing_result.status_code == 404
    assert draft_approval_result.status_code == 409
    assert draft_change_result.status_code == 409
    assert invalid_review_result.status_code == 409


def createDraftBlueprint(repositories: AppRepositories) -> str:
    """
    Creates a generated blueprint awaiting internal review.

    Args:
        repositories: Repository bundle.

    Returns:
        Blueprint id.
    """
    intake_result = IntakeService(repositories).createPublicIntake(
        createValidIntakePayload(),
        current_time_ms=CURRENT_TIME_MS,
    )
    assert intake_result.project is not None
    generation_result = BlueprintAiService(repositories).generateBlueprintForProject(
        intake_result.project.id,
        actor_user_id="demo_workflow_analyst",
        current_time_ms=CURRENT_TIME_MS,
    )
    assert generation_result.blueprint is not None
    return generation_result.blueprint.id


def createReadyBlueprint(repositories: AppRepositories) -> str:
    """
    Creates a blueprint ready for customer review.

    Args:
        repositories: Repository bundle.

    Returns:
        Blueprint id.
    """
    blueprint_id = createDraftBlueprint(repositories)
    result = BlueprintReviewService(repositories).markReadyForCustomerReview(
        blueprint_id,
        reviewer_user_id="demo_workflow_analyst",
        current_time_ms=CURRENT_TIME_MS + 1,
    )
    assert result.ok is True
    return blueprint_id
