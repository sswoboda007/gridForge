# -*- coding: utf-8 -*-
# gridforge/web/auth/demoAuth.py
"""
Defines local demo-user identities for GridForge.

Demo users allow Phase 3 role guards to be exercised before durable account,
identity-provider, and session-management work is implemented.

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
from gridforge.domain.enums import UserRole


@dataclass(frozen=True)
class DemoUser:
    """
    Represents a selectable local demo user.

    Args:
        id: Demo user identifier.
        label: Human-readable display label.
        email: Demo user email.
        roles: Roles granted to the demo user.
        organization_ids: Organization ids the user can access.
        project_ids: Project ids the user can access.
    """

    id: str
    label: str
    email: str
    roles: tuple[UserRole, ...]
    organization_ids: tuple[str, ...] = ()
    project_ids: tuple[str, ...] = ()


DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser(
        id="demo_platform_admin",
        label="GridForge Owner / Platform Admin",
        email="admin@gridforge.example",
        roles=(UserRole.PLATFORM_ADMIN,),
    ),
    DemoUser(
        id="demo_workflow_analyst",
        label="Workflow Analyst / Blueprint Reviewer",
        email="analyst@gridforge.example",
        roles=(UserRole.WORKFLOW_ANALYST,),
    ),
    DemoUser(
        id="demo_developer",
        label="Developer / Builder",
        email="developer@gridforge.example",
        roles=(UserRole.DEVELOPER,),
    ),
    DemoUser(
        id="demo_qa_reviewer",
        label="QA / Validation Reviewer",
        email="qa@gridforge.example",
        roles=(UserRole.QA_REVIEWER,),
    ),
    DemoUser(
        id="demo_support_manager",
        label="Support / Account Manager",
        email="support@gridforge.example",
        roles=(UserRole.SUPPORT_MANAGER,),
    ),
    DemoUser(
        id="demo_read_only_executive",
        label="Read-Only Executive / Advisor",
        email="executive@gridforge.example",
        roles=(UserRole.READ_ONLY_EXECUTIVE,),
    ),
    DemoUser(
        id="demo_customer_contact",
        label="Customer Contact",
        email="customer@gridforge.example",
        roles=(UserRole.CUSTOMER_CONTACT,),
        organization_ids=("org_demo_customer",),
        project_ids=("project_demo_customer",),
    ),
    DemoUser(
        id="demo_client_stakeholder",
        label="Client Stakeholder / Approver",
        email="stakeholder@gridforge.example",
        roles=(UserRole.CLIENT_STAKEHOLDER,),
        organization_ids=("org_demo_customer",),
        project_ids=("project_demo_customer",),
    ),
)


def getDemoUser(user_id: str) -> DemoUser | None:
    """
    Finds a demo user by id.

    Args:
        user_id: Demo user identifier.

    Returns:
        Matching DemoUser, or None.
    """
    for user in DEMO_USERS:
        if user.id == user_id:
            return user
    return None
