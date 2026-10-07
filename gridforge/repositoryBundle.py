# -*- coding: utf-8 -*-
# gridforge/repositoryBundle.py
"""
Defines application repository boundaries for GridForge Command Cloud.

The default implementation uses in-memory repositories for Phase 1 so domain,
service, and route behavior can be developed and tested before durable storage is
introduced.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.configLoader import AppConfig
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
from gridforge.repositories.healthRepo import HealthRepository, LocalHealthRepository
from gridforge.repositories.memoryRepo import InMemoryRecordRepository, RecordRepository


@dataclass(frozen=True)
class AppRepositories:
    """
    Bundles repositories injected into route blueprints and services.

    Args:
        ai_request_log_repo: Repository used by internal AI request metadata.
        audit_event_repo: Repository used by workflow audit events.
        blueprint_repo: Repository used by customer-facing blueprints.
        client_approval_repo: Repository used by customer/internal approvals.
        developer_plan_repo: Repository used by internal developer plans.
        export_repo: Repository used by export records.
        health_repo: Repository used by the health check route.
        implementation_slice_repo: Repository used by build slices.
        intake_repo: Repository used by guided intake responses.
        organization_repo: Repository used by customer organizations.
        qa_validation_repo: Repository used by QA validation records.
        support_request_repo: Repository used by support/enhancement records.
        user_repo: Repository used by future local/demo auth records.
        workflow_project_repo: Repository used by customer workflow projects.
    """

    ai_request_log_repo: RecordRepository[AiRequestLog]
    audit_event_repo: RecordRepository[AuditEvent]
    blueprint_repo: RecordRepository[CustomerBlueprint]
    client_approval_repo: RecordRepository[ClientApproval]
    developer_plan_repo: RecordRepository[DeveloperPlan]
    export_repo: RecordRepository[ExportRecord]
    health_repo: HealthRepository
    implementation_slice_repo: RecordRepository[ImplementationSlice]
    intake_repo: RecordRepository[IntakeResponse]
    organization_repo: RecordRepository[CustomerOrganization]
    qa_validation_repo: RecordRepository[QaValidationItem]
    support_request_repo: RecordRepository[SupportRequest]
    user_repo: RecordRepository[User]
    workflow_project_repo: RecordRepository[CustomerWorkflowProject]


def createMemoryRepositories(health_repo: HealthRepository | None = None) -> AppRepositories:
    """
    Creates an in-memory repository bundle for tests and early MVP slices.

    Args:
        health_repo: Optional health repository override.

    Returns:
        AppRepositories backed by in-memory repositories.
    """
    return AppRepositories(
        ai_request_log_repo=InMemoryRecordRepository[AiRequestLog](),
        audit_event_repo=InMemoryRecordRepository[AuditEvent](),
        blueprint_repo=InMemoryRecordRepository[CustomerBlueprint](),
        client_approval_repo=InMemoryRecordRepository[ClientApproval](),
        developer_plan_repo=InMemoryRecordRepository[DeveloperPlan](),
        export_repo=InMemoryRecordRepository[ExportRecord](),
        health_repo=health_repo or LocalHealthRepository(),
        implementation_slice_repo=InMemoryRecordRepository[ImplementationSlice](),
        intake_repo=InMemoryRecordRepository[IntakeResponse](),
        organization_repo=InMemoryRecordRepository[CustomerOrganization](),
        qa_validation_repo=InMemoryRecordRepository[QaValidationItem](),
        support_request_repo=InMemoryRecordRepository[SupportRequest](),
        user_repo=InMemoryRecordRepository[User](),
        workflow_project_repo=InMemoryRecordRepository[CustomerWorkflowProject](),
    )


def createDefaultRepositories(app_config: AppConfig | None = None) -> AppRepositories:
    """
    Creates the default repository bundle for the application factory.

    Args:
        app_config: Optional application configuration used by later persistence choices.

    Returns:
        AppRepositories backed by Phase 1 in-memory repositories.
    """
    _ = app_config
    return createMemoryRepositories()
