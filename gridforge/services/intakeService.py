# -*- coding: utf-8 -*-
# gridforge/services/intakeService.py
"""
Creates GridForge customer workflow projects from guided intake submissions.

The intake service validates public payloads, normalizes fields, creates the
organization/project/intake records, evaluates missing blueprint details, flags
fit risks, and records safe audit events.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass
import re
from typing import Any, Mapping

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import IntakeStatus, ProjectStatus, UserRole
from gridforge.domain.records import (
    AuditEvent,
    CustomerOrganization,
    CustomerWorkflowProject,
    IntakeResponse,
)
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import AuditService, createRecordId, currentTimeMs
from gridforge.services.missingDetailService import MissingDetailResult, MissingDetailService

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REQUIRED_FIELDS = (
    "organizationName",
    "primaryContactName",
    "primaryContactEmail",
    "workflowType",
    "workflowDescription",
)


@dataclass(frozen=True)
class IntakeCreationResult:
    """
    Stores the result of creating a public intake.

    Args:
        ok: Whether creation succeeded.
        status_code: HTTP-friendly status code.
        errors: Field-level validation errors.
        organization: Created organization when successful.
        project: Created project when successful.
        intake: Created intake when successful.
        audit_event: Created audit event when successful.
        missing_detail_result: Coverage/risk result when available.
    """

    ok: bool
    status_code: int
    errors: Mapping[str, str]
    organization: CustomerOrganization | None = None
    project: CustomerWorkflowProject | None = None
    intake: IntakeResponse | None = None
    audit_event: AuditEvent | None = None
    missing_detail_result: MissingDetailResult | None = None


class IntakeService:
    """
    Validates and creates customer workflow intake records.
    """

    def __init__(self, repositories: AppRepositories) -> None:
        """
        Initializes the service.

        Args:
            repositories: Repository bundle used for Phase 2 writes.

        Returns:
            None.
        """
        self._repositories = repositories
        self._audit_service = AuditService(repositories.audit_event_repo)
        self._missing_detail_service = MissingDetailService()

    def createPublicIntake(
        self,
        payload: Mapping[str, Any],
        current_time_ms: int | None = None,
    ) -> IntakeCreationResult:
        """
        Creates organization, project, intake, and audit records from public intake.

        Args:
            payload: Incoming intake payload from JSON or form data.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            IntakeCreationResult with created records or validation errors.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        normalized_payload = normalizeIntakePayload(payload)
        validation_errors = validateIntakePayload(normalized_payload)
        if validation_errors:
            return IntakeCreationResult(ok=False, status_code=400, errors=validation_errors)

        missing_detail_result = self._missing_detail_service.evaluateIntakeCoverage(
            normalized_payload
        )
        organization = createOrganizationFromPayload(normalized_payload, now_ms)
        project = createProjectFromPayload(
            normalized_payload, organization.id, missing_detail_result, now_ms
        )
        intake = createIntakeFromPayload(
            normalized_payload,
            organization.id,
            project.id,
            missing_detail_result,
            now_ms,
        )

        self._repositories.organization_repo.createRecord(organization)
        self._repositories.workflow_project_repo.createRecord(project)
        self._repositories.intake_repo.createRecord(intake)
        audit_event = self._audit_service.recordEvent(
            event_type="intake_submitted",
            organization_id=organization.id,
            project_id=project.id,
            record_type="IntakeResponse",
            record_id=intake.id,
            safe_summary=f"Intake submitted for {organization.organization_name}.",
            actor_role=UserRole.PUBLIC_VISITOR,
            customer_visible=False,
            before_after_json={
                "projectStatus": project.status.value,
                "intakeStatus": intake.status.value,
            },
            current_time_ms=now_ms,
        )

        return IntakeCreationResult(
            ok=True,
            status_code=201,
            errors={},
            organization=organization,
            project=project,
            intake=intake,
            audit_event=audit_event,
            missing_detail_result=missing_detail_result,
        )


