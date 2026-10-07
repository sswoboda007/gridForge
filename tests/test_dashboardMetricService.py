# -*- coding: utf-8 -*-
# tests/test_dashboardMetricService.py
"""
Tests GridForge dashboard metric aggregation.

The tests verify Phase 7 command-center metrics for pipeline, review queues,
build/QA state, support state, exports, and recent audit events.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import replace

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import ProjectStatus, QaStatus, UserRole
from gridforge.services.dashboardMetricService import DashboardMetricService
from gridforge.services.exportService import ExportService
from gridforge.services.implementationSliceService import ImplementationSliceService
from gridforge.services.qaValidationService import QaValidationService
from gridforge.services.supportRequestService import SupportRequestService
from tests.fakes import createFakeRepositories
from tests.test_developerPlanService import CURRENT_TIME_MS
from tests.test_implementationSliceService import createApprovedDeveloperPlan


def test_dashboardMetricServiceAggregatesMvpMetrics() -> None:
    """
    Verifies command-center metrics aggregate workflow state.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    project_id, _ = createApprovedDeveloperPlan(repositories)
    slice_result = ImplementationSliceService(repositories).createSlicesFromApprovedPlan(
        project_id,
        actor_user_id="demo_developer",
        current_time_ms=CURRENT_TIME_MS + 7,
    )
    QaValidationService(repositories).updateQaItemStatus(
        slice_result.qa_items[0].id,
        status_value=QaStatus.FAILED.value,
        actor_user_id="demo_qa_reviewer",
        current_time_ms=CURRENT_TIME_MS + 8,
    )
    project = repositories.workflow_project_repo.getRecord(project_id)
    assert project is not None
    repositories.workflow_project_repo.updateRecord(
        replace(project, status=ProjectStatus.HANDOFF_READY, next_action_due_at_ms=CURRENT_TIME_MS)
    )
    SupportRequestService(repositories).createSupportRequest(
        project_id,
        title="Post-handoff support",
        customer_description="Need help with a support item.",
        actor_user_id="demo_support_manager",
        current_time_ms=CURRENT_TIME_MS + 9,
    )
    ExportService(repositories).buildProjectExport(
        project_id,
        export_type="customer_summary",
        actor_user_id="demo_platform_admin",
        actor_roles=(UserRole.PLATFORM_ADMIN,),
        current_time_ms=CURRENT_TIME_MS + 10,
    )

    metrics = DashboardMetricService(repositories).buildDashboardMetrics(
        current_time_ms=CURRENT_TIME_MS + 11
    )

    assert metrics.counts["totalActiveProjects"] == 1
    assert metrics.counts["blueprintsApproved"] == 1
    assert metrics.counts["developerPlansApproved"] == 1
    assert metrics.counts["blockedBuilds"] == 1
    assert metrics.counts["qaFailed"] == 1
    assert metrics.counts["supportRetainer"] == 1
    assert metrics.counts["overdueNextActions"] == 1
    assert metrics.review_queue["qaFailures"] == 1
    assert metrics.project_status_counts[ProjectStatus.SUPPORT_RETAINER.value] == 1
    assert metrics.recent_audit_events[0].event_type == "export_downloaded"
