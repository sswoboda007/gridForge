# -*- coding: utf-8 -*-
# gridforge/services/blueprintAiService.py
"""
Generates customer-facing blueprint drafts for GridForge.

The service uses an injectable AI client interface, defaults to a deterministic
fake client, validates generated JSON, stores customer-safe blueprint records, and
logs AI request metadata without storing raw prompts or responses in customer data.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass, replace
import json
from typing import Any, Protocol

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import BlueprintStatus, ProjectStatus, UserRole
from gridforge.domain.records import AiRequestLog, AuditEvent, CustomerBlueprint
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import AuditService, createRecordId, currentTimeMs
from gridforge.services.blueprintPromptService import BlueprintPromptService
from gridforge.services.blueprintValidationService import BlueprintValidationService

DEFAULT_BLUEPRINT_MODEL = "fake-customer-blueprint-v1"


@dataclass(frozen=True)
class BlueprintAiResponse:
    """
    Represents a customer-blueprint AI client response.

    Args:
        raw_text: Raw AI response text.
        model: Model identifier.
        raw_response_ref: Internal raw response reference.
        token_input: Input token count.
        token_output: Output token count.
        cost_estimate_cents: Estimated request cost in cents.
    """

    raw_text: str
    model: str
    raw_response_ref: str
    token_input: int = 0
    token_output: int = 0
    cost_estimate_cents: int = 0


@dataclass(frozen=True)
class BlueprintGenerationResult:
    """
    Stores the outcome of blueprint generation.

    Args:
        ok: Whether a valid blueprint was created.
        status_code: HTTP-friendly status code.
        errors: Internal validation or guard errors.
        blueprint: Created blueprint when generation succeeds.
        ai_request_log: AI request metadata log.
        audit_events: Created audit events.
    """

    ok: bool
    status_code: int
    errors: tuple[str, ...]
    blueprint: CustomerBlueprint | None = None
    ai_request_log: AiRequestLog | None = None
    audit_events: tuple[AuditEvent, ...] = ()


class BlueprintAiClient(Protocol):
    """
    Describes the AI client boundary for customer blueprint generation.
    """

    def generateCustomerBlueprint(self, prompt_text: str, model: str) -> BlueprintAiResponse:
        """
        Generates raw customer blueprint content.

        Args:
            prompt_text: Prompt text for generation.
            model: Model identifier.

        Returns:
            BlueprintAiResponse from the client.
        """
        ...


class FakeBlueprintAiClient:
    """
    Provides deterministic customer blueprint output for tests and local demo.
    """

    def generateCustomerBlueprint(self, prompt_text: str, model: str) -> BlueprintAiResponse:
        """
        Generates deterministic customer-safe blueprint JSON.

        Args:
            prompt_text: Prompt text for generation.
            model: Model identifier.

        Returns:
            Deterministic BlueprintAiResponse.
        """
        prompt_payload = json.loads(prompt_text)
        project = prompt_payload["project"]
        app_name = f"{project['workflowType']} Command Center"
        content = {
            "appNameIdeas": [app_name, "Workflow Command Cloud"],
            "appSummary": f"A private workflow system for {project['projectName']}.",
            "problemBeingSolved": project["painfulWorkflowDescription"],
            "targetUsers": [
                {"role": "Customer Contact", "goal": "Submit workflow context and review status."},
                {"role": "Workflow Analyst", "goal": "Review blueprint readiness and risks."},
            ],
            "authorityMatrix": [
                {
                    "role": "Customer Contact",
                    "permissions": ["view_shared_blueprint", "request_changes"],
                },
                {
                    "role": "Workflow Analyst",
                    "permissions": ["generate_blueprint", "approve_for_customer_review"],
                },
            ],
            "mainWorkflows": [
                {
                    "name": "Intake to Blueprint",
                    "steps": ["capture intake", "review gaps", "share blueprint"],
                }
            ],
            "recommendedPages": [
                {"name": "Customer Status", "purpose": "Show customer-safe project progress."},
                {"name": "Internal Review Queue", "purpose": "Track blueprints needing review."},
            ],
            "dataObjects": [
                {"name": "Customer Workflow Project", "purpose": "Track lifecycle and status."},
                {"name": "Customer Blueprint", "purpose": "Store customer-facing plan."},
            ],
            "reportsAndExports": ["Customer-safe blueprint summary", "Internal review queue"],
            "integrations": ["Configurable AI provider through server-side service boundary"],
            "mvpScope": ["Guided intake", "Customer-facing blueprint", "Human review gate"],
            "phaseTwoScope": ["Developer plan generation", "Implementation slices"],
            "laterScope": ["Durable authentication", "Advanced exports"],
            "risksAndUnknowns": list(project.get("riskFlags") or ["Scope requires human review"]),
            "followUpQuestions": list(
                prompt_payload["intake"].get("followUpQuestions") or ["Confirm the MVP cut line."]
            ),
            "suggestedBuildMilestones": [
                "Approve blueprint",
                "Draft developer plan",
                "Build MVP slice",
            ],
            "fitSummary": {
                "fit": "strong",
                "reason": (
                    "The workflow benefits from role-scoped intake, review, and status tracking."
                ),
            },
        }
        return BlueprintAiResponse(
            raw_text=json.dumps(content, sort_keys=True),
            model=model,
            raw_response_ref=createRecordId("raw_blueprint_response"),
            token_input=len(prompt_text.split()),
            token_output=len(json.dumps(content).split()),
            cost_estimate_cents=0,
        )


class BlueprintAiService:
    """
    Generates, validates, stores, and logs customer blueprint drafts.
    """

    def __init__(
        self,
        repositories: AppRepositories,
        ai_client: BlueprintAiClient | None = None,
    ) -> None:
        """
        Initializes the blueprint generation service.

        Args:
            repositories: Repository bundle used by generation workflow.
            ai_client: Optional AI client; defaults to deterministic fake client.

        Returns:
            None.
        """
        self._repositories = repositories
        self._ai_client = ai_client or FakeBlueprintAiClient()
        self._audit_service = AuditService(repositories.audit_event_repo)
        self._prompt_service = BlueprintPromptService()
        self._validation_service = BlueprintValidationService()

    def generateBlueprintForProject(
        self,
        project_id: str,
        actor_user_id: str | None,
        model: str = DEFAULT_BLUEPRINT_MODEL,
        current_time_ms: int | None = None,
    ) -> BlueprintGenerationResult:
        """
        Generates and stores a customer-facing blueprint draft.

        Args:
            project_id: Workflow project id.
            actor_user_id: Internal actor user id.
            model: Model identifier.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            BlueprintGenerationResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        project = self._repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            return BlueprintGenerationResult(
                ok=False, status_code=404, errors=("Project not found.",)
            )
        intakes = self._repositories.intake_repo.listByProject(project.id)
        if not intakes:
            return BlueprintGenerationResult(
                ok=False, status_code=409, errors=("Project has no intake.",)
            )
        intake = intakes[-1]
        if project.status != ProjectStatus.INTAKE_READY_FOR_BLUEPRINT:
            return BlueprintGenerationResult(
                ok=False,
                status_code=409,
                errors=("Project is not ready for blueprint generation.",),
            )
        if not intake.ai_consent_accepted:
            return BlueprintGenerationResult(
                ok=False,
                status_code=409,
                errors=("AI planning-draft consent is required.",),
            )

        prompt = self._prompt_service.buildCustomerBlueprintPrompt(project, intake)
        ai_response = self._ai_client.generateCustomerBlueprint(prompt.prompt_text, model)
        validation_result = self._validation_service.validateBlueprintText(ai_response.raw_text)
        ai_log = self.createAiRequestLog(
            project.organization_id,
            project.id,
            prompt.prompt_version,
            ai_response,
            "validated" if validation_result.ok else "validation_failed",
            validation_result.errors,
            now_ms,
        )
        if not validation_result.ok:
            return BlueprintGenerationResult(
                ok=False,
                status_code=422,
                errors=validation_result.errors,
                ai_request_log=ai_log,
            )

        content = validation_result.content
        blueprint = createBlueprintFromValidatedContent(
            content,
            organization_id=project.organization_id,
            project_id=project.id,
            intake_id=intake.id,
            prompt_version=prompt.prompt_version,
            model=ai_response.model,
            raw_response_ref=ai_response.raw_response_ref,
            current_time_ms=now_ms,
        )
        self._repositories.blueprint_repo.createRecord(blueprint)
        updated_project = replace(
            project,
            status=ProjectStatus.BLUEPRINT_NEEDS_INTERNAL_REVIEW,
            next_action="Review customer blueprint draft",
            next_action_owner_role=UserRole.WORKFLOW_ANALYST,
            updated_at_ms=now_ms,
            last_activity_at_ms=now_ms,
        )
        self._repositories.workflow_project_repo.updateRecord(updated_project)
        generated_event = self._audit_service.recordEvent(
            event_type="blueprint_generated",
            organization_id=project.organization_id,
            project_id=project.id,
            record_type="CustomerBlueprint",
            record_id=blueprint.id,
            safe_summary="Customer blueprint draft generated.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.WORKFLOW_ANALYST,
            customer_visible=False,
            before_after_json={"projectStatus": updated_project.status.value},
            current_time_ms=now_ms,
        )
        queued_event = self._audit_service.recordEvent(
            event_type="blueprint_review_queued",
            organization_id=project.organization_id,
            project_id=project.id,
            record_type="CustomerBlueprint",
            record_id=blueprint.id,
            safe_summary="Blueprint queued for internal review.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.WORKFLOW_ANALYST,
            customer_visible=False,
            before_after_json={"blueprintStatus": blueprint.status.value},
            current_time_ms=now_ms,
        )
        return BlueprintGenerationResult(
            ok=True,
            status_code=201,
            errors=(),
            blueprint=blueprint,
            ai_request_log=ai_log,
            audit_events=(generated_event, queued_event),
        )

    def createAiRequestLog(
        self,
        organization_id: str,
        project_id: str,
        prompt_version: str,
        ai_response: BlueprintAiResponse,
        validation_status: str,
        validation_errors: tuple[str, ...],
        current_time_ms: int,
    ) -> AiRequestLog:
        """
        Creates internal-only AI request metadata.

        Args:
            organization_id: Owning organization id.
            project_id: Owning project id.
            prompt_version: Prompt version.
            ai_response: AI client response metadata.
            validation_status: Validation outcome.
            validation_errors: Internal validation errors.
            current_time_ms: Timestamp for created/updated fields.

        Returns:
            Stored AiRequestLog.
        """
        ai_log = AiRequestLog(
            id=createRecordId("ai_log"),
            organization_id=organization_id,
            project_id=project_id,
            request_type="customer_blueprint",
            prompt_version=prompt_version,
            model=ai_response.model,
            status="complete",
            raw_prompt_ref=createRecordId("raw_blueprint_prompt"),
            raw_response_ref=ai_response.raw_response_ref,
            token_input=ai_response.token_input,
            token_output=ai_response.token_output,
            cost_estimate_cents=ai_response.cost_estimate_cents,
            validation_status=validation_status,
            error_summary="; ".join(validation_errors),
            created_at_ms=current_time_ms,
            updated_at_ms=current_time_ms,
        )
        return self._repositories.ai_request_log_repo.createRecord(ai_log)


