# -*- coding: utf-8 -*-
# tests/test_roleGuards.py
"""
Tests GridForge local demo role guard helpers.

The tests verify demo session normalization, role checks, organization/project
scope checks, invalid-role filtering, and logout cleanup without external auth.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Any

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import UserRole
from gridforge.web.auth.roleGuards import (
    getCurrentUserContext,
    hasAnyRole,
    isLoggedIn,
    loginDemoUser,
    logoutDemoUser,
    parseRoles,
    canAccessOrganization,
    canAccessProject,
)


def test_demoUserSessionRoundTripAndLogout() -> None:
    """
    Verifies demo user login context can be read and cleared.

    Returns:
        None.
    """
    session_data: dict[str, Any] = {}

    loginDemoUser(
        session_data,
        user_id="demo_customer_contact",
        email="customer@gridforge.example",
        roles=(UserRole.CUSTOMER_CONTACT,),
        organization_ids=("org_1",),
        project_ids=("project_1",),
    )
    context = getCurrentUserContext(session_data)

    assert isLoggedIn(session_data) is True
    assert context.user_id == "demo_customer_contact"
    assert context.email == "customer@gridforge.example"
    assert context.roles == (UserRole.CUSTOMER_CONTACT,)
    assert context.organization_ids == ("org_1",)
    assert context.project_ids == ("project_1",)
    assert hasAnyRole((UserRole.CUSTOMER_CONTACT,), session_data) is True
    assert hasAnyRole((UserRole.PLATFORM_ADMIN,), session_data) is False

    logoutDemoUser(session_data)

    assert isLoggedIn(session_data) is False
    assert getCurrentUserContext(session_data).roles == ()


def test_scopeChecksAllowInternalRolesAndScopedCustomers() -> None:
    """
    Verifies internal users get broad access and customers are scoped.

    Returns:
        None.
    """
    internal_session: dict[str, Any] = {}
    customer_session: dict[str, Any] = {}
    loginDemoUser(
        internal_session,
        user_id="demo_platform_admin",
        email="admin@gridforge.example",
        roles=(UserRole.PLATFORM_ADMIN,),
    )
    loginDemoUser(
        customer_session,
        user_id="demo_customer_contact",
        email="customer@gridforge.example",
        roles=(UserRole.CUSTOMER_CONTACT,),
        organization_ids=("org_allowed",),
        project_ids=("project_allowed",),
    )

    assert canAccessOrganization("any_org", internal_session) is True
    assert canAccessProject("any_project", internal_session) is True
    assert canAccessOrganization("org_allowed", customer_session) is True
    assert canAccessProject("project_allowed", customer_session) is True
    assert canAccessOrganization("org_blocked", customer_session) is False
    assert canAccessProject("project_blocked", customer_session) is False


def test_parseRolesFiltersInvalidRolesAndDeduplicates() -> None:
    """
    Verifies invalid or duplicate role values do not grant access.

    Returns:
        None.
    """
    roles = parseRoles(
        (
            "platform_admin",
            "unknown_role",
            "platform_admin",
            "customer_contact",
        )
    )

    assert roles == (UserRole.PLATFORM_ADMIN, UserRole.CUSTOMER_CONTACT)
