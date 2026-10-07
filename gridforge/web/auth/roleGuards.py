# -*- coding: utf-8 -*-
# gridforge/web/auth/roleGuards.py
"""
Provides local demo session and role guard helpers for GridForge.

The helpers enforce server-side authorization checks for Phase 3 and are
intentionally small so a durable authentication provider can replace the identity
source later without changing route-level permission intent.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from functools import wraps
from typing import Any, ParamSpec, TypeVar

# 2) Third-party imports (alphabetized)
from flask import abort, redirect, request, session, url_for
from werkzeug.wrappers.response import Response

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import UserRole

SESSION_ORGANIZATION_IDS_KEY = "organization_ids"
SESSION_PROJECT_IDS_KEY = "project_ids"
SESSION_USER_EMAIL_KEY = "user_email"
SESSION_USER_ID_KEY = "user_id"
SESSION_USER_ROLES_KEY = "roles"

INTERNAL_ROLES = (
    UserRole.PLATFORM_ADMIN,
    UserRole.WORKFLOW_ANALYST,
    UserRole.DEVELOPER,
    UserRole.QA_REVIEWER,
    UserRole.SUPPORT_MANAGER,
    UserRole.READ_ONLY_EXECUTIVE,
)
ADMIN_ROLES = (UserRole.PLATFORM_ADMIN,)
PROJECT_REVIEW_ROLES = (
    UserRole.PLATFORM_ADMIN,
    UserRole.WORKFLOW_ANALYST,
    UserRole.DEVELOPER,
    UserRole.QA_REVIEWER,
    UserRole.SUPPORT_MANAGER,
    UserRole.READ_ONLY_EXECUTIVE,
)
CUSTOMER_ROLES = (UserRole.CUSTOMER_CONTACT, UserRole.CLIENT_STAKEHOLDER)

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True)
class DemoUserContext:
    """
    Stores the current local/demo user context.

    Args:
        user_id: Current user identifier.
        email: Current user email.
        roles: Current user roles.
        organization_ids: Organization ids the user can access.
        project_ids: Project ids the user can access.
    """

    user_id: str | None
    email: str | None
    roles: tuple[UserRole, ...]
    organization_ids: tuple[str, ...]
    project_ids: tuple[str, ...]


def loginDemoUser(
    session_data: MutableMapping[str, Any],
    *,
    user_id: str,
    email: str,
    roles: Sequence[UserRole],
    organization_ids: Sequence[str] = (),
    project_ids: Sequence[str] = (),
) -> None:
    """
    Stores a local demo identity in the signed session.

    Args:
        session_data: Mutable Flask session mapping.
        user_id: Demo user identifier.
        email: Demo user email.
        roles: Demo user roles.
        organization_ids: Accessible organization ids.
        project_ids: Accessible project ids.

    Returns:
        None.
    """
    session_data[SESSION_USER_ID_KEY] = user_id
    session_data[SESSION_USER_EMAIL_KEY] = email
    session_data[SESSION_USER_ROLES_KEY] = [role.value for role in roles]
    session_data[SESSION_ORGANIZATION_IDS_KEY] = list(organization_ids)
    session_data[SESSION_PROJECT_IDS_KEY] = list(project_ids)


def logoutDemoUser(session_data: MutableMapping[str, Any]) -> None:
    """
    Removes the local demo identity from the signed session.

    Args:
        session_data: Mutable Flask session mapping.

    Returns:
        None.
    """
    for key in (
        SESSION_ORGANIZATION_IDS_KEY,
        SESSION_PROJECT_IDS_KEY,
        SESSION_USER_EMAIL_KEY,
        SESSION_USER_ID_KEY,
        SESSION_USER_ROLES_KEY,
    ):
        session_data.pop(key, None)


def getCurrentUserContext(session_data: Mapping[str, Any] | None = None) -> DemoUserContext:
    """
    Reads the current local/demo user context.

    Args:
        session_data: Optional session mapping; defaults to Flask session.

    Returns:
        DemoUserContext from the session.
    """
    source = session if session_data is None else session_data
    return DemoUserContext(
        user_id=optionalSessionString(source.get(SESSION_USER_ID_KEY)),
        email=optionalSessionString(source.get(SESSION_USER_EMAIL_KEY)),
        roles=parseRoles(source.get(SESSION_USER_ROLES_KEY)),
        organization_ids=parseStringSequence(source.get(SESSION_ORGANIZATION_IDS_KEY)),
        project_ids=parseStringSequence(source.get(SESSION_PROJECT_IDS_KEY)),
    )


def getCurrentUserId(session_data: Mapping[str, Any] | None = None) -> str | None:
    """
    Reads the current user id from the session.

    Args:
        session_data: Optional session mapping; defaults to Flask session.

    Returns:
        Current user id, or None.
    """
    return getCurrentUserContext(session_data).user_id


def getCurrentUserRoles(session_data: Mapping[str, Any] | None = None) -> tuple[UserRole, ...]:
    """
    Reads the current user roles from the session.

    Args:
        session_data: Optional session mapping; defaults to Flask session.

    Returns:
        Current normalized user roles.
    """
    return getCurrentUserContext(session_data).roles


def isLoggedIn(session_data: Mapping[str, Any] | None = None) -> bool:
    """
    Checks whether a local/demo user is logged in.

    Args:
        session_data: Optional session mapping; defaults to Flask session.

    Returns:
        True when a user id is present.
    """
    return getCurrentUserContext(session_data).user_id is not None


def hasAnyRole(
    required_roles: Sequence[UserRole],
    session_data: Mapping[str, Any] | None = None,
) -> bool:
    """
    Checks whether the current user has any required role.

    Args:
        required_roles: Allowed roles.
        session_data: Optional session mapping; defaults to Flask session.

    Returns:
        True when any role matches.
    """
    current_roles = set(getCurrentUserRoles(session_data))
    return bool(current_roles.intersection(required_roles))


def canAccessOrganization(
    organization_id: str,
    session_data: Mapping[str, Any] | None = None,
) -> bool:
    """
    Checks organization-scope access for the current user.

    Args:
        organization_id: Organization id to check.
        session_data: Optional session mapping; defaults to Flask session.

    Returns:
        True when internal role or explicit organization scope allows access.
    """
    context = getCurrentUserContext(session_data)
    if set(context.roles).intersection(INTERNAL_ROLES):
        return True
    return organization_id in context.organization_ids


def canAccessProject(project_id: str, session_data: Mapping[str, Any] | None = None) -> bool:
    """
    Checks project-scope access for the current user.

    Args:
        project_id: Project id to check.
        session_data: Optional session mapping; defaults to Flask session.

    Returns:
        True when internal role or explicit project scope allows access.
    """
    context = getCurrentUserContext(session_data)
    if set(context.roles).intersection(INTERNAL_ROLES):
        return True
    return project_id in context.project_ids


def roleRequired(*required_roles: UserRole) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Creates a route decorator that requires one of the specified roles.

    Args:
        required_roles: Allowed roles for the route.

    Returns:
        Decorator enforcing the role requirement.
    """

    def decorator(route_handler: Callable[P, R]) -> Callable[P, R]:
        @wraps(route_handler)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if not isLoggedIn():
                abort(403)
            if not hasAnyRole(required_roles):
                abort(403)
            return route_handler(*args, **kwargs)

        return wrapped

    return decorator