def createBlueprintFromValidatedContent(
    content: dict[str, object],
    *,
    organization_id: str,
    project_id: str,
    intake_id: str,
    prompt_version: str,
    model: str,
    raw_response_ref: str,
    current_time_ms: int,
) -> CustomerBlueprint:
    """
    Creates a CustomerBlueprint from validated content.

    Args:
        content: Validated customer blueprint content.
        organization_id: Owning organization id.
        project_id: Owning project id.
        intake_id: Source intake id.
        prompt_version: Prompt version.
        model: Model identifier.
        raw_response_ref: Internal raw response reference.
        current_time_ms: Timestamp for created/updated fields.

    Returns:
        CustomerBlueprint domain record.
    """
    app_name_ideas = asStringTuple(content["appNameIdeas"])
    fit_summary = asDict(content["fitSummary"])
    return CustomerBlueprint(
        id=createRecordId("blueprint"),
        organization_id=organization_id,
        project_id=project_id,
        intake_id=intake_id,
        status=BlueprintStatus.NEEDS_INTERNAL_REVIEW,
        title=firstString(app_name_ideas),
        app_name_ideas=app_name_ideas,
        app_summary=str(content["appSummary"]),
        problem_being_solved=str(content["problemBeingSolved"]),
        target_users_json=asDictTuple(content["targetUsers"]),
        authority_matrix_json=asDictTuple(content["authorityMatrix"]),
        main_workflows_json=asDictTuple(content["mainWorkflows"]),
        recommended_pages_json=asDictTuple(content["recommendedPages"]),
        data_objects_json=asDictTuple(content["dataObjects"]),
        reports_and_exports_json=asNamedDictTuple(content["reportsAndExports"]),
        integrations_json=asNamedDictTuple(content["integrations"]),
        mvp_scope_json=asStringTuple(content["mvpScope"]),
        phase_two_scope_json=asStringTuple(content["phaseTwoScope"]),
        later_scope_json=asStringTuple(content["laterScope"]),
        risks_and_unknowns_json=asStringTuple(content["risksAndUnknowns"]),
        follow_up_questions_json=asStringTuple(content["followUpQuestions"]),
        suggested_build_milestones_json=asStringTuple(content["suggestedBuildMilestones"]),
        fit_summary_json=fit_summary,
        complexity_summary=str(fit_summary.get("reason", "Human review required.")),
        prompt_version=prompt_version,
        model=model,
        raw_response_ref=raw_response_ref,
        validation_status="validated",
        generated_at_ms=current_time_ms,
        created_at_ms=current_time_ms,
        updated_at_ms=current_time_ms,
    )


