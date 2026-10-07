# -*- coding: utf-8 -*-
# gridforge/web/blueprints/authRoutes.py
"""
Defines local demo authentication routes for GridForge.

The routes allow local/demo role switching so Phase 3 authorization policies can
be exercised before durable account and identity-provider work is implemented.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import cast
from urllib.parse import urlparse

# 2) Third-party imports (alphabetized)
from flask import Blueprint, Response, abort, redirect, render_template, request, session, url_for

# 3) Application-specific imports (alphabetized)
from gridforge.web.auth.demoAuth import DEMO_USERS, getDemoUser
from gridforge.web.auth.roleGuards import loginDemoUser, logoutDemoUser


def createAuthBlueprint() -> Blueprint:
    """
    Creates demo authentication routes.

    Returns:
        A Flask Blueprint containing auth routes.
    """
    auth_routes = Blueprint("auth", __name__)

    @auth_routes.get("/auth/login")
    def loginPage() -> str:
        """
        Renders the demo login page.

        Returns:
            Rendered demo login page HTML.
        """
        next_path = normalizeNextPath(request.args.get("next"))
        return cast(
            str, render_template("auth/login.html", demo_users=DEMO_USERS, next_path=next_path)
        )

    @auth_routes.post("/auth/demo-login")
    def demoLogin() -> Response:
        """
        Logs in as a selected local demo user.

        Returns:
            Redirect response to the requested safe local path.
        """
        user_id = request.form.get("userId", "").strip()
        demo_user = getDemoUser(user_id)
        if demo_user is None:
            abort(400)
            raise RuntimeError("unreachable")
        loginDemoUser(
            session,
            user_id=demo_user.id,
            email=demo_user.email,
            roles=demo_user.roles,
            organization_ids=demo_user.organization_ids,
            project_ids=demo_user.project_ids,
        )
        return redirect(normalizeNextPath(request.form.get("next")))

    @auth_routes.post("/auth/logout")
    def logout() -> Response:
        """
        Logs out the current local demo user.

        Returns:
            Redirect response to the public landing page.
        """
        logoutDemoUser(session)
        return redirect(url_for("public.landingPage"))

    return auth_routes


def normalizeNextPath(raw_next_path: str | None) -> str:
    """
    Normalizes redirect targets to safe local paths.

    Args:
        raw_next_path: Raw next path from query string or form data.

    Returns:
        Safe local redirect path.
    """
    fallback_path = cast(str, url_for("public.landingPage"))
    if not raw_next_path:
        return fallback_path
    parsed_next = urlparse(raw_next_path)
    if parsed_next.scheme or parsed_next.netloc or not raw_next_path.startswith("/"):
        return fallback_path
    return raw_next_path
