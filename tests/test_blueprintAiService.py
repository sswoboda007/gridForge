# -*- coding: utf-8 -*-
# tests/test_blueprintAiService.py
"""
Tests GridForge customer blueprint generation service.

The tests verify deterministic fake AI generation, validation failure handling,
AI request logging, audit logging, and project state updates.

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
from gridforge.domain.enums import BlueprintStatus, ProjectStatus
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.blueprintAiService import BlueprintAiResponse, BlueprintAiService
from gridforge.services.intakeService import IntakeService
from tests.test_blueprintValidationService import createValidBlueprintContent
from tests.test_intakeService import createValidIntakePayload
from tests.fakes import createFakeRepositories

CURRENT_TIME_MS = 1000


class ForbiddenClaimBlueprintAiClient:
    """
    Returns forbidden customer-facing AI content for tests.
    """

    def generateCustomerBlueprint(self, prompt_text: str, model: str) -> BlueprintAiResponse:
        """
        Generates a forbidden-claim AI response.

        Args:
            prompt_text: Prompt text.
            model: Model identifier.

        Returns:
            BlueprintAiResponse containing invalid content.
        """
        _ = prompt_text
        content = createValidBlueprintContent()
        content["appSummary"] = "This is HIPAA compliant with a guaranteed timeline."
        return BlueprintAiResponse(
            raw_text=json.dumps(content),
            model=model,
            raw_response_ref="raw_forbidden",
        )


def test_blueprintAiServiceGeneratesValidatedBlueprintAndLogsEvents() -> None:
    """
    Verifies fake AI creates a validated internal-review blueprint draft.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id = createReadyProject(repositories)

    result = BlueprintAiService(repositories).generateBlueprintForProject(
        project_id,
        actor_user_id="demo_workflow_analyst",
        current_time_ms=CURRENT_TIME_MS,
    )

    assert result.ok is True
    assert result.status_code == 201
    assert result.blueprint is not None
    assert result.blueprint.status == BlueprintStatus.NEEDS_INTERNAL_REVIEW
    assert result.blueprint.validation_status == "validated"
    assert result.blueprint.prompt_version == "customer-blueprint-v1"
    assert result.ai_request_log is not None
    assert result.ai_request_log.validation_status == "validated"
    assert result.audit_events[0].event_type == "blueprint_generated"
    assert result.audit_events[1].event_type == "blueprint_review_queued"
    updated_project = repositories.workflow_project_repo.getRecord(project_id)
    assert updated_project is not None
    assert updated_project.status == ProjectStatus.BLUEPRINT_NEEDS_INTERNAL_REVIEW
    assert repositories.blueprint_repo.getRecord(result.blueprint.id) == result.blueprint


def test_blueprintAiServiceRejectsProjectsNotReadyForBlueprint() -> None:
    """
    Verifies generation is blocked when intake needs follow-up.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    payload = createValidIntakePayload()
    payload.pop("usersPermissions")
    payload.pop("workflowLifecycle")
    payload.pop("statuses")
    project_result = IntakeService(repositories).createPublicIntake(
        payload,
        current_time_ms=CURRENT_TIME_MS,
    )

    assert project_result.project is not None
    result = BlueprintAiService(repositories).generateBlueprintForProject(
        project_result.project.id,
        actor_user_id="demo_workflow_analyst",
        current_time_ms=CURRENT_TIME_MS,
    )

    assert result.ok is False
    assert result.status_code == 409
    assert result.errors == ("Project is not ready for blueprint generation.",)
    assert repositories.blueprint_repo.listRecords() == ()


def test_blueprintAiServiceRejectsForbiddenAiOutputButLogsMetadata() -> None:
    """
    Verifies forbidden AI output is rejected and internal metadata is logged.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id = createReadyProject(repositories)

    result = BlueprintAiService(
        repositories,
        ai_client=ForbiddenClaimBlueprintAiClient(),
    ).generateBlueprintForProject(
        project_id,
        actor_user_id="demo_workflow_analyst",
        current_time_ms=CURRENT_TIME_MS,
    )

    assert result.ok is False
    assert result.status_code == 422
    assert "Forbidden claim detected: hipaa compliant" in result.errors
    assert "Forbidden claim detected: guaranteed timeline" in result.errors
    assert result.ai_request_log is not None
    assert result.ai_request_log.validation_status == "validation_failed"
    assert repositories.blueprint_repo.listRecords() == ()


def createReadyProject(repositories: AppRepositories) -> str:
    """
    Creates a project ready for blueprint generation.

    Args:
        repositories: Repository bundle used by the intake service.

    Returns:
        Created project id.
    """
    result = IntakeService(repositories).createPublicIntake(
        createValidIntakePayload(),
        current_time_ms=CURRENT_TIME_MS,
    )

    assert result.project is not None
    assert result.project.status == ProjectStatus.INTAKE_READY_FOR_BLUEPRINT
    return result.project.id