def firstString(value: tuple[str, ...]) -> str:
    """
    Extracts the first string from a validated list value.

    Args:
        value: Validated string tuple.

    Returns:
        First string value.
    """
    if value:
        return value[0]
    return "Customer Workflow Blueprint"


def asStringTuple(value: object) -> tuple[str, ...]:
    """
    Converts a validated list value into a string tuple.

    Args:
        value: Validated list-like value.

    Returns:
        Tuple of string values.
    """
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def asDictTuple(value: object) -> tuple[dict[str, Any], ...]:
    """
    Converts a validated list of objects into a dict tuple.

    Args:
        value: Validated list-like value.

    Returns:
        Tuple of dictionary values.
    """
    if not isinstance(value, list):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, dict))


def asNamedDictTuple(value: object) -> tuple[dict[str, str], ...]:
    """
    Converts a validated list into simple name dictionaries.

    Args:
        value: Validated list-like value.

    Returns:
        Tuple of name dictionaries.
    """
    if not isinstance(value, list):
        return ()
    return tuple({"name": str(item)} for item in value)


def asDict(value: object) -> dict[str, Any]:
    """
    Converts a validated object into a dictionary.

    Args:
        value: Validated object value.

    Returns:
        Dictionary value.
    """
    if isinstance(value, dict):
        return dict(value)
    return {}
