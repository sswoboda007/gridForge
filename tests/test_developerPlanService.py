# -*- coding: utf-8 -*-
# tests/test_developerPlanService.py
"""
Tests GridForge developer-plan service behavior.

The tests verify developer-plan generation after blueprint approval, validation
failure handling, technical review approval/blocking, project state updates, and
audit events.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
import json

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import DeveloperPlanStatus, ProjectStatus
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.blueprintAiService import BlueprintAiService
from gridforge.services.blueprintReviewService import BlueprintReviewService
from gridforge.services.developerPlanService import (
    DeveloperPlanGeneratorResponse,
    DeveloperPlanService,
)
from gridforge.services.intakeService import IntakeService
from tests.fakes import createFakeRepositories
from tests.test_developerPlanValidationService import createValidDeveloperPlanContent
from tests.test_intakeService import createValidIntakePayload

CURRENT_TIME_MS = 1000


class InvalidDeveloperPlanGenerator:
    """
    Returns invalid developer-plan content for tests.
    """

    def generateDeveloperPlan(
        self,
        prompt_text: str,
        model: str,
    ) -> DeveloperPlanGeneratorResponse:
        """
        Generates invalid developer-plan output.

        Args:
            prompt_text: Prompt text.
            model: Model identifier.

        Returns:
            DeveloperPlanGeneratorResponse with invalid route specs.
        """
        _ = prompt_text
        content = createValidDeveloperPlanContent()
        content["routeSpecs"] = [{"method": "GET"}]
        return DeveloperPlanGeneratorResponse(
            raw_text=json.dumps(content),
            model=model,
            raw_response_ref="raw_invalid_developer_plan",
        )


def test_developerPlanServiceGeneratesAfterApprovedBlueprintAndQueuesReview() -> None:
    """
    Verifies generation creates an internal plan and queues technical review.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    blueprint_id = createApprovedBlueprint(repositories)

    result = DeveloperPlanService(repositories).generateDeveloperPlanForBlueprint(
        blueprint_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 3,
    )

    assert result.ok is True
    assert result.status_code == 201
    assert result.developer_plan is not None
    assert result.developer_plan.status == DeveloperPlanStatus.NEEDS_TECHNICAL_REVIEW
    assert result.developer_plan.prompt_version == "developer-plan-v3"
    assert result.developer_plan.validation_status == "validated"
    assert result.developer_plan.implementation_slices_json[0]["name"] == "Developer plan workflow"
    project = repositories.workflow_project_repo.getRecord(result.developer_plan.project_id)
    assert project is not None
    assert project.status == ProjectStatus.DEVELOPER_PLAN_NEEDS_REVIEW
    assert project.active_developer_plan_id == result.developer_plan.id
    assert result.audit_events[0].event_type == "developer_plan_generated"
    assert result.audit_events[1].event_type == "developer_plan_review_queued"


def test_developerPlanServiceRejectsBlueprintBeforeApproval() -> None:
    """
    Verifies generation is blocked before customer blueprint approval.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    blueprint_id = createReadyBlueprint(repositories)

    result = DeveloperPlanService(repositories).generateDeveloperPlanForBlueprint(
        blueprint_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 2,
    )

    assert result.ok is False
    assert result.status_code == 409
    assert result.errors == ("Blueprint must be approved before developer-plan generation.",)
    assert repositories.developer_plan_repo.listRecords() == ()


def test_developerPlanServiceRejectsInvalidGeneratedContent() -> None:
    """
    Verifies invalid generated plan content is rejected before storage.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    blueprint_id = createApprovedBlueprint(repositories)

    result = DeveloperPlanService(
        repositories,
        generator=InvalidDeveloperPlanGenerator(),
    ).generateDeveloperPlanForBlueprint(
        blueprint_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 3,
    )

    assert result.ok is False
    assert result.status_code == 422
    assert "routeSpecs[0] must include route." in result.errors
    assert repositories.developer_plan_repo.listRecords() == ()


def test_developerPlanServiceApprovesAndBlocksTechnicalReview() -> None:
    """
    Verifies developer-plan review actions update plan/project state.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    first_plan_id = createDeveloperPlan(repositories)
    service = DeveloperPlanService(repositories)

    missing_reason_result = service.reviewDeveloperPlan(
        first_plan_id,
        action="block",
        reviewer_user_id="demo_developer",
        blocker_reason=" ",
        current_time_ms=CURRENT_TIME_MS + 4,
    )
    blocked_result = service.reviewDeveloperPlan(
        first_plan_id,
        action="block",
        reviewer_user_id="demo_developer",
        blocker_reason="Confirm deployment target.",
        current_time_ms=CURRENT_TIME_MS + 5,
    )
    second_plan_id = createDeveloperPlan(repositories)
    approved_result = service.reviewDeveloperPlan(
        second_plan_id,
        action="approve",
        reviewer_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 6,
    )
    unsupported_result = service.reviewDeveloperPlan(
        second_plan_id,
        action="ship",
        reviewer_user_id="demo_developer",
    )

    assert missing_reason_result.status_code == 400
    assert blocked_result.developer_plan is not None
    assert blocked_result.developer_plan.status == DeveloperPlanStatus.BLOCKED
    assert "Confirm deployment target." in blocked_result.developer_plan.blocking_questions_json
    assert approved_result.developer_plan is not None
    assert approved_result.developer_plan.status == DeveloperPlanStatus.APPROVED
    project = repositories.workflow_project_repo.getRecord(
        approved_result.developer_plan.project_id
    )
    assert project is not None
    assert project.status == ProjectStatus.DEVELOPER_PLAN_APPROVED
    assert unsupported_result.status_code == 400


def createDeveloperPlan(repositories: AppRepositories) -> str:
    """
    Creates a developer plan awaiting technical review.

    Args:
        repositories: Repository bundle.

    Returns:
        Developer plan id.
    """
    blueprint_id = createApprovedBlueprint(repositories)
    result = DeveloperPlanService(repositories).generateDeveloperPlanForBlueprint(
        blueprint_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 3,
    )
    assert result.developer_plan is not None
    return result.developer_plan.id


def createApprovedBlueprint(repositories: AppRepositories) -> str:
    """
    Creates an approved customer blueprint.

    Args:
        repositories: Repository bundle.

    Returns:
        Approved blueprint id.
    """
    blueprint_id = createReadyBlueprint(repositories)
    approval_result = BlueprintReviewService(repositories).approveBlueprint(
        blueprint_id,
        approver_user_id="demo_client_stakeholder",
        current_time_ms=CURRENT_TIME_MS + 2,
    )
    assert approval_result.ok is True
    return blueprint_id


def createReadyBlueprint(repositories: AppRepositories) -> str:
    """
    Creates a blueprint ready for customer approval.

    Args:
        repositories: Repository bundle.

    Returns:
        Ready blueprint id.
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
    review_result = BlueprintReviewService(repositories).markReadyForCustomerReview(
        generation_result.blueprint.id,
        reviewer_user_id="demo_workflow_analyst",
        current_time_ms=CURRENT_TIME_MS + 1,
    )
    assert review_result.ok is True
    return generation_result.blueprint.id
