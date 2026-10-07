# -*- coding: utf-8 -*-
# gridforge/services/implementationSliceService.py
"""
Creates and updates implementation slices for GridForge.

The service derives buildable implementation slices from approved developer plans,
creates initial QA checks from slice acceptance criteria, enforces developer-only
status updates, and records audit events for build workflow transitions.

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
from gridforge.domain.enums import (
    DeveloperPlanStatus,
    ProjectStatus,
    QaStatus,
    SliceStatus,
    UserRole,
)
from gridforge.domain.records import AuditEvent, ImplementationSlice, JsonObject, QaValidationItem
from gridforge.repositoryBundle import AppRepositories
from gridforge.services.auditService import AuditService, createRecordId, currentTimeMs

DEVELOPER_ALLOWED_SLICE_STATUSES = (
    SliceStatus.READY,
    SliceStatus.ACTIVE,
    SliceStatus.BLOCKED,
    SliceStatus.NEEDS_INTERNAL_REVIEW,
    SliceStatus.NEEDS_QA,
    SliceStatus.DEFERRED,
)


@dataclass(frozen=True)
class ImplementationSliceResult:
    """
    Stores implementation-slice service action outcomes.

    Args:
        ok: Whether the action succeeded.
        status_code: HTTP-friendly status code.
        errors: Validation or guard errors.
        slices: Slices created or affected.
        qa_items: QA items created or affected.
        audit_events: Audit events created by the action.
    """

    ok: bool
    status_code: int
    errors: tuple[str, ...]
    slices: tuple[ImplementationSlice, ...] = ()
    qa_items: tuple[QaValidationItem, ...] = ()
    audit_events: tuple[AuditEvent, ...] = ()


class ImplementationSliceService:
    """
    Creates and updates implementation slices from approved developer plans.
    """

    def __init__(self, repositories: AppRepositories) -> None:
        """
        Initializes the implementation-slice service.

        Args:
            repositories: Repository bundle used by slice workflow.

        Returns:
            None.
        """
        self._repositories = repositories
        self._audit_service = AuditService(repositories.audit_event_repo)

    def createSlicesFromApprovedPlan(
        self,
        project_id: str,
        actor_user_id: str | None,
        current_time_ms: int | None = None,
    ) -> ImplementationSliceResult:
        """
        Creates implementation slices and QA checks from an approved developer plan.

        Args:
            project_id: Project id whose active developer plan should be sliced.
            actor_user_id: Developer/Admin actor user id.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            ImplementationSliceResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        project = self._repositories.workflow_project_repo.getRecord(project_id)
        if project is None:
            return ImplementationSliceResult(
                ok=False, status_code=404, errors=("Project not found.",)
            )
        if not project.active_developer_plan_id:
            return ImplementationSliceResult(
                ok=False,
                status_code=409,
                errors=("Project does not have an active developer plan.",),
            )
        developer_plan = self._repositories.developer_plan_repo.getRecord(
            project.active_developer_plan_id
        )
        if developer_plan is None:
            return ImplementationSliceResult(
                ok=False,
                status_code=409,
                errors=("Active developer plan not found.",),
            )
        if developer_plan.status != DeveloperPlanStatus.APPROVED:
            return ImplementationSliceResult(
                ok=False,
                status_code=409,
                errors=("Developer plan must be approved before creating slices.",),
            )
        existing_slices = self._repositories.implementation_slice_repo.listByProject(project.id)
        if existing_slices:
            return ImplementationSliceResult(
                ok=False,
                status_code=409,
                errors=("Project already has implementation slices.",),
            )
        created_slices: list[ImplementationSlice] = []
        created_qa_items: list[QaValidationItem] = []
        for index, slice_spec in enumerate(developer_plan.implementation_slices_json, start=1):
            implementation_slice = createImplementationSliceFromSpec(
                slice_spec,
                organization_id=developer_plan.organization_id,
                project_id=developer_plan.project_id,
                developer_plan_id=developer_plan.id,
                priority=f"P{index}",
                current_time_ms=now_ms,
            )
            self._repositories.implementation_slice_repo.createRecord(implementation_slice)
            created_slices.append(implementation_slice)
            qa_items = createQaItemsForSlice(implementation_slice, slice_spec, now_ms)
            for qa_item in qa_items:
                self._repositories.qa_validation_repo.createRecord(qa_item)
            created_qa_items.extend(qa_items)
        updated_project = replace(
            project,
            status=ProjectStatus.BUILD_QUEUED,
            next_action="Start implementation slices",
            next_action_owner_role=UserRole.DEVELOPER,
            updated_at_ms=now_ms,
            last_activity_at_ms=now_ms,
        )
        self._repositories.workflow_project_repo.updateRecord(updated_project)
        slice_event = self._audit_service.recordEvent(
            event_type="implementation_slices_created",
            organization_id=project.organization_id,
            project_id=project.id,
            record_type="ImplementationSlice",
            record_id=developer_plan.id,
            safe_summary="Implementation slices created from approved developer plan.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.DEVELOPER,
            customer_visible=False,
            before_after_json={"sliceCount": len(created_slices)},
            current_time_ms=now_ms,
        )
        qa_event = self._audit_service.recordEvent(
            event_type="qa_items_generated",
            organization_id=project.organization_id,
            project_id=project.id,
            record_type="QaValidationItem",
            record_id=developer_plan.id,
            safe_summary="QA validation items generated from implementation slices.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.DEVELOPER,
            customer_visible=False,
            before_after_json={"qaItemCount": len(created_qa_items)},
            current_time_ms=now_ms,
        )
        return ImplementationSliceResult(
            ok=True,
            status_code=201,
            errors=(),
            slices=tuple(created_slices),
            qa_items=tuple(created_qa_items),
            audit_events=(slice_event, qa_event),
        )

    def updateSliceStatus(
        self,
        slice_id: str,
        status_value: str,
        actor_user_id: str | None,
        current_time_ms: int | None = None,
    ) -> ImplementationSliceResult:
        """
        Updates a slice status using allowed developer transitions.

        Args:
            slice_id: Implementation slice id.
            status_value: Requested SliceStatus value.
            actor_user_id: Developer/Admin actor user id.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            ImplementationSliceResult.
        """
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        implementation_slice = self._repositories.implementation_slice_repo.getRecord(slice_id)
        if implementation_slice is None:
            return ImplementationSliceResult(
                ok=False, status_code=404, errors=("Slice not found.",)
            )
        requested_status = parseSliceStatus(status_value)
        if requested_status is None or requested_status not in DEVELOPER_ALLOWED_SLICE_STATUSES:
            return ImplementationSliceResult(
                ok=False,
                status_code=400,
                errors=("Unsupported slice status.",),
            )
        updated_slice = updateSliceForStatus(implementation_slice, requested_status, now_ms)
        self._repositories.implementation_slice_repo.updateRecord(updated_slice)
        self.updateProjectForSliceStatus(updated_slice, requested_status, now_ms)
        audit_event = self._audit_service.recordEvent(
            event_type="implementation_slice_status_changed",
            organization_id=updated_slice.organization_id,
            project_id=updated_slice.project_id,
            record_type="ImplementationSlice",
            record_id=updated_slice.id,
            safe_summary=f"Implementation slice status changed to {requested_status.value}.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.DEVELOPER,
            customer_visible=False,
            before_after_json={"sliceStatus": requested_status.value},
            current_time_ms=now_ms,
        )
        return ImplementationSliceResult(
            ok=True,
            status_code=200,
            errors=(),
            slices=(updated_slice,),
            audit_events=(audit_event,),
        )

    def addSliceBlocker(
        self,
        slice_id: str,
        blocker_note: str,
        actor_user_id: str | None,
        current_time_ms: int | None = None,
    ) -> ImplementationSliceResult:
        """
        Adds a required blocker note and blocks a slice.

        Args:
            slice_id: Implementation slice id.
            blocker_note: Required blocker note.
            actor_user_id: Developer/Admin actor user id.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            ImplementationSliceResult.
        """
        normalized_note = blocker_note.strip()
        if not normalized_note:
            return ImplementationSliceResult(
                ok=False, status_code=400, errors=("Blocker note is required.",)
            )
        now_ms = current_time_ms if current_time_ms is not None else currentTimeMs()
        implementation_slice = self._repositories.implementation_slice_repo.getRecord(slice_id)
        if implementation_slice is None:
            return ImplementationSliceResult(
                ok=False, status_code=404, errors=("Slice not found.",)
            )
        updated_slice = replace(
            implementation_slice,
            status=SliceStatus.BLOCKED,
            blockers_json=implementation_slice.blockers_json + (normalized_note,),
            updated_at_ms=now_ms,
        )
        self._repositories.implementation_slice_repo.updateRecord(updated_slice)
        self.updateProjectForSliceStatus(updated_slice, SliceStatus.BLOCKED, now_ms)
        audit_event = self._audit_service.recordEvent(
            event_type="implementation_slice_blocked",
            organization_id=updated_slice.organization_id,
            project_id=updated_slice.project_id,
            record_type="ImplementationSlice",
            record_id=updated_slice.id,
            safe_summary="Implementation slice blocked.",
            actor_user_id=actor_user_id,
            actor_role=UserRole.DEVELOPER,
            customer_visible=False,
            before_after_json={"blockerCount": len(updated_slice.blockers_json)},
            current_time_ms=now_ms,
        )
        return ImplementationSliceResult(
            ok=True,
            status_code=200,
            errors=(),
            slices=(updated_slice,),
            audit_events=(audit_event,),
        )

    def updateProjectForSliceStatus(
        self,
        implementation_slice: ImplementationSlice,
        requested_status: SliceStatus,
        current_time_ms: int,
    ) -> None:
        """
        Updates project status for developer-side slice transitions.

        Args:
            implementation_slice: Updated implementation slice.
            requested_status: Requested slice status.
            current_time_ms: Timestamp for project update.

        Returns:
            None.
        """
        project = self._repositories.workflow_project_repo.getRecord(
            implementation_slice.project_id
        )
        if project is None:
            return
        project_status = project.status
        next_action = project.next_action
        next_action_owner_role = project.next_action_owner_role
        if requested_status == SliceStatus.ACTIVE:
            project_status = ProjectStatus.BUILD_ACTIVE
            next_action = "Complete active implementation slice"
            next_action_owner_role = UserRole.DEVELOPER
        elif requested_status == SliceStatus.BLOCKED:
            project_status = ProjectStatus.BUILD_BLOCKED
            next_action = "Resolve implementation blocker"
            next_action_owner_role = UserRole.DEVELOPER
        elif requested_status == SliceStatus.NEEDS_QA:
            project_status = ProjectStatus.QA_VALIDATION
            next_action = "Run QA validation"
            next_action_owner_role = UserRole.QA_REVIEWER
        elif requested_status == SliceStatus.NEEDS_INTERNAL_REVIEW:
            project_status = ProjectStatus.INTERNAL_REVIEW
            next_action = "Review completed implementation slice"
            next_action_owner_role = UserRole.DEVELOPER
        self._repositories.workflow_project_repo.updateRecord(
            replace(
                project,
                status=project_status,
                next_action=next_action,
                next_action_owner_role=next_action_owner_role,
                updated_at_ms=current_time_ms,
                last_activity_at_ms=current_time_ms,
            )
        )


