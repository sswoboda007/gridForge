# -*- coding: utf-8 -*-
# gridforge/web/blueprints/publicRoutes.py
"""
Defines public marketing and start routes for GridForge Command Cloud.

The public routes introduce the cloud-first workflow operating system and direct
visitors toward the guided intake flow.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import cast

# 2) Third-party imports (alphabetized)
from flask import Blueprint, render_template

# 3) Application-specific imports (alphabetized)
from gridforge.repositoryBundle import AppRepositories


def createPublicBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates public marketing and intake entry routes.

    Args:
        repositories: Repository bundle reserved for later public data needs.

    Returns:
        A Flask Blueprint containing public routes.
    """
    _ = repositories
    public_routes = Blueprint("public", __name__)

    @public_routes.get("/")
    def landingPage() -> str:
        """
        Renders the public GridForge landing page.

        Returns:
            Rendered landing page HTML.
        """
        return cast(str, render_template("public/landing.html"))

    @public_routes.get("/start")
    def startPage() -> str:
        """
        Renders the Phase 2 blueprint intake form.

        Returns:
            Rendered start page HTML.
        """
        return cast(str, render_template("intake/form.html"))

    return public_routes
