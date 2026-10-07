# -*- coding: utf-8 -*-
# tests/test_developerPlanValidationService.py
"""
Tests GridForge developer-plan validation.

The tests verify required developer-plan sections, malformed output rejection,
route-spec shape, authorization policy shape, and CSV export spec shape.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
import json

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.services.developerPlanValidationService import DeveloperPlanValidationService


def test_developerPlanValidationAcceptsCompleteSchemaWithWrappedJson() -> None:
    """
    Verifies complete developer-plan JSON validates successfully.

    Returns:
        None.
    """
    raw_text = f"prefix {json.dumps(createValidDeveloperPlanContent())} suffix"

    result = DeveloperPlanValidationService().validateDeveloperPlanText(raw_text)

    assert result.ok is True
    assert result.errors == ()
    assert result.content["implementationOverview"] == "Build the approved workflow MVP."


def test_developerPlanValidationRejectsMalformedOutput() -> None:
    """
    Verifies malformed generated output is rejected.

    Returns:
        None.
    """
    result = DeveloperPlanValidationService().validateDeveloperPlanText("not json")

    assert result.ok is False
    assert result.errors == ("Response did not contain a valid JSON object.",)


def test_developerPlanValidationRejectsMissingAndEmptyRequiredValues() -> None:
    """
    Verifies missing keys and empty required lists are rejected.

    Returns:
        None.
    """
    content = createValidDeveloperPlanContent()
    content.pop("implementationOverview")
    content["implementationSlices"] = []

    result = DeveloperPlanValidationService().validateDeveloperPlanContent(content)

    assert result.ok is False
    assert "Missing required key: implementationOverview" in result.errors
    assert "implementationOverview must be a non-empty string." in result.errors
    assert "Required list must be non-empty: implementationSlices" in result.errors


def test_developerPlanValidationRejectsInvalidRouteAuthAndExportShapes() -> None:
    """
    Verifies required technical sub-shapes are enforced.

    Returns:
        None.
    """
    content = createValidDeveloperPlanContent()
    content["routeSpecs"] = [{"method": "GET"}]
    content["authorizationPolicies"] = [{"role": "Developer"}]
    content["csvExportSpecs"] = [{"columns": ["id"]}]

    result = DeveloperPlanValidationService().validateDeveloperPlanContent(content)

    assert result.ok is False
    assert "routeSpecs[0] must include route." in result.errors
    assert "routeSpecs[0] must include auth." in result.errors
    assert "routeSpecs[0] must include errorCases." in result.errors
    assert "routeSpecs[0] must include tests." in result.errors
    assert "authorizationPolicies[0] must include scope." in result.errors
    assert "authorizationPolicies[0] must include rules." in result.errors
    assert "csvExportSpecs[0] must include roleAccess." in result.errors
    assert "csvExportSpecs[0] must include auditEvent." in result.errors


def createValidDeveloperPlanContent() -> dict[str, object]:
    """
    Creates valid developer-plan content.

    Returns:
        Valid developer-plan content mapping.
    """
    return {
        "implementationOverview": "Build the approved workflow MVP.",
        "mvpCutLine": {"included": ["intake"], "excluded": ["payments"]},
        "entitySpecs": [{"name": "Project", "fields": ["id", "status"]}],
        "routeSpecs": [
            {
                "method": "GET",
                "route": "/developer/plans/<id>",
                "auth": "developer",
                "errorCases": ["403"],
                "tests": ["developer 200"],
            }
        ],
        "authorizationPolicies": [
            {"role": "Developer", "scope": "internal", "rules": ["view plan"]}
        ],
        "stateMachines": [{"name": "Plan review", "states": ["review", "approved"]}],
        "validationRules": ["Approved blueprint required"],
        "queryAndIndexSpecs": [{"name": "plansByProject", "fields": ["project_id"]}],
        "dashboardMetricSpecs": [{"name": "plans_needing_review"}],
        "csvExportSpecs": [
            {
                "columns": ["id", "status"],
                "roleAccess": ["developer"],
                "auditEvent": "developer_plan_exported",
            }
        ],
        "testPlan": {"unit": ["validation"], "route": ["detail"]},
        "dataLifecycleRules": ["Supersede old plans"],
        "auditEvents": ["developer_plan_generated"],
        "securityPrivacyNotes": ["Internal only"],
        "failureModes": [{"mode": "invalid", "response": "422"}],
        "operationalNotes": ["Review before slicing"],
        "implementationSlices": [
            {
                "name": "Developer workflow",
                "goal": "Plan implementation",
                "acceptanceCriteria": ["developer sees plan"],
            }
        ],
        "blockingQuestions": ["Confirm repo"],
        "deferredQuestions": ["Confirm exports"],
        "developerMilestones": ["Approve plan"],
    }
