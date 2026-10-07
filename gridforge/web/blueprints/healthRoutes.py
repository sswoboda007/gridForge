# -*- coding: utf-8 -*-
# gridforge/web/blueprints/healthRoutes.py
"""
Defines the GridForge health check route.

The health route returns non-sensitive app and repository status suitable for
local validation and cloud health checks.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Any

# 2) Third-party imports (alphabetized)
from flask import Blueprint, Response, current_app, jsonify

# 3) Application-specific imports (alphabetized)
from gridforge.repositoryBundle import AppRepositories


def createHealthBlueprint(repositories: AppRepositories) -> Blueprint:
    """
    Creates the health route blueprint.

    Args:
        repositories: Repository bundle used for health status.

    Returns:
        A Flask Blueprint containing health routes.
    """
    health_routes = Blueprint("health", __name__)

    @health_routes.get("/health")
    def healthCheck() -> Response:
        """
        Returns non-sensitive application health data.

        Returns:
            JSON Flask response.
        """
        payload: dict[str, Any] = {
            "app": "gridforge-command-cloud",
            "environment": str(current_app.config.get("APP_ENV", "local")),
            "repositories": dict(repositories.health_repo.getHealthSummary()),
            "status": "ok",
        }
        return jsonify(payload)

    return health_routes
