# -*- coding: utf-8 -*-
# gridforge/services/blueprintReviewService.py
"""
Reviews and approves customer-facing blueprints for GridForge.

The service applies human review and customer approval transitions while keeping
internal notes, validation details, raw AI references, and developer-only data out
of customer-facing projections.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass, replace
from typing import Mapping

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import ApprovalStatus, BlueprintStatus, ProjectStatus, UserRole
from gridforge.domain.records import (
    AuditEvent,
    CustomerBlueprint,
    JsonObject,
    blueprintToCustomerSafeDict,
)
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import AuditService, currentTimeMs


@dataclass(frozen=True)
class BlueprintReviewResult:
    """
    Stores the outcome of blueprint review actions.

    Args:
        ok: Whether the action succeeded.
        status_code: HTTP-friendly status code.
        errors: Validation or guard errors.
        blueprint: Updated blueprint when successful.
        audit_event: Created audit event when successful.
    """

    ok: bool
    status_code: int
    errors: tuple[str, ...]
    blueprint: CustomerBlueprint | None = None
    audit_event: AuditEvent | None = None


class BlueprintReviewService:
    """
    Applies internal review and customer approval transitions.
    """

    def __init__(self, repositories: AppRepositories) -> None:
        """
        Initializes the review service.

        Args:
            repositories: Repository bundle used by review workflow.

        Returns:
            None.
        """
        self._repositories = repositories
        self._audit_service = AuditService(repositories.audit_event_repo)

    def markReadyForCustomerReview(
        self,
        blueprint_id: str,
        reviewer_user_id: str | None,
        reviewer_notes: str = "",
        current_time_ms: int | None = None,
    ) -> BlueprintReviewResult:
        """
        Marks a validated draft blueprint ready for customer review.

        Args:
            blueprint_id: Blueprint identifier.
            reviewer_user_id: Internal reviewer user id.
            reviewer_notes: Internal-only review notes.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            BlueprintReviewResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        blueprint = self._repositories.blueprint_repo.getRecord(blueprint_id)
        if blueprint is None:
            return BlueprintReviewResult(
                ok=False, status_code=404, errors=("Blueprint not found.",)
            )
        if blueprint.status not in (
            BlueprintStatus.NEEDS_INTERNAL_REVIEW,
            BlueprintStatus.CHANGES_REQUESTED,
        ):
            return BlueprintReviewResult(
                ok=False,
                status_code=409,
                errors=("Blueprint is not awaiting internal review.",),
            )
        updated_blueprint = replace(
            blueprint,
            status=BlueprintStatus.READY_FOR_CUSTOMER_REVIEW,
            internal_reviewer_notes=reviewer_notes.strip(),
            human_reviewer_user_id=reviewer_user_id,
            human_reviewed_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        self._repositories.blueprint_repo.updateRecord(updated_blueprint)
        self.updateProjectForBlueprintReview(updated_blueprint, now_ms)
        audit_event = self._audit_service.recordEvent(
            event_type="blueprint_reviewed",
            organization_id=updated_blueprint.organization_id,
            project_id=updated_blueprint.project_id,
            record_type="CustomerBlueprint",
            record_id=updated_blueprint.id,
            safe_summary="Blueprint marked ready for customer review.",
            actor_user_id=reviewer_user_id,
            actor_role=UserRole.WORKFLOW_ANALYST,
            customer_visible=False,
            before_after_json={"blueprintStatus": updated_blueprint.status.value},
            current_time_ms=now_ms,
        )
        return BlueprintReviewResult(
            ok=True,
            status_code=200,
            errors=(),
            blueprint=updated_blueprint,
            audit_event=audit_event,
        )

    def approveBlueprint(
        self,
        blueprint_id: str,
        approver_user_id: str | None,
        current_time_ms: int | None = None,
    ) -> BlueprintReviewResult:
        """
        Approves a customer-reviewed blueprint and locks the scope baseline.

        Args:
            blueprint_id: Blueprint identifier.
            approver_user_id: Customer approver or admin override user id.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            BlueprintReviewResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        blueprint = self._repositories.blueprint_repo.getRecord(blueprint_id)
        if blueprint is None:
            return BlueprintReviewResult(
                ok=False, status_code=404, errors=("Blueprint not found.",)
            )
        if blueprint.status != BlueprintStatus.READY_FOR_CUSTOMER_REVIEW:
            return BlueprintReviewResult(
                ok=False,
                status_code=409,
                errors=("Blueprint is not ready for customer approval.",),
            )
        updated_blueprint = replace(
            blueprint,
            status=BlueprintStatus.APPROVED,
            customer_approval_status=ApprovalStatus.APPROVED,
            customer_approved_by_user_id=approver_user_id,
            customer_approved_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        self._repositories.blueprint_repo.updateRecord(updated_blueprint)
        self.updateProjectForBlueprintApproval(updated_blueprint, now_ms)
        audit_event = self._audit_service.recordEvent(
            event_type="blueprint_approved",
            organization_id=updated_blueprint.organization_id,
            project_id=updated_blueprint.project_id,
            record_type="CustomerBlueprint",
            record_id=updated_blueprint.id,
            safe_summary="Customer blueprint approved.",
            actor_user_id=approver_user_id,
            actor_role=UserRole.CLIENT_STAKEHOLDER,
            customer_visible=True,
            before_after_json={"blueprintStatus": updated_blueprint.status.value},
            current_time_ms=now_ms,
        )
        return BlueprintReviewResult(
            ok=True,
            status_code=200,
            errors=(),
            blueprint=updated_blueprint,
            audit_event=audit_event,
        )

    def requestBlueprintChanges(
        self,
        blueprint_id: str,
        requester_user_id: str | None,
        change_note: str,
        current_time_ms: int | None = None,
    ) -> BlueprintReviewResult:
        """
        Records customer-requested blueprint changes.

        Args:
            blueprint_id: Blueprint identifier.
            requester_user_id: Customer or reviewer user id.
            change_note: Required customer-visible change request.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            BlueprintReviewResult.
        """
        normalized_note = change_note.strip()
        if not normalized_note:
            return BlueprintReviewResult(
                ok=False, status_code=400, errors=("Change note is required.",)
            )
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        blueprint = self._repositories.blueprint_repo.getRecord(blueprint_id)
        if blueprint is None:
            return BlueprintReviewResult(
                ok=False, status_code=404, errors=("Blueprint not found.",)
            )
        if blueprint.status != BlueprintStatus.READY_FOR_CUSTOMER_REVIEW:
            return BlueprintReviewResult(
                ok=False,
                status_code=409,
                errors=("Blueprint is not ready for customer feedback.",),
            )
        updated_blueprint = replace(
            blueprint,
            status=BlueprintStatus.CHANGES_REQUESTED,
            customer_approval_status=ApprovalStatus.CHANGES_REQUESTED,
            customer_visible_notes=normalized_note,
            updated_at_ms=now_ms,
        )
        self._repositories.blueprint_repo.updateRecord(updated_blueprint)
        self.updateProjectForBlueprintChangeRequest(updated_blueprint, now_ms)
        audit_event = self._audit_service.recordEvent(
            event_type="blueprint_changes_requested",
            organization_id=updated_blueprint.organization_id,
            project_id=updated_blueprint.project_id,
            record_type="CustomerBlueprint",
            record_id=updated_blueprint.id,
            safe_summary="Customer requested blueprint changes.",
            actor_user_id=requester_user_id,
            actor_role=UserRole.CUSTOMER_CONTACT,
            customer_visible=True,
            before_after_json={"blueprintStatus": updated_blueprint.status.value},
            current_time_ms=now_ms,
        )
        return BlueprintReviewResult(
            ok=True,
            status_code=200,
            errors=(),
            blueprint=updated_blueprint,
            audit_event=audit_event,
        )

    def createCustomerSafeView(self, blueprint: CustomerBlueprint) -> Mapping[str, object]:
        """
        Creates a customer-safe blueprint projection.

        Args:
            blueprint: Blueprint to project.

        Returns:
            Customer-safe blueprint mapping.
        """
        return blueprintToCustomerSafeDict(blueprint)

    def updateProjectForBlueprintReview(
        self, blueprint: CustomerBlueprint, current_time_ms: int
    ) -> None:
        """
        Updates project status after internal blueprint review.

        Args:
            blueprint: Reviewed blueprint.
            current_time_ms: Timestamp for project update.

        Returns:
            None.
        """
        project = self._repositories.workflow_project_repo.getRecord(blueprint.project_id)
        if project is None:
            return
        self._repositories.workflow_project_repo.updateRecord(
            replace(
                project,
                status=ProjectStatus.BLUEPRINT_READY_FOR_CUSTOMER_REVIEW,
                next_action="Customer reviews blueprint",
                next_action_owner_role=UserRole.CLIENT_STAKEHOLDER,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        )

    def updateProjectForBlueprintApproval(
        self, blueprint: CustomerBlueprint, current_time_ms: int
    ) -> None:
        """
        Updates project status after customer blueprint approval.

        Args:
            blueprint: Approved blueprint.
            current_time_ms: Timestamp for project update.

        Returns:
            None.
        """
        project = self._repositories.workflow_project_repo.getRecord(blueprint.project_id)
        if project is None:
            return
        self._repositories.workflow_project_repo.updateRecord(
            replace(
                project,
                status=ProjectStatus.BLUEPRINT_APPROVED,
                approved_blueprint_id=blueprint.id,
                next_action="Draft developer implementation plan",
                next_action_owner_role=UserRole.DEVELOPER,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        )

    def updateProjectForBlueprintChangeRequest(
        self, blueprint: CustomerBlueprint, current_time_ms: int
    ) -> None:
        """
        Updates project status after customer change request.

        Args:
            blueprint: Blueprint with requested changes.
            current_time_ms: Timestamp for project update.

        Returns:
            None.
        """
        project = self._repositories.workflow_project_repo.getRecord(blueprint.project_id)
        if project is None:
            return
        self._repositories.workflow_project_repo.updateRecord(
            replace(
                project,
                status=ProjectStatus.BLUEPRINT_CHANGES_REQUESTED,
                next_action="Review requested blueprint changes",
                next_action_owner_role=UserRole.WORKFLOW_ANALYST,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        )


def createReviewErrorPayload(result: BlueprintReviewResult) -> JsonObject:
    """
    Creates a JSON-safe error response payload.

    Args:
        result: Failed review result.

    Returns:
        Error payload.
    """
    return {"ok": False, "errors": list(result.errors)}
