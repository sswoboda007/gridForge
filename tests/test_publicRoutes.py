# -*- coding: utf-8 -*-
# tests/test_publicRoutes.py
"""
Tests GridForge public routes.

The tests verify the public landing and start pages render the expected Phase 0
content without exposing private implementation details.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)
from flask.testing import FlaskClient

# 3) Application-specific imports (alphabetized)


def test_landingPageRendersCommandCloudPositioning(client: FlaskClient) -> None:
    """
    Verifies the landing page explains GridForge's workflow-system positioning.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Turn messy workflows into private, role-based webapp systems" in body
    assert "Start Blueprint" in body


def test_startPageShowsSensitiveDataWarning(client: FlaskClient) -> None:
    """
    Verifies the start page includes the sensitive-data warning.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.get("/start")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Sensitive data warning" in body
    assert "Do not enter passwords" in body
