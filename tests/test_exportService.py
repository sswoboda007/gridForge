# -*- coding: utf-8 -*-
# tests/test_exportService.py
"""
Tests GridForge CSV export service behavior.

The tests verify customer-safe redaction, internal-role requirements, export/audit
records, QA handoff CSVs, and platform audit exports.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import UserRole
from gridforge.services.exportService import ExportService
from gridforge.services.implementationSliceService import ImplementationSliceService
from tests.fakes import createFakeRepositories
from tests.test_developerPlanService import CURRENT_TIME_MS
from tests.test_implementationSliceService import createApprovedDeveloperPlan


def test_exportServiceBuildsCustomerSafeExportsAndAuditRecords() -> None:
    """
    Verifies customer-safe exports exclude internal/developer/AI fields.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    service = ExportService(repositories)

    result = service.buildProjectExport(
        project_id,
        export_type="customer_summary",
        actor_user_id="demo_customer_contact",
        actor_roles=(UserRole.CUSTOMER_CONTACT,),
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    blueprint_result = service.buildProjectExport(
        project_id,
        export_type="blueprint_summary",
        actor_user_id="demo_customer_contact",
        actor_roles=(UserRole.CUSTOMER_CONTACT,),
        current_time_ms=CURRENT_TIME_MS + 8,
    )

    assert result.ok is True
    assert "internal_notes" not in result.content
    assert "developer_plan" not in result.content
    assert "raw_response_ref" not in blueprint_result.content
    assert "validation_errors" not in blueprint_result.content
    assert result.export_record is not None
    assert result.export_record.restricted_fields_excluded is True
    assert result.audit_event is not None
    assert result.audit_event.event_type == "export_downloaded"


def test_exportServiceRequiresInternalRoleForInternalExports() -> None:
    """
    Verifies developer-plan exports require internal roles.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    service = ExportService(repositories)

    denied_result = service.buildProjectExport(
        project_id,
        export_type="developer_plan_internal",
        actor_user_id="demo_customer_contact",
        actor_roles=(UserRole.CUSTOMER_CONTACT,),
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    allowed_result = service.buildProjectExport(
        project_id,
        export_type="developer_plan_internal",
        actor_user_id="demo_developer",
        actor_roles=(UserRole.DEVELOPER,),
        current_time_ms=CURRENT_TIME_MS + 8,
    )

    assert denied_result.status_code == 403
    assert allowed_result.status_code == 200
    assert "implementation_overview" in allowed_result.content
    assert allowed_result.export_record is not None
    assert allowed_result.export_record.restricted_fields_excluded is False


def test_exportServiceBuildsQaHandoffAndAuditExports() -> None:
    """
    Verifies QA handoff and audit CSV exports are recorded.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    service = ExportService(repositories)

    qa_result = service.buildProjectExport(
        project_id,
        export_type="qa_handoff",
        actor_user_id="demo_qa_reviewer",
        actor_roles=(UserRole.QA_REVIEWER,),
        current_time_ms=CURRENT_TIME_MS + 8,
    )
    denied_audit_result = service.buildAuditExport(
        actor_user_id="demo_developer",
        actor_roles=(UserRole.DEVELOPER,),
        current_time_ms=CURRENT_TIME_MS + 9,
    )
    audit_result = service.buildAuditExport(
        actor_user_id="demo_platform_admin",
        actor_roles=(UserRole.PLATFORM_ADMIN,),
        current_time_ms=CURRENT_TIME_MS + 10,
    )

    assert qa_result.status_code == 200
    assert "acceptance_criterion" in qa_result.content
    assert denied_audit_result.status_code == 403
    assert audit_result.status_code == 200
    assert "event_type" in audit_result.content
