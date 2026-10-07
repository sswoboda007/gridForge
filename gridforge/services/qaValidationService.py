# -*- coding: utf-8 -*-
# gridforge/services/qaValidationService.py
"""
Creates and updates QA validation items for GridForge.

The service enforces QA statuses, updates linked implementation slices, blocks
demo readiness on failures, and marks projects demo-ready only after required QA
checks pass.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass, replace

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import ProjectStatus, QaStatus, SliceStatus, UserRole
from gridforge.domain.records import AuditEvent, JsonObject, QaValidationItem
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import AuditService, createRecordId, currentTimeMs

ALLOWED_QA_STATUSES = (
    QaStatus.OPEN,
    QaStatus.PASSED,
    QaStatus.FAILED,
    QaStatus.BLOCKED,
    QaStatus.NEEDS_CUSTOMER_CLARIFICATION,
)


@dataclass(frozen=True)
class QaValidationResult:
    """
    Stores QA validation service action outcomes.

    Args:
        ok: Whether the action succeeded.
        status_code: HTTP-friendly status code.
        errors: Validation or guard errors.
        qa_item: QA item created or updated by the action.
        audit_events: Audit events created by the action.
    """

    ok: bool
    status_code: int
    errors: tuple[str, ...]
    qa_item: QaValidationItem | None = None
    audit_events: tuple[AuditEvent, ...] = ()


class QaValidationService:
    """
    Creates and updates QA validation items.
    """

    def __init__(self, repositories: AppRepositories) -> None:
        """
        Initializes the QA validation service.

        Args:
            repositories: Repository bundle used by QA workflow.

        Returns:
            None.
        """
        self._repositories = repositories
        self._audit_service = AuditService(repositories.audit_event_repo)

    def createQaItem(
        self,
        project_id: str,
        title: str,
        actor_user_id: str | None,
        implementation_slice_id: str | None = None,
        acceptance_criterion: str = "",
        expected_behavior: str = "",
        severity: str = "medium",
        current_time_ms: int | None = None,
    ) -> QaValidationResult:
        """
        Creates a manual QA validation item for a project.

        Args:
            project_id: Owning project id.
            title: QA item title.
            actor_user_id: QA/Admin actor user id.
            implementation_slice_id: Optional related implementation slice id.
            acceptance_criterion: Acceptance criterion under test.
            expected_behavior: Expected behavior.
            severity: Severity label.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            QaValidationResult.
        """
        normalized_title = title.strip()
        if not normalized_title:
            return QaValidationResult(
                ok=False, status_code=400, errors=("QA item title is required.",)
            )
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        project = self._repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            return QaValidationResult(ok=False, status_code=404, errors=("Project not found.",))
        if implementation_slice_id:
            implementation_slice = self._repositories.implementation_slice_repo.getRecord(
                implementation_slice_id
            )
            if implementation_slice is None or implementation_slice.project_id != project_id:
                return QaValidationResult(
                    ok=False,
                    status_code=404,
                    errors=("Implementation slice not found.",),
                )
        qa_item = QaValidationItem(
            id=createRecordId("qa"),
            organization_id=project.organization_id,
            project_id=project.id,
            implementation_slice_id=implementation_slice_id,
            title=normalized_title,
            status=QaStatus.OPEN,
            acceptance_criterion=acceptance_criterion.strip(),
            expected_behavior=expected_behavior.strip(),
            severity=severity.strip() or "medium",
            assigned_qa_user_id=actor_user_id,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        self._repositories.qa_validation_repo.createRecord(qa_item)
        audit_event = self._audit_service.recordEvent(
            event_type="qa_item_created",
            organization_id=qa_item.organization_id,
            project_id=qa_item.project_id,
            record_type="QaValidationItem",
            record_id=qa_item.id,
            safe_summary="QA validation item created.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.QA_REVIEWER,
            customer_visible=False,
            before_after_json={"qaStatus": qa_item.status.value},
            current_time_ms=now_ms,
        )
        return QaValidationResult(
            ok=True,
            status_code=201,
            errors=(),
            qa_item=qa_item,
            audit_events=(audit_event,),
        )

    def updateQaItemStatus(
        self,
        qa_item_id: str,
        status_value: str,
        actor_user_id: str | None,
        actual_behavior: str = "",
        evidence_link: str = "",
        resolution_notes: str = "",
        current_time_ms: int | None = None,
    ) -> QaValidationResult:
        """
        Updates a QA item status and synchronizes linked slice/project state.

        Args:
            qa_item_id: QA item id.
            status_value: Requested QA status value.
            actor_user_id: QA/Admin actor user id.
            actual_behavior: Observed behavior.
            evidence_link: Evidence or artifact link.
            resolution_notes: Resolution notes.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            QaValidationResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        qa_item = self._repositories.qa_validation_repo.getRecord(qa_item_id)
        if qa_item is None:
            return QaValidationResult(ok=False, status_code=404, errors=("QA item not found.",))
        requested_status = parseQaStatus(status_value)
        if requested_status is None or requested_status not in ALLOWED_QA_STATUSES:
            return QaValidationResult(ok=False, status_code=400, errors=("Unsupported QA status.",))
        updated_item = replace(
            qa_item,
            status=requested_status,
            actual_behavior=actual_behavior.strip(),
            evidence_link=evidence_link.strip(),
            resolution_notes=resolution_notes.strip(),
            passed_at_ms=now_ms if requested_status == QaStatus.PASSED else qa_item.passed_at_ms,
            updated_at_ms=now_ms,
        )
        self._repositories.qa_validation_repo.updateRecord(updated_item)
        self.updateSliceForQaStatus(updated_item, requested_status, now_ms)
        self.updateProjectForQaStatus(updated_item.project_id, requested_status, now_ms)
        audit_event = self._audit_service.recordEvent(
            event_type="qa_item_status_changed",
            organization_id=updated_item.organization_id,
            project_id=updated_item.project_id,
            record_type="QaValidationItem",
            record_id=updated_item.id,
            safe_summary=f"QA item status changed to {requested_status.value}.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.QA_REVIEWER,
            customer_visible=False,
            before_after_json={"qaStatus": requested_status.value},
            current_time_ms=now_ms,
        )
        return QaValidationResult(
            ok=True,
            status_code=200,
            errors=(),
            qa_item=updated_item,
            audit_events=(audit_event,),
        )

    def updateSliceForQaStatus(
        self,
        qa_item: QaValidationItem,
        requested_status: QaStatus,
        current_time_ms: int,
    ) -> None:
        """
        Updates linked slice QA status after QA changes.

        Args:
            qa_item: Updated QA item.
            requested_status: Requested QA status.
            current_time_ms: Timestamp for slice update.

        Returns:
            None.
        """
        if qa_item.implementation_slice_id is None:
            return
        implementation_slice = self._repositories.implementation_slice_repo.getRecord(
            qa_item.implementation_slice_id
        )
        if implementation_slice is None:
            return
        if requested_status == QaStatus.FAILED:
            updated_slice = replace(
                implementation_slice,
                status=SliceStatus.QA_FAILED,
                qa_status=QaStatus.FAILED,
                updated_at_ms=current_time_ms,
            )
        elif requested_status == QaStatus.PASSED and self.allQaItemsPassedForSlice(
            implementation_slice.id
        ):
            updated_slice = replace(
                implementation_slice,
                status=SliceStatus.COMPLETE,
                qa_status=QaStatus.PASSED,
                completed_at_ms=current_time_ms,
                updated_at_ms=current_time_ms,
            )
        elif requested_status == QaStatus.BLOCKED:
            updated_slice = replace(
                implementation_slice,
                status=SliceStatus.BLOCKED,
                qa_status=QaStatus.BLOCKED,
                updated_at_ms=current_time_ms,
            )
        else:
            updated_slice = replace(
                implementation_slice,
                qa_status=requested_status,
                updated_at_ms=current_time_ms,
            )
        self._repositories.implementation_slice_repo.updateRecord(updated_slice)

    def updateProjectForQaStatus(
        self,
        project_id: str,
        requested_status: QaStatus,
        current_time_ms: int,
    ) -> None:
        """
        Updates project QA/demo readiness after QA changes.

        Args:
            project_id: Project id.
            requested_status: Requested QA status.
            current_time_ms: Timestamp for project update.

        Returns:
            None.
        """
        project = self._repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            return
        if requested_status == QaStatus.FAILED:
            updated_project = replace(
                project,
                status=ProjectStatus.QA_FAILED_NEEDS_FIXES,
                next_action="Fix failed QA item",
                next_action_owner_role=UserRole.DEVELOPER,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        elif requested_status == QaStatus.PASSED and self.allProjectQaItemsPassed(project_id):
            updated_project = replace(
                project,
                status=ProjectStatus.DEMO_READY,
                next_action="Prepare customer demo review",
                next_action_owner_role=UserRole.QA_REVIEWER,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        elif requested_status in (QaStatus.BLOCKED, QaStatus.NEEDS_CUSTOMER_CLARIFICATION):
            updated_project = replace(
                project,
                status=ProjectStatus.QA_VALIDATION,
                next_action="Resolve QA blocker or clarification",
                next_action_owner_role=UserRole.QA_REVIEWER,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        else:
            updated_project = replace(
                project,
                status=ProjectStatus.QA_VALIDATION,
                next_action="Continue QA validation",
                next_action_owner_role=UserRole.QA_REVIEWER,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        self._repositories.workflow_project_repo.updateRecord(updated_project)

    def allQaItemsPassedForSlice(self, slice_id: str) -> bool:
        """
        Checks whether all QA items for a slice have passed.

        Args:
            slice_id: Implementation slice id.

        Returns:
            True when at least one QA item exists and all are passed.
        """
        qa_items = tuple(
            qa_item
            for qa_item in self._repositories.qa_validation_repo.listRecords()
            if qa_item.implementation_slice_id == slice_id
        )
        return bool(qa_items) and all(qa_item.status == QaStatus.PASSED for qa_item in qa_items)

    def allProjectQaItemsPassed(self, project_id: str) -> bool:
        """
        Checks whether all QA items for a project have passed.

        Args:
            project_id: Project id.

        Returns:
            True when at least one QA item exists and all are passed.
        """
        qa_items = self._repositories.qa_validation_repo.listByProject(project_id)
        slices = self._repositories.implementation_slice_repo.listByProject(project_id)
        qa_passed = bool(qa_items) and all(
            qa_item.status == QaStatus.PASSED for qa_item in qa_items
        )
        slices_complete = bool(slices) and all(
            implementation_slice.status == SliceStatus.COMPLETE for implementation_slice in slices
        )
        return qa_passed and slices_complete


def parseQaStatus(status_value: str) -> QaStatus | None:
    """
    Parses a QA status value safely.

    Args:
        status_value: Raw status value.

    Returns:
        Parsed QaStatus, or None.
    """
    try:
        return QaStatus(status_value)
    except ValueError:
        return None


def createQaValidationErrorPayload(result: QaValidationResult) -> JsonObject:
    """
    Creates a JSON-safe error payload.

    Args:
        result: Failed service result.

    Returns:
        Error payload.
    """
    return {"ok": False, "errors": list(result.errors)}