def createImplementationSliceFromSpec(
    slice_spec: JsonObject,
    *,
    organization_id: str,
    project_id: str,
    developer_plan_id: str,
    priority: str,
    current_time_ms: int,
) -> ImplementationSlice:
    """
    Creates an implementation slice from a developer-plan slice spec.

    Args:
        slice_spec: Developer-plan slice spec.
        organization_id: Owning organization id.
        project_id: Owning project id.
        developer_plan_id: Source developer plan id.
        priority: Derived priority label.
        current_time_ms: Timestamp for created/updated fields.

    Returns:
        ImplementationSlice domain record.
    """
    return ImplementationSlice(
        id=createRecordId("slice"),
        organization_id=organization_id,
        project_id=project_id,
        developer_plan_id=developer_plan_id,
        name=str(slice_spec.get("name", "Implementation Slice")),
        description=str(slice_spec.get("goal", "Build a verified implementation slice.")),
        status=SliceStatus.READY,
        priority=priority,
        scope_items_json=asStringTuple(slice_spec.get("scopeItems", ())),
        related_entities_json=asStringTuple(slice_spec.get("relatedEntities", ())),
        related_routes_json=asStringTuple(slice_spec.get("relatedRoutes", ())),
        required_tests_json=asStringTuple(slice_spec.get("tests", ())),
        definition_of_done_json=asStringTuple(slice_spec.get("acceptanceCriteria", ())),
        estimated_complexity=str(slice_spec.get("estimatedComplexity", "medium")),
        created_at_ms=current_time_ms,
        updated_at_ms=current_time_ms,
    )


