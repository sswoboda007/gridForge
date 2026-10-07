# -*- coding: utf-8 -*-
# gridforge/services/blueprintValidationService.py
"""
Validates customer-facing blueprint AI output for GridForge.

The validation service parses AI JSON, checks required customer-facing schema
sections, rejects forbidden claims, and keeps validation errors internal-only.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass
import json
from typing import Any, Mapping

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.records import JsonObject

REQUIRED_BLUEPRINT_KEYS = (
    "appNameIdeas",
    "appSummary",
    "problemBeingSolved",
    "targetUsers",
    "authorityMatrix",
    "mainWorkflows",
    "recommendedPages",
    "dataObjects",
    "reportsAndExports",
    "integrations",
    "mvpScope",
    "phaseTwoScope",
    "laterScope",
    "risksAndUnknowns",
    "followUpQuestions",
    "suggestedBuildMilestones",
    "fitSummary",
)
LIST_BLUEPRINT_KEYS = (
    "appNameIdeas",
    "targetUsers",
    "authorityMatrix",
    "mainWorkflows",
    "recommendedPages",
    "dataObjects",
    "reportsAndExports",
    "integrations",
    "mvpScope",
    "phaseTwoScope",
    "laterScope",
    "risksAndUnknowns",
    "followUpQuestions",
    "suggestedBuildMilestones",
)
FORBIDDEN_CLAIM_PHRASES = (
    "hipaa compliant",
    "hipaa certified",
    "ferpa compliant",
    "ferpa certified",
    "soc2 compliant",
    "soc 2 compliant",
    "soc2 certified",
    "legal advice",
    "medical advice",
    "financial advice",
    "guaranteed offline",
    "offline-first guarantee",
    "fixed price",
    "guaranteed price",
    "guaranteed timeline",
    "production code generated",
)


@dataclass(frozen=True)
class BlueprintValidationResult:
    """
    Stores the result of customer blueprint output validation.

    Args:
        ok: Whether validation passed.
        content: Parsed and normalized content when valid.
        errors: Internal validation errors when invalid.
    """

    ok: bool
    content: JsonObject
    errors: tuple[str, ...]


class BlueprintValidationService:
    """
    Validates generated customer blueprint content.
    """

    def validateBlueprintText(self, raw_text: str) -> BlueprintValidationResult:
        """
        Parses and validates a raw AI response.

        Args:
            raw_text: Raw AI response text.

        Returns:
            BlueprintValidationResult with parsed content or errors.
        """
        parsed_content = parseFirstJsonObject(raw_text)
        if parsed_content is None:
            return BlueprintValidationResult(
                ok=False,
                content={},
                errors=("Response did not contain a valid JSON object.",),
            )
        return self.validateBlueprintContent(parsed_content)

    def validateBlueprintContent(self, content: Mapping[str, Any]) -> BlueprintValidationResult:
        """
        Validates a parsed customer blueprint mapping.

        Args:
            content: Parsed blueprint content.

        Returns:
            BlueprintValidationResult with normalized content or errors.
        """
        errors: list[str] = []
        normalized_content = dict(content)
        for key in REQUIRED_BLUEPRINT_KEYS:
            if key not in normalized_content:
                errors.append(f"Missing required key: {key}")
        for key in LIST_BLUEPRINT_KEYS:
            value = normalized_content.get(key)
            if not isinstance(value, list) or len(value) == 0:
                errors.append(f"Required list must be non-empty: {key}")
        if not isinstance(normalized_content.get("fitSummary"), dict):
            errors.append("fitSummary must be an object.")
        errors.extend(validateAuthorityMatrix(normalized_content.get("authorityMatrix")))
        forbidden_claims = findForbiddenClaims(normalized_content)
        errors.extend(f"Forbidden claim detected: {claim}" for claim in forbidden_claims)
        return BlueprintValidationResult(
            ok=not errors,
            content=normalized_content if not errors else {},
            errors=tuple(errors),
        )


def parseFirstJsonObject(raw_text: str) -> JsonObject | None:
    """
    Parses the first JSON object found in raw text.

    Args:
        raw_text: Raw AI response text.

    Returns:
        Parsed JSON object, or None when parsing fails.
    """
    start_index = raw_text.find("{")
    end_index = raw_text.rfind("}")
    if start_index < 0 or end_index < start_index:
        return None
    try:
        parsed_value = json.loads(raw_text[start_index : end_index + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed_value, dict):
        return None
    return parsed_value


def validateAuthorityMatrix(value: object) -> tuple[str, ...]:
    """
    Validates the required authority matrix shape.

    Args:
        value: Authority matrix value.

    Returns:
        Validation error messages.
    """
    if not isinstance(value, list) or not value:
        return ("authorityMatrix must be a non-empty list.",)
    errors: list[str] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            errors.append(f"authorityMatrix[{index}] must be an object.")
            continue
        if not row.get("role"):
            errors.append(f"authorityMatrix[{index}] must include role.")
        permissions = row.get("permissions")
        if not isinstance(permissions, list) or not permissions:
            errors.append(f"authorityMatrix[{index}] must include permissions.")
    return tuple(errors)


def findForbiddenClaims(value: object) -> tuple[str, ...]:
    """
    Finds forbidden customer-facing claims recursively.

    Args:
        value: Parsed blueprint value.

    Returns:
        Ordered forbidden claim phrases that appeared.
    """
    rendered_value = json.dumps(value, sort_keys=True).lower()
    return tuple(claim for claim in FORBIDDEN_CLAIM_PHRASES if claim in rendered_value)
