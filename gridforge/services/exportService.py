# -*- coding: utf-8 -*-
# gridforge/services/exportService.py
"""
Builds CSV exports for GridForge.

The service produces customer-safe and internal CSV downloads, applies role access
at the service boundary, redacts restricted fields from customer-safe exports, and
records export/audit records for every download.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
import csv
from dataclasses import dataclass
from io import StringIO
from typing import Iterable

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import ExportStatus, ProjectStatus, UserRole
from gridforge.domain.records import AuditEvent, ExportRecord, JsonObject
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import AuditService, createRecordId, currentTimeMs

CUSTOMER_SAFE_EXPORT_TYPES = ("customer_summary", "blueprint_summary")
INTERNAL_EXPORT_TYPES = ("developer_plan_internal", "qa_handoff", "audit")


@dataclass(frozen=True)
class ExportResult:
    """
    Stores export service outcomes.

    Args:
        ok: Whether the export succeeded.
        status_code: HTTP-friendly status code.
        errors: Validation or guard errors.
        filename: Suggested download filename.
        content: CSV content.
        export_record: Export record created for the download.
        audit_event: Audit event created for the download.
    """

    ok: bool
    status_code: int
    errors: tuple[str, ...]
    filename: str = ""
    content: str = ""
    export_record: ExportRecord | None = None
    audit_event: AuditEvent | None = None


class ExportService:
    """
    Builds CSV exports and records download audit trails.
    """

    def __init__(self, repositories: AppRepositories) -> None:
        """
        Initializes the export service.

        Args:
            repositories: Repository bundle used by exports.

        Returns:
            None.
        """
        self._repositories = repositories
        self._audit_service = AuditService(repositories.audit_event_repo)

    def buildProjectExport(
        self,
        project_id: str,
        export_type: str,
        actor_user_id: str | None,
        actor_roles: tuple[UserRole, ...],
        current_time_ms: int | None = None,
    ) -> ExportResult:
        """
        Builds a project-scoped CSV export.

        Args:
            project_id: Project id.
            export_type: Export type identifier.
            actor_user_id: Current actor id.
            actor_roles: Current actor roles.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            ExportResult with CSV content or errors.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        project = self._repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            return ExportResult(ok=False, status_code=404, errors=("Project not found.",))
        if export_type in INTERNAL_EXPORT_TYPES and not hasInternalRole(actor_roles):
            return ExportResult(ok=False, status_code=403, errors=("Internal role required.",))
        if export_type == "customer_summary":
            rows = [
                {
                    "project_id": project.id,
                    "project_name": project.project_name,
                    "workflow_type": project.workflow_type,
                    "status": customerSafeProjectStatus(project.status),
                    "primary_contact_name": project.primary_contact_name,
                    "desired_outcome": project.desired_outcome,
                    "customer_visible_notes": project.customer_visible_notes,
                }
            ]
            return self.recordExportDownload(
                project_id=project.id,
                organization_id=project.organization_id,
                export_type=export_type,
                actor_user_id=actor_user_id,
                actor_roles=actor_roles,
                filename=f"{project.id}-customer-summary.csv",
                rows=rows,
                current_time_ms=now_ms,
                restricted_fields_excluded=True,
            )
        if export_type == "blueprint_summary":
            blueprints = self._repositories.blueprint_repo.listByProject(project.id)
            rows = [
                {
                    "blueprint_id": blueprint.id,
                    "project_id": blueprint.project_id,
                    "title": blueprint.title,
                    "status": blueprint.status.value,
                    "problem_being_solved": blueprint.problem_being_solved,
                    "recommended_pages": summarizeJsonTuple(blueprint.recommended_pages_json),
                    "mvp_scope": " | ".join(blueprint.mvp_scope_json),
                    "risks": " | ".join(blueprint.risks_and_unknowns_json),
                }
                for blueprint in blueprints
            ]
            return self.recordExportDownload(
                project_id=project.id,
                organization_id=project.organization_id,
                export_type=export_type,
                actor_user_id=actor_user_id,
                actor_roles=actor_roles,
                filename=f"{project.id}-blueprint-summary.csv",
                rows=rows,
                current_time_ms=now_ms,
                restricted_fields_excluded=True,
            )
        if export_type == "developer_plan_internal":
            developer_plans = self._repositories.developer_plan_repo.listByProject(project.id)
            rows = [
                {
                    "developer_plan_id": developer_plan.id,
                    "project_id": developer_plan.project_id,
                    "blueprint_id": developer_plan.blueprint_id,
                    "status": developer_plan.status.value,
                    "validation_status": developer_plan.validation_status,
                    "implementation_overview": developer_plan.implementation_overview,
                    "slice_count": str(len(developer_plan.implementation_slices_json)),
                }
                for developer_plan in developer_plans
            ]
            return self.recordExportDownload(
                project_id=project.id,
                organization_id=project.organization_id,
                export_type=export_type,
                actor_user_id=actor_user_id,
                actor_roles=actor_roles,
                filename=f"{project.id}-developer-plan-internal.csv",
                rows=rows,
                current_time_ms=now_ms,
                restricted_fields_excluded=False,
            )
        if export_type == "qa_handoff":
            qa_items = self._repositories.qa_validation_repo.listByProject(project.id)
            rows = [
                {
                    "qa_item_id": qa_item.id,
                    "project_id": qa_item.project_id,
                    "slice_id": qa_item.implementation_slice_id or "",
                    "title": qa_item.title,
                    "status": qa_item.status.value,
                    "acceptance_criterion": qa_item.acceptance_criterion,
                    "actual_behavior": qa_item.actual_behavior,
                    "resolution_notes": qa_item.resolution_notes,
                }
                for qa_item in qa_items
            ]
            return self.recordExportDownload(
                project_id=project.id,
                organization_id=project.organization_id,
                export_type=export_type,
                actor_user_id=actor_user_id,
                actor_roles=actor_roles,
                filename=f"{project.id}-qa-handoff.csv",
                rows=rows,
                current_time_ms=now_ms,
                restricted_fields_excluded=True,
            )
        return ExportResult(ok=False, status_code=400, errors=("Unsupported export type.",))

    def buildAuditExport(
        self,
        actor_user_id: str | None,
        actor_roles: tuple[UserRole, ...],
        current_time_ms: int | None = None,
    ) -> ExportResult:
        """
        Builds a platform-admin audit CSV export.

        Args:
            actor_user_id: Current actor id.
            actor_roles: Current actor roles.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            ExportResult with CSV content or errors.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        if UserRole.PLATFORM_ADMIN not in actor_roles:
            return ExportResult(
                ok=False, status_code=403, errors=("Platform Admin role required.",)
            )
        rows = [
            {
                "audit_event_id": event.id,
                "project_id": event.project_id or "",
                "organization_id": event.organization_id or "",
                "event_type": event.event_type,
                "record_type": event.record_type,
                "record_id": event.record_id,
                "safe_summary": event.safe_summary,
                "customer_visible": str(event.customer_visible),
                "created_at_ms": event.created_at_ms,
            }
            for event in self._repositories.audit_event_repo.listRecords()
        ]
        return self.recordExportDownload(
            project_id=None,
            organization_id=None,
            export_type="audit",
            actor_user_id=actor_user_id,
            actor_roles=actor_roles,
            filename="gridforge-audit.csv",
            rows=rows,
            current_time_ms=now_ms,
            restricted_fields_excluded=True,
        )

    def recordExportDownload(
        self,
        *,
        project_id: str | None,
        organization_id: str | None,
        export_type: str,
        actor_user_id: str | None,
        actor_roles: tuple[UserRole, ...],
        filename: str,
        rows: list[JsonObject],
        current_time_ms: int,
        restricted_fields_excluded: bool,
    ) -> ExportResult:
        """
        Records an export download and creates CSV content.

        Args:
            project_id: Optional project id.
            organization_id: Optional organization id.
            export_type: Export type identifier.
            actor_user_id: Current actor id.
            actor_roles: Current actor roles.
            filename: Suggested filename.
            rows: CSV rows.
            current_time_ms: Timestamp for records.
            restricted_fields_excluded: Whether restricted fields were excluded.

        Returns:
            ExportResult with CSV content and stored records.
        """
        export_record = ExportRecord(
            id=createRecordId("export"),
            organization_id=organization_id or "",
            project_id=project_id,
            export_type=export_type,
            status=ExportStatus.DOWNLOADED,
            generated_by_user_id=actor_user_id or "unknown",
            generated_at_ms=current_time_ms,
            created_at_ms=current_time_ms,
            updated_at_ms=current_time_ms,
            filters_json={"projectId": project_id} if project_id else {},
            role_access_json={"roles": [role.value for role in actor_roles]},
            downloaded_by_user_id=actor_user_id,
            downloaded_at_ms=current_time_ms,
            restricted_fields_excluded=restricted_fields_excluded,
            file_ref=filename,
        )
        self._repositories.export_repo.createRecord(export_record)
        audit_event = self._audit_service.recordEvent(
            event_type="export_downloaded",
            organization_id=organization_id,
            project_id=project_id,
            record_type="ExportRecord",
            record_id=export_record.id,
            safe_summary=f"CSV export downloaded: {export_type}.",
            actor_user_id=actor_user_id,
            actor_role=actor_roles[0] if actor_roles else None,
            customer_visible=False,
            before_after_json={"exportType": export_type, "filename": filename},
            current_time_ms=current_time_ms,
        )
        return ExportResult(
            ok=True,
            status_code=200,
            errors=(),
            filename=filename,
            content=buildCsv(rows),
            export_record=export_record,
            audit_event=audit_event,
        )


def customerSafeProjectStatus(status: ProjectStatus) -> str:
    """
    Maps internal lifecycle statuses to customer-safe labels.

    Args:
        status: Internal project status.

    Returns:
        Customer-safe status label.
    """
    if status in (
        ProjectStatus.LEAD_CAPTURED,
        ProjectStatus.INTAKE_IN_PROGRESS,
        ProjectStatus.INTAKE_NEEDS_FOLLOW_UP,
        ProjectStatus.INTAKE_READY_FOR_BLUEPRINT,
    ):
        return "intake"
    if status in (
        ProjectStatus.BLUEPRINT_DRAFT_GENERATED,
        ProjectStatus.BLUEPRINT_NEEDS_INTERNAL_REVIEW,
        ProjectStatus.BLUEPRINT_READY_FOR_CUSTOMER_REVIEW,
        ProjectStatus.BLUEPRINT_CHANGES_REQUESTED,
        ProjectStatus.BLUEPRINT_APPROVED,
    ):
        return "planning"
    if status in (
        ProjectStatus.DEMO_READY,
        ProjectStatus.CUSTOMER_DEMO_REVIEW,
        ProjectStatus.CHANGES_REQUESTED,
    ):
        return "demo_review"
    if status in (
        ProjectStatus.HANDOFF_READY,
        ProjectStatus.ACCEPTED_DELIVERED,
        ProjectStatus.SUPPORT_RETAINER,
    ):
        return "support"
    if status == ProjectStatus.ARCHIVED:
        return "archived"
    return "in_progress"


def summarizeJsonTuple(values: tuple[JsonObject, ...]) -> str:
    """
    Creates a compact customer-safe summary for JSON tuple fields.

    Args:
        values: Tuple of JSON object values.

    Returns:
        Pipe-delimited object summaries.
    """
    summaries: list[str] = []
    for value in values:
        label = value.get("name") or value.get("title") or value.get("page") or value.get("role")
        summaries.append(str(label or value))
    return " | ".join(summaries)


def hasInternalRole(actor_roles: tuple[UserRole, ...]) -> bool:
    """
    Checks whether roles include an internal GridForge role.

    Args:
        actor_roles: Actor roles.

    Returns:
        True when the actor is internal.
    """
    internal_roles = {
        UserRole.PLATFORM_ADMIN,
        UserRole.WORKFLOW_ANALYST,
        UserRole.DEVELOPER,
        UserRole.QA_REVIEWER,
        UserRole.SUPPORT_MANAGER,
        UserRole.READ_ONLY_EXECUTIVE,
    }
    return bool(set(actor_roles).intersection(internal_roles))


def buildCsv(rows: Iterable[JsonObject]) -> str:
    """
    Builds CSV text from JSON-safe row mappings.

    Args:
        rows: Row mappings.

    Returns:
        CSV content including a header row when fields exist.
    """
    materialized_rows = list(rows)
    fieldnames = tuple(materialized_rows[0].keys()) if materialized_rows else ("empty",)
    output = StringIO()
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for row in materialized_rows:
        writer.writerow(row)
    return output.getvalue()


def createExportErrorPayload(result: ExportResult) -> JsonObject:
    """
    Creates a JSON-safe export error payload.

    Args:
        result: Failed export result.

    Returns:
        Error payload.
    """
    return {"ok": False, "errors": list(result.errors)}
