# -*- coding: utf-8 -*-
# tests/test_intakeService.py
"""
Tests GridForge guided intake creation service.

The tests verify validation, normalization, record creation, missing-detail
tracking, project status selection, and audit-event creation.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import IntakeStatus, ProjectStatus, UserRole
from gridforge.services.intakeService import IntakeService, normalizeIntakePayload
from tests.fakes import createFakeRepositories

CURRENT_TIME_MS = 1000


def test_intakeServiceCreatesOrganizationProjectIntakeAndAuditEvent() -> None:
    """
    Verifies a valid public intake creates all Phase 2 records.

    Returns:
        None.
    """
    repositories = createFakeRepositories()
    result = IntakeService(repositories).createPublicIntake(
        createValidIntakePayload(),
        current_time_ms=CURRENT_TIME_MS,
    )

    assert result.ok is True
    assert result.status_code == 201
    assert result.organization is not None
    assert result.project is not None
    assert result.intake is not None
    assert result.audit_event is not None
    assert result.project.status == ProjectStatus.INTAKE_READY_FOR_BLUEPRINT
    assert result.intake.status == IntakeStatus.SUBMITTED
    assert result.intake.completion_percent == 100
    assert result.audit_event.event_type == "intake_submitted"
    assert result.audit_event.actor_role == UserRole.PUBLIC_VISITOR
    assert repositories.organization_repo.getRecord(result.organization.id) == result.organization
    assert repositories.workflow_project_repo.getRecord(result.project.id) == result.project
    assert repositories.intake_repo.getRecord(result.intake.id) == result.intake
    assert repositories.audit_event_repo.listByProject(result.project.id) == (result.audit_event,)


def test_intakeServiceTracksMissingDetailsAndRiskFlags() -> None:
    """
    Verifies incomplete intakes are marked for follow-up with risk flags.

    Returns:
        None.
    """
    payload = createValidIntakePayload()
    payload.pop("usersPermissions")
    payload.pop("workflowLifecycle")
    payload.pop("statuses")
    payload.pop("formsDataFiles")
    payload["workflowDescription"] = "We need an offline-first native mobile app."
    payload["budgetRange"] = "Not sure yet"

    result = IntakeService(createFakeRepositories()).createPublicIntake(
        payload,
        current_time_ms=CURRENT_TIME_MS,
    )

    assert result.project is not None
    assert result.intake is not None
    assert result.project.status == ProjectStatus.INTAKE_NEEDS_FOLLOW_UP
    assert result.intake.status == IntakeStatus.NEEDS_FOLLOW_UP
    assert "users_and_permissions" in result.intake.missing_detail_categories
    assert "workflow_lifecycle" in result.intake.missing_detail_categories
    assert "data_forms_and_files" in result.intake.missing_detail_categories
    assert "offline_first_requested" in result.intake.risk_flags
    assert "native_mobile_requested" in result.intake.risk_flags
    assert "unclear_budget" in result.intake.risk_flags
    assert "Who will use the app" in result.intake.follow_up_questions[0]


def test_intakeServiceRejectsInvalidPayload() -> None:
    """
    Verifies validation rejects missing fields, invalid email, and missing consent.

    Returns:
        None.
    """
    result = IntakeService(createFakeRepositories()).createPublicIntake(
        {
            "organizationName": "",
            "primaryContactName": "Pat Customer",
            "primaryContactEmail": "not-an-email",
            "workflowType": "Discovery",
            "workflowDescription": "Build a system.",
            "aiConsentAccepted": False,
            "termsAccepted": False,
        },
        current_time_ms=CURRENT_TIME_MS,
    )

    assert result.ok is False
    assert result.status_code == 400
    assert result.errors["organizationName"] == "This field is required."
    assert result.errors["primaryContactEmail"] == "Enter a valid email address."
    assert result.errors["aiConsentAccepted"] == "AI planning-draft consent is required."
    assert result.errors["termsAccepted"] == "Planning-draft terms acknowledgement is required."


def test_normalizeIntakePayloadHandlesFormsAndCurrentTools() -> None:
    """
    Verifies form-style values are normalized for service processing.

    Returns:
        None.
    """
    normalized = normalizeIntakePayload(
        {
            "organizationName": " Example Co ",
            "currentTools": " spreadsheets, email ,, docs ",
            "aiConsentAccepted": "on",
            "termsAccepted": "accepted",
        }
    )

    assert normalized["organizationName"] == "Example Co"
    assert normalized["currentTools"] == ("spreadsheets", "email", "docs")
    assert normalized["aiConsentAccepted"] is True
    assert normalized["termsAccepted"] is True


def createValidIntakePayload() -> dict[str, object]:
    """
    Creates a complete sample intake payload.

    Returns:
        Valid intake payload.
    """
    return {
        "organizationName": "GridForge Systems",
        "primaryContactName": "Sean Swoboda",
        "primaryContactEmail": "sean@example.test",
        "workflowType": "Customer discovery",
        "workflowDescription": "Turn messy intake into a structured blueprint.",
        "currentTools": ["spreadsheets", "email", "AI chats"],
        "desiredOutcome": "A structured blueprint and support flow.",
        "successDefinition": "Clear workflow from intake to support.",
        "usersPermissions": "Admins, analysts, developers, QA, support, customers.",
        "workflowLifecycle": "Lead captured to support.",
        "statuses": "Lead, intake, blueprint, build, QA, handoff, support.",
        "formsDataFiles": "Organization, project, intake, blueprint, plan, QA.",
        "dashboardsReports": "Command center, review queue, exports.",
        "integrationsNotifications": "Email and AI provider later.",
        "additionalContext": "Cloud-first and web-first.",
        "budgetRange": "Not sure yet",
        "aiConsentAccepted": True,
        "termsAccepted": True,
    }
