# -*- coding: utf-8 -*-
# gridforge/appFactory.py
"""
Creates the GridForge Command Cloud Flask application.

The factory loads configuration, creates or accepts injected repositories, and
registers route blueprints so tests can exercise the app without production
services.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Any, Mapping

# 2) Third-party imports (alphabetized)
from flask import Flask

# 3) Application-specific imports (alphabetized)
from gridforge.configLoader import loadConfig
from gridforge.repositoryBundle import AppRepositories, createDefaultRepositories
from gridforge.web.auth.roleGuards import getTemplateAuthContext
from gridforge.web.blueprints.adminRoutes import createAdminBlueprint
from gridforge.web.blueprints.authRoutes import createAuthBlueprint
from gridforge.web.blueprints.healthRoutes import createHealthBlueprint
from gridforge.web.blueprints.intakeRoutes import createIntakeBlueprint
from gridforge.web.blueprints.publicRoutes import createPublicBlueprint


def createApp(
    config_overrides: Mapping[str, Any] | None = None,
    repositories: AppRepositories | None = None,
) -> Flask:
    """
    Builds and configures the Flask application instance.

    Args:
        config_overrides: Optional Flask-style config overrides for tests.
        repositories: Optional repository bundle for dependency injection.

    Returns:
        A configured Flask application.
    """
    app_config = loadConfig(overrides=config_overrides)
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.update(app_config.toFlaskConfig())

    app_repositories = repositories or createDefaultRepositories(app_config)
    app.extensions["gridforge_repositories"] = app_repositories
    app.context_processor(getTemplateContext)
    app.context_processor(getTemplateAuthContext)
    app.register_blueprint(createPublicBlueprint(app_repositories))
    app.register_blueprint(createAuthBlueprint())
    app.register_blueprint(createIntakeBlueprint(app_repositories))
    app.register_blueprint(createAdminBlueprint(app_repositories))
    app.register_blueprint(createHealthBlueprint(app_repositories))
    return app


def getTemplateContext() -> dict[str, object]:
    """
    Provides shared template context values.

    Returns:
        A mapping of common template values.
    """
    return {
        "appName": "GridForge Command Cloud",
        "companyName": "GridForge Systems",
    }