def createQaItemsForSlice(
    implementation_slice: ImplementationSlice,
    slice_spec: JsonObject,
    current_time_ms: int,
) -> tuple[QaValidationItem, ...]:
    """
    Creates initial QA validation items from slice acceptance criteria/tests.

    Args:
        implementation_slice: Created implementation slice.
        slice_spec: Developer-plan slice spec.
        current_time_ms: Timestamp for created/updated fields.

    Returns:
        Tuple of QA validation items.
    """
    acceptance_criteria = asStringTuple(slice_spec.get("acceptanceCriteria", ()))
    tests = asStringTuple(slice_spec.get("tests", ()))
    source_items = acceptance_criteria or tests or ("Slice meets definition of done.",)
    return tuple(
        QaValidationItem(
            id=createRecordId("qa"),
            organization_id=implementation_slice.organization_id,
            project_id=implementation_slice.project_id,
            implementation_slice_id=implementation_slice.id,
            title=f"QA: {implementation_slice.name} — {index}",
            status=QaStatus.OPEN,
            requirement_reference=implementation_slice.name,
            acceptance_criterion=item,
            expected_behavior=item,
            created_at_ms=current_time_ms,
            updated_at_ms=current_time_ms,
        )
        for index, item in enumerate(source_items, start=1)
    )


