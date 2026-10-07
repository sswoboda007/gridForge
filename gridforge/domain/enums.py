# -*- coding: utf-8 -*-
# gridforge/domain/enums.py
"""
Defines shared GridForge workflow enums.

Enums centralize role, lifecycle, and status values used by domain records,
repositories, route guards, dashboards, exports, and audit events.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from enum import StrEnum

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)


class UserRole(StrEnum):
    """
    Enumerates role identities used by GridForge access policies.
    """

    PUBLIC_VISITOR = "public_visitor"
    CUSTOMER_CONTACT = "customer_contact"
    CLIENT_STAKEHOLDER = "client_stakeholder"
    PLATFORM_ADMIN = "platform_admin"
    WORKFLOW_ANALYST = "workflow_analyst"
    DEVELOPER = "developer"
    QA_REVIEWER = "qa_reviewer"
    SUPPORT_MANAGER = "support_manager"
    READ_ONLY_EXECUTIVE = "read_only_executive"


class ProjectStatus(StrEnum):
    """
    Enumerates the Customer Workflow Project lifecycle.
    """

    LEAD_CAPTURED = "lead_captured"
    INTAKE_IN_PROGRESS = "intake_in_progress"
    INTAKE_NEEDS_FOLLOW_UP = "intake_needs_follow_up"
    INTAKE_READY_FOR_BLUEPRINT = "intake_ready_for_blueprint"
    BLUEPRINT_DRAFT_GENERATED = "blueprint_draft_generated"
    BLUEPRINT_NEEDS_INTERNAL_REVIEW = "blueprint_needs_internal_review"
    BLUEPRINT_READY_FOR_CUSTOMER_REVIEW = "blueprint_ready_for_customer_review"
    BLUEPRINT_CHANGES_REQUESTED = "blueprint_changes_requested"
    BLUEPRINT_APPROVED = "blueprint_approved"
    DEVELOPER_PLAN_PENDING = "developer_plan_pending"
    DEVELOPER_PLAN_DRAFTED = "developer_plan_drafted"
    DEVELOPER_PLAN_NEEDS_REVIEW = "developer_plan_needs_review"
    DEVELOPER_PLAN_APPROVED = "developer_plan_approved"
    BUILD_QUEUED = "build_queued"
    BUILD_ACTIVE = "build_active"
    BUILD_BLOCKED = "build_blocked"
    INTERNAL_REVIEW = "internal_review"
    QA_VALIDATION = "qa_validation"
    QA_FAILED_NEEDS_FIXES = "qa_failed_needs_fixes"
    DEMO_READY = "demo_ready"
    CUSTOMER_DEMO_REVIEW = "customer_demo_review"
    CHANGES_REQUESTED = "changes_requested"
    HANDOFF_READY = "handoff_ready"
    ACCEPTED_DELIVERED = "accepted_delivered"
    SUPPORT_RETAINER = "support_retainer"
    ARCHIVED = "archived"


class IntakeStatus(StrEnum):
    """
    Enumerates guided intake statuses.
    """

    DRAFT = "draft"
    SUBMITTED = "submitted"
    NEEDS_FOLLOW_UP = "needs_follow_up"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class BlueprintStatus(StrEnum):
    """
    Enumerates customer-facing blueprint statuses.
    """

    GENERATED = "generated"
    VALIDATION_FAILED = "validation_failed"
    NEEDS_INTERNAL_REVIEW = "needs_internal_review"
    READY_FOR_CUSTOMER_REVIEW = "ready_for_customer_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class DeveloperPlanStatus(StrEnum):
    """
    Enumerates private developer-plan statuses.
    """

    MISSING = "missing"
    GENERATED = "generated"
    VALIDATION_FAILED = "validation_failed"
    NEEDS_TECHNICAL_REVIEW = "needs_technical_review"
    APPROVED = "approved"
    BLOCKED = "blocked"
    SUPERSEDED = "superseded"


class SliceStatus(StrEnum):
    """
    Enumerates implementation slice statuses.
    """

    PLANNED = "planned"
    READY = "ready"
    ACTIVE = "active"
    BLOCKED = "blocked"
    NEEDS_INTERNAL_REVIEW = "needs_internal_review"
    NEEDS_QA = "needs_qa"
    QA_FAILED = "qa_failed"
    COMPLETE = "complete"
    DEFERRED = "deferred"


class QaStatus(StrEnum):
    """
    Enumerates QA validation item statuses.
    """

    OPEN = "open"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_CUSTOMER_CLARIFICATION = "needs_customer_clarification"


class ApprovalStatus(StrEnum):
    """
    Enumerates customer/internal approval decisions.
    """

    REQUESTED = "requested"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SupportStatus(StrEnum):
    """
    Enumerates support/enhancement request statuses.
    """

    OPEN = "open"
    IN_REVIEW = "in_review"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class ExportStatus(StrEnum):
    """
    Enumerates generated export statuses.
    """

    GENERATED = "generated"
    DOWNLOADED = "downloaded"
    BLOCKED = "blocked"
    EXPIRED = "expired"
