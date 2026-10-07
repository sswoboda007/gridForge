# -*- coding: utf-8 -*-
# tests/test_domainRecords.py
"""
Tests GridForge domain records and customer-safe projections.

The tests verify the Phase 1 dataclasses can represent core MVP records and that
customer-safe helpers remove internal-only fields.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

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
from gridforge.domain.records import (
    AiRequestLog,
    AuditEvent,
    ClientApproval,
    CustomerBlueprint,
    CustomerOrganization,
    CustomerWorkflowProject,
    DeveloperPlan,
    ExportRecord,
    ImplementationSlice,
    IntakeResponse,
    QaValidationItem,
    SupportRequest,
    User,
    blueprintToCustomerSafeDict,
    exportToCustomerSafeDict,
    organizationToCustomerSafeDict,
    projectToCustomerSafeDict,
)

CURRENT_TIME_MS = 1000


def test_coreDomainRecordsRepresentMvpWorkflow() -> None:
    """
    Verifies every core MVP record can be constructed with typed statuses.

    Returns:
        None.
    """
    organization = CustomerOrganization(
        id="org_1",
        organization_name="Example Co",
        primary_contact_name="Pat Customer",
        primary_contact_email="pat@example.test",
        status="lead",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    project = CustomerWorkflowProject(
        id="project_1",
        organization_id=organization.id,
        project_name="Command Center",
        primary_contact_name="Pat Customer",
        primary_contact_email="pat@example.test",
        workflow_type="customer discovery",
        status=ProjectStatus.LEAD_CAPTURED,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    intake = IntakeResponse(
        id="intake_1",
        organization_id=organization.id,
        project_id=project.id,
        status=IntakeStatus.SUBMITTED,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
        ai_consent_accepted=True,
        terms_accepted=True,
    )
    blueprint = CustomerBlueprint(
        id="blueprint_1",
        organization_id=organization.id,
        project_id=project.id,
        intake_id=intake.id,
        status=BlueprintStatus.GENERATED,
        title="Customer Workflow Blueprint",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    developer_plan = DeveloperPlan(
        id="devplan_1",
        organization_id=organization.id,
        project_id=project.id,
        blueprint_id=blueprint.id,
        status=DeveloperPlanStatus.GENERATED,
        implementation_overview="Build the focused MVP.",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    implementation_slice = ImplementationSlice(
        id="slice_1",
        organization_id=organization.id,
        project_id=project.id,
        developer_plan_id=developer_plan.id,
        name="Intake Management",
        description="Capture the customer intake.",
        status=SliceStatus.PLANNED,
        priority="high",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    qa_item = QaValidationItem(
        id="qa_1",
        organization_id=organization.id,
        project_id=project.id,
        implementation_slice_id=implementation_slice.id,
        title="Intake creates project",
        status=QaStatus.OPEN,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    approval = ClientApproval(
        id="approval_1",
        organization_id=organization.id,
        project_id=project.id,
        approval_type="blueprint",
        requested_by_user_id="user_admin",
        requested_from_user_id="user_customer",
        status=ApprovalStatus.REQUESTED,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    support_request = SupportRequest(
        id="support_1",
        organization_id=organization.id,
        project_id=project.id,
        title="Need a status tweak",
        request_type="enhancement",
        priority="normal",
        status=SupportStatus.OPEN,
        customer_description="Please add another status.",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    export_record = ExportRecord(
        id="export_1",
        organization_id=organization.id,
        project_id=project.id,
        export_type="customer_summary",
        status=ExportStatus.GENERATED,
        generated_by_user_id="user_admin",
        generated_at_ms=CURRENT_TIME_MS,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    audit_event = AuditEvent(
        id="audit_1",
        organization_id=organization.id,
        project_id=project.id,
        event_type="blueprint_generated",
        actor_user_id="user_admin",
        actor_role=UserRole.PLATFORM_ADMIN,
        record_type="CustomerBlueprint",
        record_id=blueprint.id,
        safe_summary="Blueprint generated.",
        customer_visible=False,
        created_at_ms=CURRENT_TIME_MS,
    )
    ai_log = AiRequestLog(
        id="ailog_1",
        organization_id=organization.id,
        project_id=project.id,
        request_type="customer_blueprint",
        prompt_version="customer-blueprint-v1",
        model="gpt-4o-mini",
        status="validated",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
    user = User(
        id="user_admin",
        organization_id=None,
        email="admin@example.test",
        display_name="GridForge Admin",
        roles=(UserRole.PLATFORM_ADMIN,),
        status="active",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )

    assert organization.id == "org_1"
    assert project.status == ProjectStatus.LEAD_CAPTURED
    assert intake.status == IntakeStatus.SUBMITTED
    assert blueprint.status == BlueprintStatus.GENERATED
    assert developer_plan.status == DeveloperPlanStatus.GENERATED
    assert implementation_slice.qa_status == QaStatus.OPEN
    assert qa_item.implementation_slice_id == implementation_slice.id
    assert approval.status == ApprovalStatus.REQUESTED
    assert support_request.status == SupportStatus.OPEN
    assert export_record.restricted_fields_excluded is True
    assert audit_event.actor_role == UserRole.PLATFORM_ADMIN
    assert ai_log.prompt_version == "customer-blueprint-v1"
    assert user.roles == (UserRole.PLATFORM_ADMIN,)


def test_customerSafeProjectionHelpersStripInternalFields() -> None:
    """
    Verifies customer-safe helpers exclude internal-only values.

    Returns:
        None.
    """
    organization = CustomerOrganization(
        id="org_1",
        organization_name="Example Co",
        primary_contact_name="Pat Customer",
        primary_contact_email="pat@example.test",
        status="lead",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
        internal_notes="internal organization note",
    )
    project = CustomerWorkflowProject(
        id="project_1",
        organization_id=organization.id,
        project_name="Command Center",
        primary_contact_name="Pat Customer",
        primary_contact_email="pat@example.test",
        workflow_type="customer discovery",
        status=ProjectStatus.LEAD_CAPTURED,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
        fit_score=90,
        internal_notes="internal project note",
        repo_link="https://example.test/private-repo",
    )
    blueprint = CustomerBlueprint(
        id="blueprint_1",
        organization_id=organization.id,
        project_id=project.id,
        intake_id="intake_1",
        status=BlueprintStatus.GENERATED,
        title="Customer Workflow Blueprint",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
        internal_reviewer_notes="internal blueprint note",
        prompt_version="customer-blueprint-v1",
        model="gpt-4o-mini",
        raw_response_ref="internal-response-ref",
        validation_errors_json={"error": "internal"},
    )
    export_record = ExportRecord(
        id="export_1",
        organization_id=organization.id,
        project_id=project.id,
        export_type="customer_summary",
        status=ExportStatus.GENERATED,
        generated_by_user_id="user_admin",
        generated_at_ms=CURRENT_TIME_MS,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
        file_ref="internal-file-ref",
    )

    organization_safe = organizationToCustomerSafeDict(organization)
    project_safe = projectToCustomerSafeDict(project)
    blueprint_safe = blueprintToCustomerSafeDict(blueprint)
    export_safe = exportToCustomerSafeDict(export_record)

    assert "internal_notes" not in organization_safe
    assert "internal_notes" not in project_safe
    assert "fit_score" not in project_safe
    assert "repo_link" not in project_safe
    assert "internal_reviewer_notes" not in blueprint_safe
    assert "prompt_version" not in blueprint_safe
    assert "model" not in blueprint_safe
    assert "raw_response_ref" not in blueprint_safe
    assert "validation_errors_json" not in blueprint_safe
    assert "file_ref" not in export_safe