def updateSliceForStatus(
    implementation_slice: ImplementationSlice,
    requested_status: SliceStatus,
    current_time_ms: int,
) -> ImplementationSlice:
    """
    Applies status-specific slice field updates.

    Args:
        implementation_slice: Current implementation slice.
        requested_status: Requested status.
        current_time_ms: Timestamp for update fields.

    Returns:
        Updated ImplementationSlice.
    """
    started_at_ms = implementation_slice.started_at_ms
    if requested_status == SliceStatus.ACTIVE and started_at_ms is None:
        started_at_ms = current_time_ms
    return replace(
        implementation_slice,
        status=requested_status,
        started_at_ms=started_at_ms,
        qa_status=QaStatus.OPEN
        if requested_status == SliceStatus.NEEDS_QA
        else implementation_slice.qa_status,
        updated_at_ms=current_time_ms,
    )


def parseSliceStatus(status_value: str) -> SliceStatus | None:
    """
    Parses a SliceStatus value safely.

    Args:
        status_value: Raw status value.

    Returns:
        Parsed SliceStatus, or None.
    """
    try:
        return SliceStatus(status_value)
    except ValueError:
        return None


def asStringTuple(value: object) -> tuple[str, ...]:
    """
    Converts a value to a tuple of strings.

    Args:
        value: List-like or tuple-like value.

    Returns:
        Tuple of string values.
    """
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


def createImplementationSliceErrorPayload(result: ImplementationSliceResult) -> JsonObject:
    """
    Creates a JSON-safe error payload.

    Args:
        result: Failed service result.

    Returns:
        Error payload.
    """
    return {"ok": False, "errors": list(result.errors)}
