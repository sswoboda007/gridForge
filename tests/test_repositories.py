# -*- coding: utf-8 -*-
# tests/test_repositories.py
"""
Tests GridForge in-memory repositories.

The tests verify Phase 1 repositories support create, read, update, list, and
organization/project scoped list operations across core MVP records.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import replace
from typing import TypeVar

# 2) Third-party imports (alphabetized)
import pytest

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
)
from gridforge.repositories.memoryRepo import (
    InMemoryRecordRepository,
    RecordRepository,
    StoredRecord,
)
from gridforge.repositoryBundle import createMemoryRepositories

CURRENT_TIME_MS = 1000
TRecord = TypeVar("TRecord", bound=StoredRecord)


def assertRepositoryRoundTrip(
    repository: RecordRepository[TRecord],
    original_record: TRecord,
    updated_record: TRecord,
) -> None:
    """
    Verifies shared repository create, read, update, and list behavior.

    Args:
        repository: Repository under test.
        original_record: Initial record to create.
        updated_record: Replacement record with the same id.

    Returns:
        None.
    """
    created_record = repository.createRecord(original_record)

    assert created_record == original_record
    assert repository.getRecord(original_record.id) == original_record
    assert repository.getRecord("missing") is None
    assert repository.listRecords() == (original_record,)
    assert repository.updateRecord(updated_record) == updated_record
    assert repository.getRecord(original_record.id) == updated_record


def test_inMemoryRepositoryRejectsDuplicateIdsAndMissingUpdates() -> None:
    """
    Verifies duplicate creates fail and missing updates are safe no-ops.

    Returns:
        None.
    """
    repository = InMemoryRecordRepository[CustomerOrganization]()
    organization = createOrganization()

    repository.createRecord(organization)

    with pytest.raises(ValueError, match="Record already exists"):
        repository.createRecord(organization)
    assert repository.updateRecord(replace(organization, id="missing")) is None


def test_memoryRepositoriesRoundTripAllCoreRecords() -> None:
    """
    Verifies the repository bundle stores every Phase 1 core record.

    Returns:
        None.
    """
    repositories = createMemoryRepositories()
    organization = createOrganization()
    project = createProject(organization.id)
    intake = createIntake(organization.id, project.id)
    blueprint = createBlueprint(organization.id, project.id, intake.id)
    developer_plan = createDeveloperPlan(organization.id, project.id, blueprint.id)
    implementation_slice = createImplementationSlice(organization.id, project.id, developer_plan.id)
    qa_item = createQaItem(organization.id, project.id, implementation_slice.id)
    approval = createApproval(organization.id, project.id)
    support_request = createSupportRequest(organization.id, project.id)
    export_record = createExportRecord(organization.id, project.id)
    audit_event = createAuditEvent(organization.id, project.id, blueprint.id)
    ai_log = createAiRequestLog(organization.id, project.id)
    user = createUser(organization.id)

    assertRepositoryRoundTrip(
        repositories.organization_repo,
        organization,
        replace(organization, status="active", updated_at_ms=CURRENT_TIME_MS + 1),
    )
    assertRepositoryRoundTrip(
        repositories.workflow_project_repo,
        project,
        replace(project, status=ProjectStatus.INTAKE_IN_PROGRESS),
    )
    assertRepositoryRoundTrip(
        repositories.intake_repo,
        intake,
        replace(intake, status=IntakeStatus.COMPLETE),
    )
    assertRepositoryRoundTrip(
        repositories.blueprint_repo,
        blueprint,
        replace(blueprint, status=BlueprintStatus.READY_FOR_CUSTOMER_REVIEW),
    )
    assertRepositoryRoundTrip(
        repositories.developer_plan_repo,
        developer_plan,
        replace(developer_plan, status=DeveloperPlanStatus.NEEDS_TECHNICAL_REVIEW),
    )
    assertRepositoryRoundTrip(
        repositories.implementation_slice_repo,
        implementation_slice,
        replace(implementation_slice, status=SliceStatus.ACTIVE),
    )
    assertRepositoryRoundTrip(
        repositories.qa_validation_repo,
        qa_item,
        replace(qa_item, status=QaStatus.PASSED),
    )
    assertRepositoryRoundTrip(
        repositories.client_approval_repo,
        approval,
        replace(approval, status=ApprovalStatus.APPROVED),
    )
    assertRepositoryRoundTrip(
        repositories.support_request_repo,
        support_request,
        replace(support_request, status=SupportStatus.IN_PROGRESS),
    )
    assertRepositoryRoundTrip(
        repositories.export_repo,
        export_record,
        replace(export_record, status=ExportStatus.DOWNLOADED),
    )
    assertRepositoryRoundTrip(
        repositories.audit_event_repo,
        audit_event,
        replace(audit_event, customer_visible=True),
    )
    assertRepositoryRoundTrip(
        repositories.ai_request_log_repo,
        ai_log,
        replace(ai_log, validation_status="passed"),
    )
    assertRepositoryRoundTrip(
        repositories.user_repo,
        user,
        replace(user, status="disabled"),
    )


def test_memoryRepositoryScopedListingUsesOrganizationAndProjectIds() -> None:
    """
    Verifies scoped list helpers enforce organization and project boundaries.

    Returns:
        None.
    """
    repository = InMemoryRecordRepository[IntakeResponse]()
    first_intake = createIntake("org_1", "project_1")
    second_intake = replace(
        first_intake, id="intake_2", organization_id="org_2", project_id="project_2"
    )

    repository.createRecord(first_intake)
    repository.createRecord(second_intake)

    assert repository.listByOrganization("org_1") == (first_intake,)
    assert repository.listByOrganization("org_2") == (second_intake,)
    assert repository.listByOrganization("org_missing") == ()
    assert repository.listByProject("project_1") == (first_intake,)
    assert repository.listByProject("project_missing") == ()


def createOrganization() -> CustomerOrganization:
    """
    Creates a sample organization record.

    Returns:
        CustomerOrganization test record.
    """
    return CustomerOrganization(
        id="org_1",
        organization_name="Example Co",
        primary_contact_name="Pat Customer",
        primary_contact_email="pat@example.test",
        status="lead",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createProject(organization_id: str) -> CustomerWorkflowProject:
    """
    Creates a sample workflow project record.

    Args:
        organization_id: Owning organization id.

    Returns:
        CustomerWorkflowProject test record.
    """
    return CustomerWorkflowProject(
        id="project_1",
        organization_id=organization_id,
        project_name="Command Center",
        primary_contact_name="Pat Customer",
        primary_contact_email="pat@example.test",
        workflow_type="customer discovery",
        status=ProjectStatus.LEAD_CAPTURED,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createIntake(organization_id: str, project_id: str) -> IntakeResponse:
    """
    Creates a sample intake response record.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.

    Returns:
        IntakeResponse test record.
    """
    return IntakeResponse(
        id="intake_1",
        organization_id=organization_id,
        project_id=project_id,
        status=IntakeStatus.SUBMITTED,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createBlueprint(organization_id: str, project_id: str, intake_id: str) -> CustomerBlueprint:
    """
    Creates a sample customer blueprint record.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.
        intake_id: Source intake id.

    Returns:
        CustomerBlueprint test record.
    """
    return CustomerBlueprint(
        id="blueprint_1",
        organization_id=organization_id,
        project_id=project_id,
        intake_id=intake_id,
        status=BlueprintStatus.GENERATED,
        title="Customer Workflow Blueprint",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createDeveloperPlan(organization_id: str, project_id: str, blueprint_id: str) -> DeveloperPlan:
    """
    Creates a sample developer plan record.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.
        blueprint_id: Source blueprint id.

    Returns:
        DeveloperPlan test record.
    """
    return DeveloperPlan(
        id="devplan_1",
        organization_id=organization_id,
        project_id=project_id,
        blueprint_id=blueprint_id,
        status=DeveloperPlanStatus.GENERATED,
        implementation_overview="Build the focused MVP.",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createImplementationSlice(
    organization_id: str,
    project_id: str,
    developer_plan_id: str,
) -> ImplementationSlice:
    """
    Creates a sample implementation slice record.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.
        developer_plan_id: Source developer plan id.

    Returns:
        ImplementationSlice test record.
    """
    return ImplementationSlice(
        id="slice_1",
        organization_id=organization_id,
        project_id=project_id,
        developer_plan_id=developer_plan_id,
        name="Intake Management",
        description="Capture customer intake.",
        status=SliceStatus.PLANNED,
        priority="high",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createQaItem(
    organization_id: str,
    project_id: str,
    implementation_slice_id: str,
) -> QaValidationItem:
    """
    Creates a sample QA validation item.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.
        implementation_slice_id: Related implementation slice id.

    Returns:
        QaValidationItem test record.
    """
    return QaValidationItem(
        id="qa_1",
        organization_id=organization_id,
        project_id=project_id,
        implementation_slice_id=implementation_slice_id,
        title="Intake creates project",
        status=QaStatus.OPEN,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createApproval(organization_id: str, project_id: str) -> ClientApproval:
    """
    Creates a sample approval record.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.

    Returns:
        ClientApproval test record.
    """
    return ClientApproval(
        id="approval_1",
        organization_id=organization_id,
        project_id=project_id,
        approval_type="blueprint",
        requested_by_user_id="user_admin",
        requested_from_user_id="user_customer",
        status=ApprovalStatus.REQUESTED,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createSupportRequest(organization_id: str, project_id: str) -> SupportRequest:
    """
    Creates a sample support request record.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.

    Returns:
        SupportRequest test record.
    """
    return SupportRequest(
        id="support_1",
        organization_id=organization_id,
        project_id=project_id,
        title="Need a status tweak",
        request_type="enhancement",
        priority="normal",
        status=SupportStatus.OPEN,
        customer_description="Please add another status.",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createExportRecord(organization_id: str, project_id: str) -> ExportRecord:
    """
    Creates a sample export record.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.

    Returns:
        ExportRecord test record.
    """
    return ExportRecord(
        id="export_1",
        organization_id=organization_id,
        project_id=project_id,
        export_type="customer_summary",
        status=ExportStatus.GENERATED,
        generated_by_user_id="user_admin",
        generated_at_ms=CURRENT_TIME_MS,
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createAuditEvent(organization_id: str, project_id: str, record_id: str) -> AuditEvent:
    """
    Creates a sample audit event.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.
        record_id: Related record id.

    Returns:
        AuditEvent test record.
    """
    return AuditEvent(
        id="audit_1",
        organization_id=organization_id,
        project_id=project_id,
        event_type="blueprint_generated",
        actor_user_id="user_admin",
        actor_role=UserRole.PLATFORM_ADMIN,
        record_type="CustomerBlueprint",
        record_id=record_id,
        safe_summary="Blueprint generated.",
        customer_visible=False,
        created_at_ms=CURRENT_TIME_MS,
    )


def createAiRequestLog(organization_id: str, project_id: str) -> AiRequestLog:
    """
    Creates a sample AI request log.

    Args:
        organization_id: Owning organization id.
        project_id: Owning project id.

    Returns:
        AiRequestLog test record.
    """
    return AiRequestLog(
        id="ailog_1",
        organization_id=organization_id,
        project_id=project_id,
        request_type="customer_blueprint",
        prompt_version="customer-blueprint-v1",
        model="gpt-4o-mini",
        status="validated",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )


def createUser(organization_id: str) -> User:
    """
    Creates a sample user record.

    Args:
        organization_id: Owning organization id.

    Returns:
        User test record.
    """
    return User(
        id="user_customer",
        organization_id=organization_id,
        email="customer@example.test",
        display_name="Pat Customer",
        roles=(UserRole.CUSTOMER_CONTACT,),
        status="active",
        created_at_ms=CURRENT_TIME_MS,
        updated_at_ms=CURRENT_TIME_MS,
    )
