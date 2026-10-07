# -*- coding: utf-8 -*-
# tests/test_healthRoutes.py
"""
Tests GridForge health routes.

The tests verify the health endpoint returns non-sensitive app and repository
status using injected fake repositories.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from typing import Any, cast

# 2) Third-party imports (alphabetized)
from flask.testing import FlaskClient

# 3) Application-specific imports (alphabetized)


def test_healthRouteReturnsOk(client: FlaskClient) -> None:
    """
    Verifies the health endpoint returns public status data.

    Args:
        client: Flask test client fixture.

    Returns:
        None.
    """
    response = client.get("/health")
    payload = cast(dict[str, Any], response.get_json())

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["app"] == "gridforge-command-cloud"
    assert payload["environment"] == "test"
    assert payload["repositories"] == {"datastore": "fake"}