def normalizeIntakePayload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    Normalizes supported intake payload fields.

    Args:
        payload: Raw request payload.

    Returns:
        Normalized payload with strings stripped and booleans coerced.
    """
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if key in {"aiConsentAccepted", "termsAccepted"}:
            normalized[key] = coerceBool(value)
        elif key == "currentTools":
            normalized[key] = normalizeStringTuple(value)
        else:
            normalized[key] = normalizeString(value)
    normalized.setdefault("currentTools", ())
    normalized.setdefault("aiConsentAccepted", False)
    normalized.setdefault("termsAccepted", False)
    return normalized


def validateIntakePayload(payload: Mapping[str, Any]) -> dict[str, str]:
    """
    Validates required public intake fields.

    Args:
        payload: Normalized payload.

    Returns:
        Field-level validation errors.
    """
    errors: dict[str, str] = {}
    for field_name in REQUIRED_FIELDS:
        if not normalizeString(payload.get(field_name)):
            errors[field_name] = "This field is required."
    email = normalizeString(payload.get("primaryContactEmail"))
    if email and EMAIL_PATTERN.match(email) is None:
        errors["primaryContactEmail"] = "Enter a valid email address."
    if not coerceBool(payload.get("aiConsentAccepted")):
        errors["aiConsentAccepted"] = "AI planning-draft consent is required."
    if not coerceBool(payload.get("termsAccepted")):
        errors["termsAccepted"] = "Planning-draft terms acknowledgement is required."
    return errors


def createOrganizationFromPayload(
    payload: Mapping[str, Any],
    current_time_ms: int,
) -> CustomerOrganization:
    """
    Creates a customer organization record from normalized payload.

    Args:
        payload: Normalized intake payload.
        current_time_ms: Timestamp for created/updated fields.

    Returns:
        CustomerOrganization domain record.
    """
    return CustomerOrganization(
        id=createRecordId("org"),
        organization_name=normalizeString(payload.get("organizationName")),
        primary_contact_name=normalizeString(payload.get("primaryContactName")),
        primary_contact_email=normalizeString(payload.get("primaryContactEmail")),
        status="lead",
        industry=normalizeString(payload.get("industry")),
        organization_size=normalizeString(payload.get("organizationSize")),
        website=normalizeString(payload.get("website")),
        primary_location=normalizeString(payload.get("primaryLocation")),
        time_zone=normalizeString(payload.get("timeZone")),
        primary_contact_phone=optionalString(payload.get("primaryContactPhone")),
        stakeholder_name=optionalString(payload.get("stakeholderName")),
        stakeholder_email=optionalString(payload.get("stakeholderEmail")),
        customer_visible_notes=normalizeString(payload.get("customerVisibleNotes")),
        internal_notes=normalizeString(payload.get("internalNotes")),
        created_at_ms=current_time_ms,
        updated_at_ms=current_time_ms,
    )


def createProjectFromPayload(
    payload: Mapping[str, Any],
    organization_id: str,
    missing_detail_result: MissingDetailResult,
    current_time_ms: int,
) -> CustomerWorkflowProject:
    """
    Creates a customer workflow project from normalized payload.

    Args:
        payload: Normalized intake payload.
        organization_id: Owning organization id.
        missing_detail_result: Intake coverage/risk result.
        current_time_ms: Timestamp for created/updated fields.

    Returns:
        CustomerWorkflowProject domain record.
    """
    project_status = ProjectStatus.INTAKE_READY_FOR_BLUEPRINT
    if missing_detail_result.missing_categories:
        project_status = ProjectStatus.INTAKE_NEEDS_FOLLOW_UP
    organization_name = normalizeString(payload.get("organizationName"))
    workflow_type = normalizeString(payload.get("workflowType"))
    return CustomerWorkflowProject(
        id=createRecordId("project"),
        organization_id=organization_id,
        project_name=f"{organization_name} — {workflow_type}",
        primary_contact_name=normalizeString(payload.get("primaryContactName")),
        primary_contact_email=normalizeString(payload.get("primaryContactEmail")),
        stakeholder_name=optionalString(payload.get("stakeholderName")),
        stakeholder_email=optionalString(payload.get("stakeholderEmail")),
        workflow_type=workflow_type,
        status=project_status,
        short_summary=normalizeString(payload.get("shortSummary")),
        painful_workflow_description=normalizeString(payload.get("workflowDescription")),
        current_tools=normalizeStringTuple(payload.get("currentTools")),
        delays_or_losses=normalizeString(payload.get("delaysOrLosses")),
        manual_reporting=normalizeString(payload.get("manualReporting")),
        desired_outcome=normalizeString(payload.get("desiredOutcome")),
        success_definition=normalizeString(payload.get("successDefinition")),
        urgency=normalizeString(payload.get("urgency")),
        budget_range=normalizeString(payload.get("budgetRange")),
        privacy_risk=normalizeString(payload.get("privacyRisk")) or "unknown",
        compliance_risk=normalizeString(payload.get("complianceRisk")) or "unknown",
        offline_risk="requested"
        if "offline_first_requested" in missing_detail_result.risk_flags
        else "not_requested",
        risk_flags=missing_detail_result.risk_flags,
        next_action="Answer missing blueprint details"
        if missing_detail_result.missing_categories
        else "Generate customer blueprint",
        next_action_owner_role=UserRole.CUSTOMER_CONTACT
        if missing_detail_result.missing_categories
        else UserRole.WORKFLOW_ANALYST,
        customer_visible_notes=normalizeString(payload.get("customerVisibleNotes")),
        internal_notes=normalizeString(payload.get("internalNotes")),
        created_at_ms=current_time_ms,
        updated_at_ms=current_time_ms,
        last_activity_at_ms=current_time_ms,
    )


def createIntakeFromPayload(
    payload: Mapping[str, Any],
    organization_id: str,
    project_id: str,
    missing_detail_result: MissingDetailResult,
    current_time_ms: int,
) -> IntakeResponse:
    """
    Creates an intake response record from normalized payload.

    Args:
        payload: Normalized intake payload.
        organization_id: Owning organization id.
        project_id: Owning project id.
        missing_detail_result: Intake coverage/risk result.
        current_time_ms: Timestamp for created/updated fields.

    Returns:
        IntakeResponse domain record.
    """
    intake_status = IntakeStatus.SUBMITTED
    if missing_detail_result.missing_categories:
        intake_status = IntakeStatus.NEEDS_FOLLOW_UP
    return IntakeResponse(
        id=createRecordId("intake"),
        organization_id=organization_id,
        project_id=project_id,
        status=intake_status,
        ai_consent_accepted=coerceBool(payload.get("aiConsentAccepted")),
        terms_accepted=coerceBool(payload.get("termsAccepted")),
        business_context_answer=normalizeString(payload.get("workflowDescription")),
        users_permissions_answer=normalizeString(payload.get("usersPermissions")),
        workflow_lifecycle_answer=normalizeString(payload.get("workflowLifecycle")),
        statuses_answer=normalizeString(payload.get("statuses")),
        forms_data_files_answer=normalizeString(payload.get("formsDataFiles")),
        dashboards_reports_answer=normalizeString(payload.get("dashboardsReports")),
        integrations_notifications_answer=normalizeString(payload.get("integrationsNotifications")),
        additional_context_answer=normalizeString(payload.get("additionalContext")),
        sensitive_information_answer=normalizeString(payload.get("sensitiveInformation")),
        compliance_certification_answer=normalizeString(payload.get("complianceCertification")),
        expected_user_count_answer=normalizeString(payload.get("expectedUserCount")),
        mvp_timing_answer=normalizeString(payload.get("mvpTiming")),
        budget_answer=normalizeString(payload.get("budgetRange")),
        project_approver_answer=normalizeString(payload.get("projectApprover")),
        features_that_can_wait_answer=normalizeString(payload.get("featuresThatCanWait")),
        missing_detail_categories=missing_detail_result.missing_categories,
        follow_up_questions=createFollowUpQuestions(missing_detail_result.missing_categories),
        coverage_count=missing_detail_result.coverage_count,
        coverage_total=missing_detail_result.coverage_total,
        completion_percent=missing_detail_result.completion_percent,
        risk_flags=missing_detail_result.risk_flags,
        submitted_at_ms=current_time_ms,
        created_at_ms=current_time_ms,
        updated_at_ms=current_time_ms,
    )


def createFollowUpQuestions(missing_categories: tuple[str, ...]) -> tuple[str, ...]:
    """
    Creates deterministic follow-up questions for missing categories.

    Args:
        missing_categories: Missing intake detail categories.

    Returns:
        Follow-up question text.
    """
    question_map = {
        "users_and_permissions": "Who will use the app, and what can each role do?",
        "workflow_lifecycle": "What statuses should the core workflow move through?",
        "data_forms_and_files": "What fields, forms, files, or records must be captured?",
        "dashboards_and_reports": "What dashboard metrics, reports, or exports are needed?",
        "integrations_and_notifications": "What integrations or notifications are required?",
        "additional_context": "What extra context would help define a safe MVP?",
        "business_context": "What business problem and current tools should the workflow capture?",
    }
    return tuple(
        question_map[category] for category in missing_categories if category in question_map
    )


def normalizeString(value: object) -> str:
    """
    Normalizes a value into stripped text.

    Args:
        value: Raw value.

    Returns:
        Stripped string or empty string.
    """
    if value is None:
        return ""
    return str(value).strip()


def optionalString(value: object) -> str | None:
    """
    Normalizes optional text.

    Args:
        value: Raw value.

    Returns:
        Stripped string, or None when blank.
    """
    normalized_value = normalizeString(value)
    return normalized_value or None


def normalizeStringTuple(value: object) -> tuple[str, ...]:
    """
    Normalizes a value into a tuple of strings.

    Args:
        value: Raw value, list-like value, or comma-separated string.

    Returns:
        Tuple of non-empty strings.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple, set)):
        return tuple(normalizeString(item) for item in value if normalizeString(item))
    return (normalizeString(value),) if normalizeString(value) else ()


def coerceBool(value: object) -> bool:
    """
    Coerces form/JSON booleans into bools.

    Args:
        value: Raw value.

    Returns:
        Boolean interpretation.
    """
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "accepted"}
