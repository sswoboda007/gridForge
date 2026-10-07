# -*- coding: utf-8 -*-
# gridforge/repositoryBundle.py
"""
Defines application repository boundaries for GridForge Command Cloud.

The default implementation is intentionally lightweight for Phase 0, while the
repository bundle establishes the dependency injection pattern used by services
and route blueprints.

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
from gridforge.configLoader import AppConfig
from gridforge.repositories.healthRepo import HealthRepository, LocalHealthRepository


@dataclass(frozen=True)
class AppRepositories:
    """
    Bundles repositories injected into route blueprints and services.

    Args:
        health_repo: Repository used by the health check route.
    """

    health_repo: HealthRepository


def createDefaultRepositories(app_config: AppConfig | None = None) -> AppRepositories:
    """
    Creates the default repository bundle for the application factory.

    Args:
        app_config: Optional application configuration used by later persistence choices.

    Returns:
        AppRepositories backed by Phase 0 local repositories.
    """
    _ = app_config
    return AppRepositories(health_repo=LocalHealthRepository())
