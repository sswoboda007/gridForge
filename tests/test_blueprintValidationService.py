# -*- coding: utf-8 -*-
# tests/test_blueprintValidationService.py
"""
Tests GridForge customer blueprint validation.

The tests verify required schema validation, first-JSON parsing, malformed output
rejection, authority matrix checks, and forbidden-claim detection.

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
from gridforge.services.blueprintValidationService import BlueprintValidationService


def test_blueprintValidationAcceptsCompleteSchemaWithWrappedJson() -> None:
    """
    Verifies complete customer blueprint JSON validates successfully.

    Returns:
        None.
    """
    raw_text = f"prefix {json.dumps(createValidBlueprintContent())} suffix"

    result = BlueprintValidationService().validateBlueprintText(raw_text)

    assert result.ok is True
    assert result.errors == ()
    assert result.content["appSummary"] == "A private workflow command center."


def test_blueprintValidationRejectsMalformedOutput() -> None:
    """
    Verifies malformed AI output is rejected.

    Returns:
        None.
    """
    result = BlueprintValidationService().validateBlueprintText("not json")

    assert result.ok is False
    assert result.errors == ("Response did not contain a valid JSON object.",)


def test_blueprintValidationRejectsMissingAndEmptyRequiredValues() -> None:
    """
    Verifies missing keys and empty required lists are rejected.

    Returns:
        None.
    """
    content = createValidBlueprintContent()
    content.pop("appSummary")
    content["targetUsers"] = []

    result = BlueprintValidationService().validateBlueprintContent(content)

    assert result.ok is False
    assert "Missing required key: appSummary" in result.errors
    assert "Required list must be non-empty: targetUsers" in result.errors


def test_blueprintValidationRejectsForbiddenClaimsAndBadAuthorityMatrix() -> None:
    """
    Verifies forbidden claims and invalid authority rows are rejected.

    Returns:
        None.
    """
    content = createValidBlueprintContent()
    content["appSummary"] = "This is HIPAA compliant with a fixed price."
    content["authorityMatrix"] = [{"role": "Customer"}]

    result = BlueprintValidationService().validateBlueprintContent(content)

    assert result.ok is False
    assert "Forbidden claim detected: hipaa compliant" in result.errors
    assert "Forbidden claim detected: fixed price" in result.errors
    assert "authorityMatrix[0] must include permissions." in result.errors


def createValidBlueprintContent() -> dict[str, object]:
    """
    Creates valid customer blueprint content.

    Returns:
        Valid blueprint content mapping.
    """
    return {
        "appNameIdeas": ["Workflow Command Center"],
        "appSummary": "A private workflow command center.",
        "problemBeingSolved": "Manual work is scattered across tools.",
        "targetUsers": [{"role": "Customer", "goal": "Review progress."}],
        "authorityMatrix": [{"role": "Customer", "permissions": ["view_blueprint"]}],
        "mainWorkflows": [{"name": "Review", "steps": ["open", "approve"]}],
        "recommendedPages": [{"name": "Status", "purpose": "Review status."}],
        "dataObjects": [{"name": "Project", "purpose": "Track work."}],
        "reportsAndExports": ["Blueprint summary"],
        "integrations": ["AI provider boundary"],
        "mvpScope": ["Guided intake"],
        "phaseTwoScope": ["Developer plan"],
        "laterScope": ["Advanced exports"],
        "risksAndUnknowns": ["Human review required"],
        "followUpQuestions": ["Confirm scope?"],
        "suggestedBuildMilestones": ["Approve blueprint"],
        "fitSummary": {"fit": "strong", "reason": "Role-based workflow."},
    }
