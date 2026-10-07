# -*- coding: utf-8 -*-
# gridforge/repositories/healthRepo.py
"""
Provides health repository contracts and local implementation for GridForge.

The health repository exposes only non-sensitive runtime status so health routes
can be tested without production persistence.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Mapping, Protocol

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)


class HealthRepository(Protocol):
    """
    Describes repository behavior needed by the health endpoint.
    """

    def getHealthSummary(self) -> Mapping[str, str]:
        """
        Returns a small, non-sensitive repository status summary.

        Returns:
            A mapping of repository component names to public status values.
        """
        ...


class LocalHealthRepository:
    """
    Provides a local placeholder health summary before durable storage is wired in.
    """

    def getHealthSummary(self) -> Mapping[str, str]:
        """
        Returns a non-sensitive local datastore status.

        Returns:
            A mapping indicating that memory-backed storage is active.
        """
        return {"datastore": "memory"}
