# -*- coding: utf-8 -*-
# gridforge/services/dashboardMetricService.py
"""
Builds internal dashboard metrics for GridForge.

The service aggregates the MVP command-center metrics from repositories without
exposing raw AI payloads, developer-only records to customers, or unrestricted
cross-tenant data.

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
from gridforge.domain.enums import (
    BlueprintStatus,
    DeveloperPlanStatus,
    ExportStatus,
    IntakeStatus,
    ProjectStatus,
    QaStatus,
    SliceStatus,
    SupportStatus,
)
from gridforge.domain.records import (
    AuditEvent,
    CustomerWorkflowProject,
    ImplementationSlice,
    JsonObject,
)
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import currentTimeMs


@dataclass(frozen=True)
class DashboardMetrics:
    """
    Stores dashboard metric results.

    Args:
        counts: Named command-center metric counts.
        project_status_counts: Counts by project lifecycle status.
        review_queue: Internal review/exception queue counts.
        project_health: Project records for the health board.
        recent_audit_events: Recent safe audit events.
    """

    counts: JsonObject
    project_status_counts: JsonObject
    review_queue: JsonObject
    project_health: tuple[CustomerWorkflowProject, ...]
    recent_audit_events: tuple[AuditEvent, ...]


class DashboardMetricService:
    """
    Aggregates internal command-center dashboard metrics.
    """

    def __init__(self, repositories: AppRepositories) -> None:
        """
        Initializes the dashboard metric service.

        Args:
            repositories: Repository bundle used to aggregate metrics.

        Returns:
            None.
        """
        self._repositories = repositories

    def buildDashboardMetrics(self, current_time_ms: int | None = None) -> DashboardMetrics:
        """
        Builds all MVP dashboard metrics.

        Args:
            current_time_ms: Optional deterministic timestamp for overdue checks.

        Returns:
            DashboardMetrics for templates/tests.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        projects = self._repositories.workflow_project_repo.listRecords()
        intakes = self._repositories.intake_repo.listRecords()
        blueprints = self._repositories.blueprint_repo.listRecords()
        developer_plans = self._repositories.developer_plan_repo.listRecords()
        slices = self._repositories.implementation_slice_repo.listRecords()
        qa_items = self._repositories.qa_validation_repo.listRecords()
        support_requests = self._repositories.support_request_repo.listRecords()
        export_records = self._repositories.export_repo.listRecords()
        ai_logs = self._repositories.ai_request_log_repo.listRecords()
        audit_events = self._repositories.audit_event_repo.listRecords()
        active_project_statuses = {
            ProjectStatus.LEAD_CAPTURED,
            ProjectStatus.INTAKE_IN_PROGRESS,
            ProjectStatus.INTAKE_NEEDS_FOLLOW_UP,
            ProjectStatus.INTAKE_READY_FOR_BLUEPRINT,
            ProjectStatus.BLUEPRINT_DRAFT_GENERATED,
            ProjectStatus.BLUEPRINT_NEEDS_INTERNAL_REVIEW,
            ProjectStatus.BLUEPRINT_READY_FOR_CUSTOMER_REVIEW,
            ProjectStatus.BLUEPRINT_CHANGES_REQUESTED,
            ProjectStatus.BLUEPRINT_APPROVED,
            ProjectStatus.DEVELOPER_PLAN_PENDING,
            ProjectStatus.DEVELOPER_PLAN_DRAFTED,
            ProjectStatus.DEVELOPER_PLAN_NEEDS_REVIEW,
            ProjectStatus.DEVELOPER_PLAN_APPROVED,
            ProjectStatus.BUILD_QUEUED,
            ProjectStatus.BUILD_ACTIVE,
            ProjectStatus.BUILD_BLOCKED,
            ProjectStatus.INTERNAL_REVIEW,
            ProjectStatus.QA_VALIDATION,
            ProjectStatus.QA_FAILED_NEEDS_FIXES,
            ProjectStatus.DEMO_READY,
            ProjectStatus.CUSTOMER_DEMO_REVIEW,
            ProjectStatus.CHANGES_REQUESTED,
            ProjectStatus.HANDOFF_READY,
            ProjectStatus.ACCEPTED_DELIVERED,
            ProjectStatus.SUPPORT_RETAINER,
        }
        counts: JsonObject = {
            "totalActiveProjects": sum(
                1 for project in projects if project.status in active_project_statuses
            ),
            "newLeadsThisMonth": sum(
                1 for project in projects if project.status == ProjectStatus.LEAD_CAPTURED
            ),
            "intakesInProgress": sum(
                1 for intake in intakes if intake.status == IntakeStatus.DRAFT
            ),
            "intakesReadyForBlueprint": sum(
                1
                for project in projects
                if project.status == ProjectStatus.INTAKE_READY_FOR_BLUEPRINT
            ),
            "blueprintsNeedingInternalReview": sum(
                1
                for blueprint in blueprints
                if blueprint.status == BlueprintStatus.NEEDS_INTERNAL_REVIEW
            ),
            "blueprintsWaitingOnCustomerInput": sum(
                1
                for blueprint in blueprints
                if blueprint.status
                in (BlueprintStatus.READY_FOR_CUSTOMER_REVIEW, BlueprintStatus.CHANGES_REQUESTED)
            ),
            "blueprintsApproved": sum(
                1 for blueprint in blueprints if blueprint.status == BlueprintStatus.APPROVED
            ),
            "developerPlansPending": sum(
                1
                for project in projects
                if project.status
                in (ProjectStatus.DEVELOPER_PLAN_PENDING, ProjectStatus.DEVELOPER_PLAN_DRAFTED)
            ),
            "developerPlansNeedingReview": sum(
                1
                for developer_plan in developer_plans
                if developer_plan.status == DeveloperPlanStatus.NEEDS_TECHNICAL_REVIEW
            ),
            "developerPlansApproved": sum(
                1
                for developer_plan in developer_plans
                if developer_plan.status == DeveloperPlanStatus.APPROVED
            ),
            "activeBuilds": sum(
                1 for project in projects if project.status == ProjectStatus.BUILD_ACTIVE
            ),
            "blockedBuilds": countBlockedBuildProjects(projects, slices),
            "implementationSlicesCompleted": sum(
                1
                for implementation_slice in slices
                if implementation_slice.status == SliceStatus.COMPLETE
            ),
            "qaOpen": sum(1 for qa_item in qa_items if qa_item.status == QaStatus.OPEN),
            "qaFailed": sum(1 for qa_item in qa_items if qa_item.status == QaStatus.FAILED),
            "qaPassed": sum(1 for qa_item in qa_items if qa_item.status == QaStatus.PASSED),
            "demoReady": sum(
                1 for project in projects if project.status == ProjectStatus.DEMO_READY
            ),
            "handoffReady": sum(
                1 for project in projects if project.status == ProjectStatus.HANDOFF_READY
            ),
            "supportRetainer": sum(
                1
                for support_request in support_requests
                if support_request.status
                in (
                    SupportStatus.OPEN,
                    SupportStatus.IN_REVIEW,
                    SupportStatus.IN_PROGRESS,
                    SupportStatus.WAITING_ON_CUSTOMER,
                )
            ),
            "overdueNextActions": sum(
                1
                for project in projects
                if project.next_action_due_at_ms is not None
                and project.next_action_due_at_ms < now_ms
            ),
            "aiValidationFailures": sum(1 for ai_log in ai_logs if "fail" in ai_log.status.lower())
            + sum(
                1
                for blueprint in blueprints
                if blueprint.status == BlueprintStatus.VALIDATION_FAILED
                or blueprint.validation_status == "failed"
            )
            + sum(
                1
                for developer_plan in developer_plans
                if developer_plan.status == DeveloperPlanStatus.VALIDATION_FAILED
                or developer_plan.validation_status == "failed"
            ),
            "exportsReady": sum(
                1
                for export_record in export_records
                if export_record.status == ExportStatus.GENERATED
            ),
        }
        review_queue: JsonObject = {
            "blueprintsNeedingReview": counts["blueprintsNeedingInternalReview"],
            "developerPlansNeedingReview": counts["developerPlansNeedingReview"],
            "aiValidationFailures": counts["aiValidationFailures"],
            "customerChangeRequests": sum(
                1 for project in projects if project.status == ProjectStatus.CHANGES_REQUESTED
            ),
            "qaFailures": counts["qaFailed"],
        }
        return DashboardMetrics(
            counts=counts,
            project_status_counts=countProjectStatuses(projects),
            review_queue=review_queue,
            project_health=tuple(
                sorted(projects, key=lambda project: project.updated_at_ms, reverse=True)
            ),
            recent_audit_events=tuple(
                sorted(audit_events, key=lambda event: event.created_at_ms, reverse=True)[:10]
            ),
        )


def countBlockedBuildProjects(
    projects: tuple[CustomerWorkflowProject, ...],
    slices: tuple[ImplementationSlice, ...],
) -> int:
    """
    Counts projects with blocked build or failed QA slice state.

    Args:
        projects: Project records to inspect.
        slices: Implementation slice records to inspect.

    Returns:
        Count of unique blocked build project ids.
    """
    blocked_project_ids = {
        project.id
        for project in projects
        if project.status in (ProjectStatus.BUILD_BLOCKED, ProjectStatus.QA_FAILED_NEEDS_FIXES)
    }
    blocked_project_ids.update(
        implementation_slice.project_id
        for implementation_slice in slices
        if implementation_slice.status in (SliceStatus.BLOCKED, SliceStatus.QA_FAILED)
    )
    return len(blocked_project_ids)


def countProjectStatuses(projects: tuple[CustomerWorkflowProject, ...]) -> JsonObject:
    """
    Counts projects by lifecycle status.

    Args:
        projects: Project records to count.

    Returns:
        JSON-safe mapping of status values to counts.
    """
    status_counts: dict[str, int] = {status.value: 0 for status in ProjectStatus}
    for project in projects:
        status_counts[project.status.value] += 1
    return status_counts