def internalRequired(route_handler: Callable[P, R]) -> Callable[P, R]:
    """
    Decorates a route so only internal GridForge roles can access it.

    Args:
        route_handler: Flask route handler.

    Returns:
        Wrapped route handler.
    """
    return roleRequired(*INTERNAL_ROLES)(route_handler)


def adminRequired(route_handler: Callable[P, R]) -> Callable[P, R]:
    """
    Decorates a route so only Platform Admin users can access it.

    Args:
        route_handler: Flask route handler.

    Returns:
        Wrapped route handler.
    """
    return roleRequired(*ADMIN_ROLES)(route_handler)


def requireProjectScope(project_id: str) -> None:
    """
    Aborts unless the current user can access a project.

    Args:
        project_id: Project id to check.

    Returns:
        None.
    """
    if not canAccessProject(project_id):
        abort(403)


def requireOrganizationScope(organization_id: str) -> None:
    """
    Aborts unless the current user can access an organization.

    Args:
        organization_id: Organization id to check.

    Returns:
        None.
    """
    if not canAccessOrganization(organization_id):
        abort(403)


def getTemplateAuthContext() -> dict[str, object]:
    """
    Provides authentication context to templates.

    Returns:
        Template context values for demo identity display.
    """
    context = getCurrentUserContext()
    return {
        "currentUserEmail": context.email,
        "currentUserRoles": tuple(role.value for role in context.roles),
        "isLoggedIn": context.user_id is not None,
    }


def loginRequiredRedirectTarget() -> Response:
    """
    Redirects users toward demo login.

    Returns:
        Redirect response to demo login page.
    """
    return redirect(url_for("auth.loginPage", next=request.path))


def parseRoles(raw_roles: object) -> tuple[UserRole, ...]:
    """
    Parses session role values into UserRole values.

    Args:
        raw_roles: Raw session role value.

    Returns:
        Tuple of valid roles.
    """
    roles: list[UserRole] = []
    for raw_role in parseStringSequence(raw_roles):
        try:
            roles.append(UserRole(raw_role))
        except ValueError:
            continue
    return tuple(dict.fromkeys(roles))


def parseStringSequence(raw_value: object) -> tuple[str, ...]:
    """
    Parses a session value into a tuple of non-empty strings.

    Args:
        raw_value: Raw session value.

    Returns:
        Tuple of strings.
    """
    values: tuple[str, ...]
    if isinstance(raw_value, str):
        values = (raw_value,)
    elif isinstance(raw_value, Sequence):
        values = tuple(str(item) for item in raw_value)
    else:
        values = ()
    return tuple(value.strip() for value in values if value.strip())


def optionalSessionString(raw_value: object) -> str | None:
    """
    Normalizes an optional session string.

    Args:
        raw_value: Raw session value.

    Returns:
        Stripped string, or None.
    """
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    return value or None
