# -*- coding: utf-8 -*-
# gridforge/services/developerPlanService.py
"""
Generates and reviews internal developer plans for GridForge.

The service creates developer-only implementation plans after customer blueprint
approval, validates required technical sections, updates project lifecycle state,
and creates audit events without exposing developer-plan content to customer
routes.

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
from gridforge.domain.enums import (
    ApprovalStatus,
    BlueprintStatus,
    DeveloperPlanStatus,
    ProjectStatus,
    UserRole,
)
from gridforge.domain.records import AuditEvent, DeveloperPlan, JsonObject
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import AuditService, createRecordId, currentTimeMs
from gridforge.services.developerPlanPromptService import DeveloperPlanPromptService
from gridforge.services.developerPlanValidationService import DeveloperPlanValidationService

DEFAULT_DEVELOPER_PLAN_MODEL = "deterministic-developer-plan-v1"


@dataclass(frozen=True)
class DeveloperPlanGeneratorResponse:
    """
    Represents deterministic developer-plan generator output.

    Args:
        raw_text: Raw generated developer-plan JSON text.
        model: Generator/model identifier.
        raw_response_ref: Internal raw response reference.
    """

    raw_text: str
    model: str
    raw_response_ref: str


@dataclass(frozen=True)
class DeveloperPlanResult:
    """
    Stores the outcome of developer-plan actions.

    Args:
        ok: Whether the action succeeded.
        status_code: HTTP-friendly status code.
        errors: Validation or guard errors.
        developer_plan: Developer plan when successful.
        audit_events: Audit events created by the action.
    """

    ok: bool
    status_code: int
    errors: tuple[str, ...]
    developer_plan: DeveloperPlan | None = None
    audit_events: tuple[AuditEvent, ...] = ()


class DeveloperPlanGenerator(Protocol):
    """
    Describes the deterministic generator boundary for developer plans.
    """

    def generateDeveloperPlan(
        self,
        prompt_text: str,
        model: str,
    ) -> DeveloperPlanGeneratorResponse:
        """
        Generates internal developer-plan content.

        Args:
            prompt_text: Internal prompt text.
            model: Generator/model identifier.

        Returns:
            DeveloperPlanGeneratorResponse.
        """
        ...


class FakeDeveloperPlanGenerator:
    """
    Provides deterministic internal developer-plan content for tests/local demo.
    """

    def generateDeveloperPlan(
        self,
        prompt_text: str,
        model: str,
    ) -> DeveloperPlanGeneratorResponse:
        """
        Generates deterministic developer-plan JSON from blueprint context.

        Args:
            prompt_text: Internal prompt text.
            model: Generator/model identifier.

        Returns:
            DeveloperPlanGeneratorResponse.
        """
        prompt_payload = json.loads(prompt_text)
        project = prompt_payload["project"]
        blueprint = prompt_payload["blueprint"]
        plan_content = {
            "implementationOverview": (
                f"Build {project['projectName']} as a private workflow operating system "
                f"based on the approved blueprint '{blueprint['title']}'."
            ),
            "mvpCutLine": {
                "included": list(blueprint["mvpScope"]),
                "excluded": ["native mobile", "payments", "advanced public publishing"],
                "decisionRule": "Keep only role-scoped workflow operations needed for MVP handoff.",
            },
            "entitySpecs": [
                {
                    "name": "CustomerWorkflowProject",
                    "purpose": "Track lifecycle, assignments, and status.",
                    "fields": ["id", "organization_id", "status", "active_developer_plan_id"],
                },
                {
                    "name": "DeveloperPlan",
                    "purpose": "Store private implementation specs.",
                    "fields": ["blueprint_id", "route_specs_json", "implementation_slices_json"],
                },
            ],
            "routeSpecs": [
                {
                    "method": "GET",
                    "route": "/developer/plans/<developer_plan_id>",
                    "auth": "Platform Admin, Developer, or QA Reviewer",
                    "errorCases": ["403 customer access", "404 missing plan"],
                    "tests": ["developer 200", "customer 403"],
                },
                {
                    "method": "POST",
                    "route": "/developer/plans/<developer_plan_id>/review",
                    "auth": "Platform Admin or Developer",
                    "errorCases": ["400 unsupported action", "409 invalid status"],
                    "tests": ["approve updates project", "block requires reason"],
                },
            ],
            "authorizationPolicies": [
                {
                    "role": "Developer",
                    "scope": "internal project",
                    "rules": ["can view developer plan", "can approve or block technical review"],
                },
                {
                    "role": "Customer Contact",
                    "scope": "customer project",
                    "rules": ["cannot view developer plan", "cannot view internal specs"],
                },
            ],
            "stateMachines": [
                {
                    "name": "Developer plan review",
                    "states": ["needs_technical_review", "approved", "blocked"],
                }
            ],
            "validationRules": [
                "Developer plan requires approved customer blueprint.",
                "Route specs must include method, route, auth, error cases, and tests.",
            ],
            "queryAndIndexSpecs": [
                {"name": "developerPlansByProject", "fields": ["project_id", "status"]}
            ],
            "dashboardMetricSpecs": [
                {"name": "plans_needing_review", "source": "developer_plan.status"}
            ],
            "csvExportSpecs": [
                {
                    "name": "Internal developer plan export",
                    "columns": ["id", "project_id", "status", "implementation_overview"],
                    "roleAccess": ["platform_admin", "developer"],
                    "auditEvent": "developer_plan_exported",
                }
            ],
            "testPlan": {
                "unit": ["developer plan validation", "developer plan service"],
                "route": ["generation guard", "developer-only detail", "review action"],
                "liveSmoke": ["generate", "view", "approve"],
            },
            "dataLifecycleRules": [
                "Developer plans are internal-only and superseded by new plans."
            ],
            "auditEvents": ["developer_plan_generated", "developer_plan_approved"],
            "securityPrivacyNotes": [
                "Never expose developer-plan content to customer routes.",
                "Keep prompt versions and raw refs internal-only.",
            ],
            "failureModes": [
                {"mode": "Blueprint not approved", "response": "409 and no developer plan"},
                {"mode": "Validation failure", "response": "422 and internal errors"},
            ],
            "operationalNotes": ["Create implementation slices only after technical approval."],
            "implementationSlices": [
                {
                    "name": "Developer plan workflow",
                    "goal": "Generate and review internal implementation plan.",
                    "acceptanceCriteria": ["customer 403", "developer detail visible"],
                },
                {
                    "name": "Implementation slices workflow",
                    "goal": "Create build slices from approved developer plan.",
                    "acceptanceCriteria": ["slices derive from approved plan"],
                },
            ],
            "blockingQuestions": ["Confirm repository and deployment target before build starts."],
            "deferredQuestions": ["Which exports are needed after MVP approval?"],
            "developerMilestones": [
                "Approve developer plan",
                "Create build slices",
                "Start MVP build",
            ],
        }
        return DeveloperPlanGeneratorResponse(
            raw_text=json.dumps(plan_content, sort_keys=True),
            model=model,
            raw_response_ref=createRecordId("raw_developer_plan_response"),
        )


class DeveloperPlanService:
    """
    Generates and reviews internal developer plans.
    """

    def __init__(
        self,
        repositories: AppRepositories,
        generator: DeveloperPlanGenerator | None = None,
    ) -> None:
        """
        Initializes the developer-plan service.

        Args:
            repositories: Repository bundle used by the workflow.
            generator: Optional deterministic generator override for tests.

        Returns:
            None.
        """
        self._repositories = repositories
        self._generator = generator or FakeDeveloperPlanGenerator()
        self._audit_service = AuditService(repositories.audit_event_repo)
        self._prompt_service = DeveloperPlanPromptService()
        self._validation_service = DeveloperPlanValidationService()

    def generateDeveloperPlanForBlueprint(
        self,
        blueprint_id: str,
        actor_user_id: str | None,
        model: str = DEFAULT_DEVELOPER_PLAN_MODEL,
        current_time_ms: int | None = None,
    ) -> DeveloperPlanResult:
        """
        Generates a validated internal developer plan from an approved blueprint.

        Args:
            blueprint_id: Approved customer blueprint id.
            actor_user_id: Internal actor user id.
            model: Generator/model identifier.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            DeveloperPlanResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        blueprint = self._repositories.blueprint_repo.getRecord(blueprint_id)
        if blueprint is None:
            return DeveloperPlanResult(ok=False, status_code=404, errors=("Blueprint not found.",))
        if blueprint.status != BlueprintStatus.APPROVED:
            return DeveloperPlanResult(
                ok=False,
                status_code=409,
                errors=("Blueprint must be approved before developer-plan generation.",),
            )
        project = self._repositories.workflow_project_repo.getRecord(blueprint.project_id)
        if project is None:
            return DeveloperPlanResult(ok=False, status_code=409, errors=("Project not found.",))
        prompt = self._prompt_service.buildDeveloperPlanPrompt(project, blueprint)
        generated_response = self._generator.generateDeveloperPlan(prompt.prompt_text, model)
        validation_result = self._validation_service.validateDeveloperPlanText(
            generated_response.raw_text
        )
        if not validation_result.ok:
            return DeveloperPlanResult(
                ok=False,
                status_code=422,
                errors=validation_result.errors,
            )
        developer_plan = createDeveloperPlanFromValidatedContent(
            validation_result.content,
            organization_id=blueprint.organization_id,
            project_id=blueprint.project_id,
            blueprint_id=blueprint.id,
            prompt_version=prompt.prompt_version,
            model=generated_response.model,
            raw_response_ref=generated_response.raw_response_ref,
            current_time_ms=now_ms,
        )
        self._repositories.developer_plan_repo.createRecord(developer_plan)
        updated_project = replace(
            project,
            status=ProjectStatus.DEVELOPER_PLAN_NEEDS_REVIEW,
            active_developer_plan_id=developer_plan.id,
            next_action="Review developer implementation plan",
            next_action_owner_role=UserRole.DEVELOPER,
            updated_at_ms=now_ms,
            last_activity_at_ms=now_ms,
        )
        self._repositories.workflow_project_repo.updateRecord(updated_project)
        generated_event = self._audit_service.recordEvent(
            event_type="developer_plan_generated",
            organization_id=developer_plan.organization_id,
            project_id=developer_plan.project_id,
            record_type="DeveloperPlan",
            record_id=developer_plan.id,
            safe_summary="Internal developer plan generated.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.DEVELOPER,
            customer_visible=False,
            before_after_json={"developerPlanStatus": developer_plan.status.value},
            current_time_ms=now_ms,
        )
        queued_event = self._audit_service.recordEvent(
            event_type="developer_plan_review_queued",
            organization_id=developer_plan.organization_id,
            project_id=developer_plan.project_id,
            record_type="DeveloperPlan",
            record_id=developer_plan.id,
            safe_summary="Developer plan queued for technical review.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.DEVELOPER,
            customer_visible=False,
            before_after_json={"projectStatus": updated_project.status.value},
            current_time_ms=now_ms,
        )
        return DeveloperPlanResult(
            ok=True,
            status_code=201,
            errors=(),
            developer_plan=developer_plan,
            audit_events=(generated_event, queued_event),
        )

    def reviewDeveloperPlan(
        self,
        developer_plan_id: str,
        action: str,
        reviewer_user_id: str | None,
        blocker_reason: str = "",
        current_time_ms: int | None = None,
    ) -> DeveloperPlanResult:
        """
        Approves or blocks a developer plan during technical review.

        Args:
            developer_plan_id: Developer plan id.
            action: Review action, either approve or block.
            reviewer_user_id: Internal reviewer user id.
            blocker_reason: Required reason when blocking.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            DeveloperPlanResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        developer_plan = self._repositories.developer_plan_repo.getRecord(developer_plan_id)
        if developer_plan is None:
            return DeveloperPlanResult(
                ok=False, status_code=404, errors=("Developer plan not found.",)
            )
        normalized_action = action.strip().lower()
        if normalized_action == "approve":
            return self.approveDeveloperPlan(developer_plan, reviewer_user_id, now_ms)
        if normalized_action == "block":
            return self.blockDeveloperPlan(developer_plan, reviewer_user_id, blocker_reason, now_ms)
        return DeveloperPlanResult(
            ok=False, status_code=400, errors=("Unsupported review action.",)
        )

    def approveDeveloperPlan(
        self,
        developer_plan: DeveloperPlan,
        reviewer_user_id: str | None,
        current_time_ms: int,
    ) -> DeveloperPlanResult:
        """
        Approves a developer plan and enables implementation-slice planning.

        Args:
            developer_plan: Developer plan under review.
            reviewer_user_id: Internal reviewer user id.
            current_time_ms: Timestamp for updates.

        Returns:
            DeveloperPlanResult.
        """
        if developer_plan.status != DeveloperPlanStatus.NEEDS_TECHNICAL_REVIEW:
            return DeveloperPlanResult(
                ok=False,
                status_code=409,
                errors=("Developer plan is not awaiting technical review.",),
            )
        updated_plan = replace(
            developer_plan,
            status=DeveloperPlanStatus.APPROVED,
            internal_approval_status=ApprovalStatus.APPROVED,
            technical_reviewer_user_id=reviewer_user_id,
            technical_reviewed_at_ms=current_time_ms,
            updated_at_ms=current_time_ms,
        )
        self._repositories.developer_plan_repo.updateRecord(updated_plan)
        self.updateProjectForDeveloperPlanApproval(updated_plan, current_time_ms)
        audit_event = self._audit_service.recordEvent(
            event_type="developer_plan_approved",
            organization_id=updated_plan.organization_id,
            project_id=updated_plan.project_id,
            record_type="DeveloperPlan",
            record_id=updated_plan.id,
            safe_summary="Developer plan approved for implementation slicing.",
            actor_user_id=reviewer_user_id,
            actor_role=UserRole.DEVELOPER,
            customer_visible=False,
            before_after_json={"developerPlanStatus": updated_plan.status.value},
            current_time_ms=current_time_ms,
        )
        return DeveloperPlanResult(
            ok=True,
            status_code=200,
            errors=(),
            developer_plan=updated_plan,
            audit_events=(audit_event,),
        )

    def blockDeveloperPlan(
        self,
        developer_plan: DeveloperPlan,
        reviewer_user_id: str | None,
        blocker_reason: str,
        current_time_ms: int,
    ) -> DeveloperPlanResult:
        """
        Blocks a developer plan with a required reason.

        Args:
            developer_plan: Developer plan under review.
            reviewer_user_id: Internal reviewer user id.
            blocker_reason: Required blocker reason.
            current_time_ms: Timestamp for updates.

        Returns:
            DeveloperPlanResult.
        """
        normalized_reason = blocker_reason.strip()
        if not normalized_reason:
            return DeveloperPlanResult(
                ok=False, status_code=400, errors=("Blocker reason is required.",)
            )
        if developer_plan.status != DeveloperPlanStatus.NEEDS_TECHNICAL_REVIEW:
            return DeveloperPlanResult(
                ok=False,
                status_code=409,
                errors=("Developer plan is not awaiting technical review.",),
            )
        updated_plan = replace(
            developer_plan,
            status=DeveloperPlanStatus.BLOCKED,
            internal_approval_status=ApprovalStatus.CHANGES_REQUESTED,
            blocking_questions_json=developer_plan.blocking_questions_json + (normalized_reason,),
            technical_reviewer_user_id=reviewer_user_id,
            technical_reviewed_at_ms=current_time_ms,
            updated_at_ms=current_time_ms,
        )
        self._repositories.developer_plan_repo.updateRecord(updated_plan)
        self.updateProjectForDeveloperPlanBlock(updated_plan, current_time_ms)
        audit_event = self._audit_service.recordEvent(
            event_type="developer_plan_blocked",
            organization_id=updated_plan.organization_id,
            project_id=updated_plan.project_id,
            record_type="DeveloperPlan",
            record_id=updated_plan.id,
            safe_summary="Developer plan blocked pending updates.",
            actor_user_id=reviewer_user_id,
            actor_role=UserRole.DEVELOPER,
            customer_visible=False,
            before_after_json={"developerPlanStatus": updated_plan.status.value},
            current_time_ms=current_time_ms,
        )
        return DeveloperPlanResult(
            ok=True,
            status_code=200,
            errors=(),
            developer_plan=updated_plan,
            audit_events=(audit_event,),
        )

    def updateProjectForDeveloperPlanApproval(
        self,
        developer_plan: DeveloperPlan,
        current_time_ms: int,
    ) -> None:
        """
        Updates project state after developer-plan approval.

        Args:
            developer_plan: Approved developer plan.
            current_time_ms: Timestamp for project update.

        Returns:
            None.
        """
        project = self._repositories.workflow_project_repo.getRecord(developer_plan.project_id)
        if project is None:
            return
        self._repositories.workflow_project_repo.updateRecord(
            replace(
                project,
                status=ProjectStatus.DEVELOPER_PLAN_APPROVED,
                active_developer_plan_id=developer_plan.id,
                next_action="Create implementation slices",
                next_action_owner_role=UserRole.DEVELOPER,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        )

    def updateProjectForDeveloperPlanBlock(
        self,
        developer_plan: DeveloperPlan,
        current_time_ms: int,
    ) -> None:
        """
        Updates project state after developer-plan blocker.

        Args:
            developer_plan: Blocked developer plan.
            current_time_ms: Timestamp for project update.

        Returns:
            None.
        """
        project = self._repositories.workflow_project_repo.getRecord(developer_plan.project_id)
        if project is None:
            return
        self._repositories.workflow_project_repo.updateRecord(
            replace(
                project,
                status=ProjectStatus.DEVELOPER_PLAN_NEEDS_REVIEW,
                active_developer_plan_id=developer_plan.id,
                next_action="Resolve developer plan blockers",
                next_action_owner_role=UserRole.DEVELOPER,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        )


def createDeveloperPlanFromValidatedContent(
    content: JsonObject,
    *,
    organization_id: str,
    project_id: str,
    blueprint_id: str,
    prompt_version: str,
    model: str,
    raw_response_ref: str,
    current_time_ms: int,
) -> DeveloperPlan:
    """
    Creates a DeveloperPlan from validated internal content.

    Args:
        content: Validated developer-plan content.
        organization_id: Owning organization id.
        project_id: Owning project id.
        blueprint_id: Approved blueprint id.
        prompt_version: Prompt version.
        model: Generator/model identifier.
        raw_response_ref: Internal raw response reference.
        current_time_ms: Timestamp for created/updated fields.

    Returns:
        DeveloperPlan domain record.
    """
    return DeveloperPlan(
        id=createRecordId("developer_plan"),
        organization_id=organization_id,
        project_id=project_id,
        blueprint_id=blueprint_id,
        status=DeveloperPlanStatus.NEEDS_TECHNICAL_REVIEW,
        implementation_overview=str(content["implementationOverview"]),
        mvp_cut_line_json=asDict(content["mvpCutLine"]),
        entity_specs_json=asDictTuple(content["entitySpecs"]),
        route_specs_json=asDictTuple(content["routeSpecs"]),
        authorization_policies_json=asDictTuple(content["authorizationPolicies"]),
        state_machines_json=asDictTuple(content["stateMachines"]),
        validation_rules_json=asStringTuple(content["validationRules"]),
        query_and_index_specs_json=asDictTuple(content["queryAndIndexSpecs"]),
        dashboard_metric_specs_json=asDictTuple(content["dashboardMetricSpecs"]),
        csv_export_specs_json=asDictTuple(content["csvExportSpecs"]),
        test_plan_json=asDict(content["testPlan"]),
        data_lifecycle_rules_json=asStringTuple(content["dataLifecycleRules"]),
        audit_events_json=asStringTuple(content["auditEvents"]),
        security_privacy_notes_json=asStringTuple(content["securityPrivacyNotes"]),
        failure_modes_json=asDictTuple(content["failureModes"]),
        operational_notes_json=asStringTuple(content["operationalNotes"]),
        implementation_slices_json=asDictTuple(content["implementationSlices"]),
        blocking_questions_json=asStringTuple(content["blockingQuestions"]),
        deferred_questions_json=asStringTuple(content["deferredQuestions"]),
        developer_milestones_json=asStringTuple(content["developerMilestones"]),
        prompt_version=prompt_version,
        model=model,
        raw_response_ref=raw_response_ref,
        validation_status="validated",
        generated_at_ms=current_time_ms,
        created_at_ms=current_time_ms,
        updated_at_ms=current_time_ms,
    )


def createDeveloperPlanErrorPayload(result: DeveloperPlanResult) -> JsonObject:
    """
    Creates a JSON-safe developer-plan error payload.

    Args:
        result: Failed developer-plan result.

    Returns:
        Error payload.
    """
    return {"ok": False, "errors": list(result.errors)}


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
