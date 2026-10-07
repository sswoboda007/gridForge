# -*- coding: utf-8 -*-
# gridforge/services/supportRequestService.py
"""
Creates and updates support requests for GridForge.

The service accepts support/enhancement requests only after a project reaches the
handoff/support portion of the lifecycle, updates request status, maintains
project support state, and records audit events.

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
from gridforge.domain.enums import ProjectStatus, SupportStatus, UserRole
from gridforge.domain.records import AuditEvent, JsonObject, SupportRequest
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import AuditService, createRecordId, currentTimeMs

SUPPORT_READY_PROJECT_STATUSES = (
    ProjectStatus.HANDOFF_READY,
    ProjectStatus.ACCEPTED_DELIVERED,
    ProjectStatus.SUPPORT_RETAINER,
)
ALLOWED_SUPPORT_STATUSES = (
    SupportStatus.OPEN,
    SupportStatus.IN_REVIEW,
    SupportStatus.IN_PROGRESS,
    SupportStatus.WAITING_ON_CUSTOMER,
    SupportStatus.RESOLVED,
    SupportStatus.ARCHIVED,
)


@dataclass(frozen=True)
class SupportRequestResult:
    """
    Stores support request service outcomes.

    Args:
        ok: Whether the action succeeded.
        status_code: HTTP-friendly status code.
        errors: Validation or guard errors.
        support_request: Support request created or updated.
        audit_events: Audit events created by the action.
    """

    ok: bool
    status_code: int
    errors: tuple[str, ...]
    support_request: SupportRequest | None = None
    audit_events: tuple[AuditEvent, ...] = ()


class SupportRequestService:
    """
    Creates and updates support/enhancement requests.
    """

    def __init__(self, repositories: AppRepositories) -> None:
        """
        Initializes the support request service.

        Args:
            repositories: Repository bundle used by support workflow.

        Returns:
            None.
        """
        self._repositories = repositories
        self._audit_service = AuditService(repositories.audit_event_repo)

    def createSupportRequest(
        self,
        project_id: str,
        title: str,
        customer_description: str,
        actor_user_id: str | None,
        request_type: str = "support",
        priority: str = "medium",
        current_time_ms: int | None = None,
    ) -> SupportRequestResult:
        """
        Creates a support request after project handoff/support readiness.

        Args:
            project_id: Project id.
            title: Request title.
            customer_description: Customer-visible request description.
            actor_user_id: Support/Admin actor id.
            request_type: Request type label.
            priority: Priority label.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            SupportRequestResult.
        """
        normalized_title = title.strip()
        normalized_description = customer_description.strip()
        if not normalized_title:
            return SupportRequestResult(
                ok=False, status_code=400, errors=("Support request title is required.",)
            )
        if not normalized_description:
            return SupportRequestResult(
                ok=False, status_code=400, errors=("Support request description is required.",)
            )
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        project = self._repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            return SupportRequestResult(ok=False, status_code=404, errors=("Project not found.",))
        if project.status not in SUPPORT_READY_PROJECT_STATUSES:
            return SupportRequestResult(
                ok=False,
                status_code=409,
                errors=("Support requests require handoff or support-ready project status.",),
            )
        support_request = SupportRequest(
            id=createRecordId("support"),
            organization_id=project.organization_id,
            project_id=project.id,
            title=normalized_title,
            request_type=request_type.strip() or "support",
            priority=priority.strip() or "medium",
            status=SupportStatus.OPEN,
            customer_description=normalized_description,
            assigned_support_user_id=actor_user_id,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        self._repositories.support_request_repo.createRecord(support_request)
        self._repositories.workflow_project_repo.updateRecord(
            replace(
                project,
                status=ProjectStatus.SUPPORT_RETAINER,
                next_action="Review open support request",
                next_action_owner_role=UserRole.SUPPORT_MANAGER,
                updated_at_ms=now_ms,
                last_activity_at_ms=now_ms,
            )
        )
        audit_event = self._audit_service.recordEvent(
            event_type="support_request_created",
            organization_id=support_request.organization_id,
            project_id=support_request.project_id,
            record_type="SupportRequest",
            record_id=support_request.id,
            safe_summary="Support request created.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.SUPPORT_MANAGER,
            customer_visible=False,
            before_after_json={"supportStatus": support_request.status.value},
            current_time_ms=now_ms,
        )
        return SupportRequestResult(
            ok=True,
            status_code=201,
            errors=(),
            support_request=support_request,
            audit_events=(audit_event,),
        )

    def updateSupportRequestStatus(
        self,
        support_request_id: str,
        status_value: str,
        actor_user_id: str | None,
        internal_notes: str = "",
        customer_visible_response: str = "",
        current_time_ms: int | None = None,
    ) -> SupportRequestResult:
        """
        Updates support request status and resolution fields.

        Args:
            support_request_id: Support request id.
            status_value: Requested support status value.
            actor_user_id: Support/Admin actor id.
            internal_notes: Internal support notes.
            customer_visible_response: Customer-visible response.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            SupportRequestResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        support_request = self._repositories.support_request_repo.getRecord(support_request_id)
        if support_request is None:
            return SupportRequestResult(
                ok=False, status_code=404, errors=("Support request not found.",)
            )
        requested_status = parseSupportStatus(status_value)
        if requested_status is None or requested_status not in ALLOWED_SUPPORT_STATUSES:
            return SupportRequestResult(
                ok=False, status_code=400, errors=("Unsupported support status.",)
            )
        updated_request = replace(
            support_request,
            status=requested_status,
            internal_notes=internal_notes.strip() or support_request.internal_notes,
            customer_visible_response=customer_visible_response.strip()
            or support_request.customer_visible_response,
            resolved_at_ms=now_ms
            if requested_status == SupportStatus.RESOLVED
            else support_request.resolved_at_ms,
            updated_at_ms=now_ms,
        )
        self._repositories.support_request_repo.updateRecord(updated_request)
        audit_event = self._audit_service.recordEvent(
            event_type="support_request_status_changed",
            organization_id=updated_request.organization_id,
            project_id=updated_request.project_id,
            record_type="SupportRequest",
            record_id=updated_request.id,
            safe_summary=f"Support request status changed to {requested_status.value}.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.SUPPORT_MANAGER,
            customer_visible=False,
            before_after_json={"supportStatus": requested_status.value},
            current_time_ms=now_ms,
        )
        return SupportRequestResult(
            ok=True,
            status_code=200,
            errors=(),
            support_request=updated_request,
            audit_events=(audit_event,),
        )


def parseSupportStatus(status_value: str) -> SupportStatus | None:
    """
    Parses a support status value safely.

    Args:
        status_value: Raw status value.

    Returns:
        Parsed SupportStatus, or None.
    """
    try:
        return SupportStatus(status_value)
    except ValueError:
        return None


def createSupportRequestErrorPayload(result: SupportRequestResult) -> JsonObject:
    """
    Creates a JSON-safe support error payload.

    Args:
        result: Failed support service result.

    Returns:
        Error payload.
    """
    return {"ok": False, "errors": list(result.errors)}
