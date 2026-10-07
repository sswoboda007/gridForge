# -*- coding: utf-8 -*-
# tests/conftest.py
"""
Configures shared pytest fixtures for GridForge Command Cloud.

The fixtures create the Flask app with fake repositories and testing config so
route tests run without production services.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)
from flask import Flask
from flask.testing import FlaskClient
import pytest

# 3) Application-specific imports (alphabetized)
from gridforge import createApp
from tests.fakes import createFakeRepositories


@pytest.fixture()
def app() -> Flask:
    """
    Creates a test Flask application with fake repositories.

    Returns:
        A configured Flask test app.
    """
    return createApp(
        config_overrides={
            "APP_ENV": "test",
            "SECRET_KEY": "test-secret-key",
            "TESTING": True,
        },
        repositories=createFakeRepositories(),
    )


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """
    Creates a Flask test client.

    Args:
        app: The pytest Flask app fixture.

    Returns:
        A FlaskClient bound to the test app.
    """
    return app.test_client()
