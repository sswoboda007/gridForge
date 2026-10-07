# -*- coding: utf-8 -*-
# tests/fakes.py
"""
Provides deterministic fakes for GridForge tests.

The fakes keep the default test suite fully offline and independent of durable
storage, AI providers, notification services, and cloud infrastructure.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Mapping

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.repositoryBundle import AppRepositories, createMemoryRepositories


class FakeHealthRepository:
    """
    Supplies deterministic repository health data for tests.
    """

    def getHealthSummary(self) -> Mapping[str, str]:
        """
        Returns deterministic fake datastore status.

        Returns:
            A mapping with fake repository status values.
        """
        return {"datastore": "fake"}


def createFakeRepositories() -> AppRepositories:
    """
    Creates a fake repository bundle for tests.

    Returns:
        AppRepositories backed by deterministic in-memory repositories.
    """
    return createMemoryRepositories(health_repo=FakeHealthRepository())
