# -*- coding: utf-8 -*-
# gridforge/domain/records.py
"""
Defines core GridForge domain records.

These frozen dataclasses describe the MVP workflow records used by repositories,
services, dashboards, exports, and audit events while keeping customer-facing and
internal-only fields clearly separated.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import asdict, dataclass, field
from typing import Any

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import (
    ApprovalStatus,
    BlueprintStatus,
    DeveloperPlanStatus,
    ExportStatus,
    IntakeStatus,
    ProjectStatus,
    QaStatus,
    SliceStatus,
    SupportStatus,
    UserRole,
)

JsonObject = dict[str, Any]
JsonTuple = tuple[JsonObject, ...]
StringTuple = tuple[str, ...]


@dataclass(frozen=True)
class CustomerOrganization:
    """
    Represents a customer organization and tenant boundary.
    """

    id: str
    organization_name: str
    primary_contact_name: str
    primary_contact_email: str
    status: str
    created_at_ms: int
    updated_at_ms: int
    industry: str = ""
    organization_size: str = ""
    website: str = ""
    primary_location: str = ""
    time_zone: str = ""
    primary_contact_phone: str | None = None
    stakeholder_name: str | None = None
    stakeholder_email: str | None = None
    customer_visible_notes: str = ""
    internal_notes: str = ""


@dataclass(frozen=True)
class CustomerWorkflowProject:
    """
    Represents one customer journey from messy workflow to support.
    """

    id: str
    organization_id: str
    project_name: str
    primary_contact_name: str
    primary_contact_email: str
    workflow_type: str
    status: ProjectStatus
    created_at_ms: int
    updated_at_ms: int
    stakeholder_name: str | None = None
    stakeholder_email: str | None = None
    short_summary: str = ""
    painful_workflow_description: str = ""
    current_tools: StringTuple = ()
    delays_or_losses: str = ""
    manual_reporting: str = ""
    desired_outcome: str = ""
    success_definition: str = ""
    urgency: str = ""
    budget_range: str = ""
    fit_score: int | None = None
    complexity_score: int | None = None
    scope_clarity_score: int | None = None
    privacy_risk: str = "unknown"
    compliance_risk: str = "unknown"
    offline_risk: str = "not_requested"
    ai_suitability_score: int | None = None
    risk_flags: StringTuple = ()
    assigned_owner_user_id: str | None = None
    assigned_analyst_user_id: str | None = None
    assigned_developer_user_id: str | None = None
    assigned_qa_user_id: str | None = None
    assigned_support_user_id: str | None = None
    next_action: str = ""
    next_action_owner_role: UserRole | None = None
    next_action_due_at_ms: int | None = None
    approved_blueprint_id: str | None = None
    active_developer_plan_id: str | None = None
    repo_link: str = ""
    demo_link: str = ""
    internal_notes: str = ""
    customer_visible_notes: str = ""
    last_activity_at_ms: int | None = None


@dataclass(frozen=True)
class IntakeResponse:
    """
    Represents structured answers from the guided intake interview.
    """

    id: str
    organization_id: str
    project_id: str
    status: IntakeStatus
    created_at_ms: int
    updated_at_ms: int
    ai_consent_accepted: bool = False
    terms_accepted: bool = False
    business_context_answer: str = ""
    users_permissions_answer: str = ""
    workflow_lifecycle_answer: str = ""
    core_record_answer: str = ""
    statuses_answer: str = ""
    forms_data_files_answer: str = ""
    dashboards_reports_answer: str = ""
    integrations_notifications_answer: str = ""
    additional_context_answer: str = ""
    sensitive_information_answer: str = ""
    compliance_certification_answer: str = ""
    expected_user_count_answer: str = ""
    mvp_timing_answer: str = ""
    budget_answer: str = ""
    project_approver_answer: str = ""
    features_that_can_wait_answer: str = ""
    missing_detail_categories: StringTuple = ()
    follow_up_questions: StringTuple = ()
    follow_up_answers_json: JsonObject = field(default_factory=dict)
    coverage_count: int = 0
    coverage_total: int = 0
    completion_percent: int = 0
    risk_flags: StringTuple = ()
    submitted_at_ms: int | None = None


@dataclass(frozen=True)
class CustomerBlueprint:
    """
    Represents a customer-facing blueprint plus internal review metadata.
    """

    id: str
    organization_id: str
    project_id: str
    intake_id: str
    status: BlueprintStatus
    title: str
    created_at_ms: int
    updated_at_ms: int
    app_name_ideas: StringTuple = ()
    app_summary: str = ""
    problem_being_solved: str = ""
    target_users_json: JsonTuple = ()
    authority_matrix_json: JsonTuple = ()
    main_workflows_json: JsonTuple = ()
    recommended_pages_json: JsonTuple = ()
    data_objects_json: JsonTuple = ()
    reports_and_exports_json: JsonTuple = ()
    integrations_json: JsonTuple = ()
    mvp_scope_json: StringTuple = ()
    phase_two_scope_json: StringTuple = ()
    later_scope_json: StringTuple = ()
    risks_and_unknowns_json: StringTuple = ()
    follow_up_questions_json: StringTuple = ()
    suggested_build_milestones_json: StringTuple = ()
    fit_summary_json: JsonObject = field(default_factory=dict)
    complexity_summary: str = ""
    customer_visible_notes: str = ""
    internal_reviewer_notes: str = ""
    prompt_version: str = ""
    model: str = ""
    raw_response_ref: str | None = None
    validation_status: str = "pending"
    validation_errors_json: JsonObject = field(default_factory=dict)
    human_reviewer_user_id: str | None = None
    human_reviewed_at_ms: int | None = None
    customer_approval_status: ApprovalStatus = ApprovalStatus.REQUESTED
    customer_approved_by_user_id: str | None = None
    customer_approved_at_ms: int | None = None
    superseded_by_blueprint_id: str | None = None
    generated_at_ms: int | None = None


@dataclass(frozen=True)
class DeveloperPlan:
    """
    Represents an internal developer-only implementation plan.
    """

    id: str
    organization_id: str
    project_id: str
    blueprint_id: str
    status: DeveloperPlanStatus
    implementation_overview: str
    created_at_ms: int
    updated_at_ms: int
    mvp_cut_line_json: JsonObject = field(default_factory=dict)
    entity_specs_json: JsonTuple = ()
    route_specs_json: JsonTuple = ()
    authorization_policies_json: JsonTuple = ()
    state_machines_json: JsonTuple = ()
    validation_rules_json: StringTuple = ()
    query_and_index_specs_json: JsonTuple = ()
    dashboard_metric_specs_json: JsonTuple = ()
    csv_export_specs_json: JsonTuple = ()
    test_plan_json: JsonObject = field(default_factory=dict)
    data_lifecycle_rules_json: StringTuple = ()
    audit_events_json: StringTuple = ()
    security_privacy_notes_json: StringTuple = ()
    failure_modes_json: JsonTuple = ()
    operational_notes_json: StringTuple = ()
    implementation_slices_json: JsonTuple = ()
    blocking_questions_json: StringTuple = ()
    deferred_questions_json: StringTuple = ()
    developer_milestones_json: StringTuple = ()
    prompt_version: str = ""
    model: str = ""
    raw_response_ref: str | None = None
    validation_status: str = "pending"
    validation_errors_json: JsonObject = field(default_factory=dict)
    technical_reviewer_user_id: str | None = None
    technical_reviewed_at_ms: int | None = None
    internal_approval_status: ApprovalStatus = ApprovalStatus.REQUESTED
    generated_at_ms: int | None = None


@dataclass(frozen=True)
class ImplementationSlice:
    """
    Represents one buildable implementation unit from a developer plan.
    """

    id: str
    organization_id: str
    project_id: str
    developer_plan_id: str
    name: str
    description: str
    status: SliceStatus
    priority: str
    created_at_ms: int
    updated_at_ms: int
    assigned_developer_user_id: str | None = None
    scope_items_json: StringTuple = ()
    related_entities_json: StringTuple = ()
    related_routes_json: StringTuple = ()
    required_tests_json: StringTuple = ()
    definition_of_done_json: StringTuple = ()
    estimated_complexity: str = ""
    blockers_json: StringTuple = ()
    internal_notes: str = ""
    demo_link: str = ""
    screenshot_link: str = ""
    repo_link: str = ""
    branch_name: str = ""
    commit_ref: str = ""
    started_at_ms: int | None = None
    completed_at_ms: int | None = None
    qa_status: QaStatus = QaStatus.OPEN


@dataclass(frozen=True)
class QaValidationItem:
    """
    Represents an acceptance or QA validation item.
    """

    id: str
    organization_id: str
    project_id: str
    implementation_slice_id: str | None
    title: str
    status: QaStatus
    created_at_ms: int
    updated_at_ms: int
    requirement_reference: str = ""
    acceptance_criterion: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    severity: str = "medium"
    assigned_qa_user_id: str | None = None
    evidence_link: str = ""
    screenshot_link: str = ""
    test_command_summary: str = ""
    customer_clarification_needed: bool = False
    resolution_notes: str = ""
    passed_at_ms: int | None = None


@dataclass(frozen=True)
class ClientApproval:
    """
    Represents a customer or internal approval decision.
    """

    id: str
    organization_id: str
    project_id: str
    approval_type: str
    requested_by_user_id: str
    requested_from_user_id: str
    status: ApprovalStatus
    created_at_ms: int
    updated_at_ms: int
    related_record_type: str = ""
    related_record_id: str = ""
    decision_notes: str = ""
    approved_by_user_id: str | None = None
    approved_at_ms: int | None = None
    changes_requested: str = ""
    superseded_by_approval_id: str | None = None


@dataclass(frozen=True)
class SupportRequest:
    """
    Represents a post-handoff support or enhancement request.
    """

    id: str
    organization_id: str
    project_id: str
    title: str
    request_type: str
    priority: str
    status: SupportStatus
    customer_description: str
    created_at_ms: int
    updated_at_ms: int
    internal_notes: str = ""
    assigned_support_user_id: str | None = None
    assigned_developer_user_id: str | None = None
    customer_visible_response: str = ""
    resolved_at_ms: int | None = None


@dataclass(frozen=True)
class ExportRecord:
    """
    Represents a generated or downloaded export event.
    """

    id: str
    organization_id: str
    project_id: str | None
    export_type: str
    status: ExportStatus
    generated_by_user_id: str
    generated_at_ms: int
    created_at_ms: int
    updated_at_ms: int
    filters_json: JsonObject = field(default_factory=dict)
    role_access_json: JsonObject = field(default_factory=dict)
    downloaded_by_user_id: str | None = None
    downloaded_at_ms: int | None = None
    restricted_fields_excluded: bool = True
    file_ref: str = ""


@dataclass(frozen=True)
class AuditEvent:
    """
    Represents a sensitive workflow event for traceability.
    """

    id: str
    organization_id: str | None
    project_id: str | None
    event_type: str
    actor_user_id: str | None
    actor_role: UserRole | None
    record_type: str
    record_id: str
    safe_summary: str
    customer_visible: bool
    created_at_ms: int
    before_after_json: JsonObject = field(default_factory=dict)


@dataclass(frozen=True)
class AiRequestLog:
    """
    Represents internal-only AI request metadata.
    """

    id: str
    organization_id: str | None
    project_id: str | None
    request_type: str
    prompt_version: str
    model: str
    status: str
    created_at_ms: int
    updated_at_ms: int
    raw_prompt_ref: str | None = None
    raw_response_ref: str | None = None
    token_input: int = 0
    token_output: int = 0
    cost_estimate_cents: int = 0
    validation_status: str = "pending"
    error_summary: str = ""


@dataclass(frozen=True)
class User:
    """
    Represents a local/demo user identity for future route guards.
    """

    id: str
    organization_id: str | None
    email: str
    display_name: str
    roles: tuple[UserRole, ...]
    status: str
    created_at_ms: int
    updated_at_ms: int


def organizationToCustomerSafeDict(organization: CustomerOrganization) -> JsonObject:
    """
    Converts an organization to a customer-safe dictionary.

    Args:
        organization: Organization record to project.

    Returns:
        Customer-safe organization data without internal notes.
    """
    data = asdict(organization)
    data.pop("internal_notes", None)
    return data


def projectToCustomerSafeDict(project: CustomerWorkflowProject) -> JsonObject:
    """
    Converts a workflow project to a customer-safe dictionary.

    Args:
        project: Project record to project.

    Returns:
        Customer-safe project data without internal scoring or build details.
    """
    data = asdict(project)
    for key in (
        "active_developer_plan_id",
        "ai_suitability_score",
        "assigned_analyst_user_id",
        "assigned_developer_user_id",
        "assigned_owner_user_id",
        "assigned_qa_user_id",
        "assigned_support_user_id",
        "complexity_score",
        "fit_score",
        "internal_notes",
        "repo_link",
        "scope_clarity_score",
    ):
        data.pop(key, None)
    return data


def blueprintToCustomerSafeDict(blueprint: CustomerBlueprint) -> JsonObject:
    """
    Converts a customer blueprint to a customer-safe dictionary.

    Args:
        blueprint: Blueprint record to project.

    Returns:
        Customer-safe blueprint data without AI or internal review metadata.
    """
    data = asdict(blueprint)
    for key in (
        "internal_reviewer_notes",
        "model",
        "prompt_version",
        "raw_response_ref",
        "validation_errors_json",
    ):
        data.pop(key, None)
    return data


def exportToCustomerSafeDict(export_record: ExportRecord) -> JsonObject:
    """
    Converts an export record to a customer-safe dictionary.

    Args:
        export_record: Export record to project.

    Returns:
        Customer-safe export data without internal storage references.
    """
    data = asdict(export_record)
    data.pop("file_ref", None)
    return data
