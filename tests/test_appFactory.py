# -*- coding: utf-8 -*-
# tests/test_appFactory.py
"""
Tests GridForge Flask app factory behavior.

The tests verify the app factory wires configuration, repositories, routes, and
template context without production services.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)
from flask import Flask

# 3) Application-specific imports (alphabetized)


def test_appFactoryAppliesTestConfig(app: Flask) -> None:
    """
    Verifies the factory applies explicit test configuration.

    Args:
        app: Test Flask app fixture.

    Returns:
        None.
    """
    assert app.config["APP_ENV"] == "test"
    assert app.config["SECRET_KEY"] == "test-secret-key"
    assert app.config["TESTING"] is True


def test_appFactoryRegistersExpectedRoutes(app: Flask) -> None:
    """
    Verifies the Phase 0 route surface is registered.

    Args:
        app: Test Flask app fixture.

    Returns:
        None.
    """
    route_paths = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/" in route_paths
    assert "/start" in route_paths
    assert "/admin/projects" in route_paths
    assert "/admin/projects/<project_id>" in route_paths
    assert "/api/intake" in route_paths
    assert "/auth/demo-login" in route_paths
    assert "/auth/login" in route_paths
    assert "/auth/logout" in route_paths
    assert "/admin/blueprints/<blueprint_id>" in route_paths
    assert "/admin/blueprints/<blueprint_id>/review" in route_paths
    assert "/admin/projects/<project_id>/generate-blueprint" in route_paths
    assert "/admin/review-queue" in route_paths
    assert "/customer/blueprints/<blueprint_id>" in route_paths
    assert "/customer/blueprints/<blueprint_id>/approve" in route_paths
    assert "/customer/blueprints/<blueprint_id>/changes-requested" in route_paths
    assert "/admin/blueprints/<blueprint_id>/generate-developer-plan" in route_paths
    assert "/developer/plans/<developer_plan_id>" in route_paths
    assert "/developer/plans/<developer_plan_id>/review" in route_paths
    assert "/developer/projects/<project_id>/slices" in route_paths
    assert "/developer/slices/<slice_id>/status" in route_paths
    assert "/developer/slices/<slice_id>/blockers" in route_paths
    assert "/qa/projects/<project_id>" in route_paths
    assert "/qa/projects/<project_id>/items" in route_paths
    assert "/qa/items/<qa_item_id>/status" in route_paths
    assert "/admin" in route_paths
    assert "/admin/audit-log" in route_paths
    assert "/admin/role-matrix" in route_paths
    assert "/exports/project/<project_id>/customer-summary.csv" in route_paths
    assert "/exports/project/<project_id>/blueprint-summary.csv" in route_paths
    assert "/exports/project/<project_id>/developer-plan-internal.csv" in route_paths
    assert "/exports/project/<project_id>/qa-handoff.csv" in route_paths
    assert "/exports/audit.csv" in route_paths
    assert "/support/projects/<project_id>" in route_paths
    assert "/support/projects/<project_id>/requests" in route_paths
    assert "/support/requests/<request_id>/status" in route_paths
    assert "/health" in route_paths


def test_appFactoryStoresRepositoryBundle(app: Flask) -> None:
    """
    Verifies injected repositories are stored on Flask extensions.

    Args:
        app: Test Flask app fixture.

    Returns:
        None.
    """
    assert "gridforge_repositories" in app.extensions
