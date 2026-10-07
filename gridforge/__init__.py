# -*- coding: utf-8 -*-
# gridforge/__init__.py
"""
Exposes the GridForge Command Cloud Flask app factory.

This package contains the application factory, configuration loader, route
blueprints, and repository boundaries used by the cloud-first GridForge web
application.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.appFactory import createApp

__all__ = ["createApp"]
