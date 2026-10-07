# -*- coding: utf-8 -*-
# tests/test_repositoryBundle.py
"""
Tests GridForge repository bundle defaults.

The tests verify the Phase 0 default repository bundle exposes non-sensitive
health status without production services.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.configLoader import loadConfig
from gridforge.repositoryBundle import createDefaultRepositories
from gridforge.repositories.healthRepo import LocalHealthRepository


def test_defaultRepositoryBundleUsesLocalHealthRepository() -> None:
    """
    Verifies the default bundle uses local Phase 0 health storage.

    Returns:
        None.
    """
    repositories = createDefaultRepositories(loadConfig(environ={"APP_ENV": "test"}))

    assert repositories.health_repo.getHealthSummary() == {"datastore": "memory"}


def test_localHealthRepositoryReportsMemoryBackend() -> None:
    """
    Verifies the local health repository reports memory storage.

    Returns:
        None.
    """
    repository = LocalHealthRepository()

    assert repository.getHealthSummary() == {"datastore": "memory"}
