# -*- coding: utf-8 -*-
# tests/test_missingDetailService.py
"""
Tests GridForge missing-detail and fit-risk evaluation.

The tests verify guided intake coverage categories and deterministic risk flags
used before blueprint generation.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.services.missingDetailService import MissingDetailService


def test_missingDetailServiceFindsCoveredAndMissingCategories() -> None:
    """
    Verifies missing detail categories are tracked deterministically.

    Returns:
        None.
    """
    result = MissingDetailService().evaluateIntakeCoverage(
        {
            "organizationName": "GridForge Systems",
            "workflowDescription": "Customer discovery pipeline",
            "currentTools": ("spreadsheets", "email"),
            "desiredOutcome": "Structured blueprint",
            "successDefinition": "Clear process",
            "usersPermissions": "Admin and customers",
        }
    )

    assert "business_context" in result.covered_categories
    assert "users_and_permissions" in result.covered_categories
    assert "workflow_lifecycle" in result.missing_categories
    assert result.coverage_count == 2
    assert result.coverage_total == 7
    assert result.completion_percent == 29


def test_missingDetailServiceFlagsScopeRisks() -> None:
    """
    Verifies deterministic fit-risk flags are extracted from intake answers.

    Returns:
        None.
    """
    result = MissingDetailService().evaluateIntakeCoverage(
        {
            "organizationName": "Example Co",
            "workflowDescription": "We want native mobile, offline-first sync, and HIPAA.",
            "budgetRange": "Not sure yet",
            "additionalContext": "Contains sensitive business customer data.",
        }
    )

    assert result.risk_flags == (
        "unclear_budget",
        "offline_first_requested",
        "native_mobile_requested",
        "compliance_review_needed",
        "sensitive_business_info",
    )
