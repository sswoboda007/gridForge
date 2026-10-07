# -*- coding: utf-8 -*-
# gridforge/services/developerPlanValidationService.py
"""
Validates internal developer-plan content for GridForge.

The validation service enforces the developer-plan schema, route-spec shape,
authorization policy shape, export-spec shape, and non-empty required sections.
Developer-plan validation errors remain internal-only.

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

REQUIRED_DEVELOPER_PLAN_KEYS = (
    "implementationOverview",
    "mvpCutLine",
    "entitySpecs",
    "routeSpecs",
    "authorizationPolicies",
    "stateMachines",
    "validationRules",
    "queryAndIndexSpecs",
    "dashboardMetricSpecs",
    "csvExportSpecs",
    "testPlan",
    "dataLifecycleRules",
    "auditEvents",
    "securityPrivacyNotes",
    "failureModes",
    "operationalNotes",
    "implementationSlices",
    "blockingQuestions",
    "deferredQuestions",
    "developerMilestones",
)
REQUIRED_LIST_KEYS = (
    "entitySpecs",
    "routeSpecs",
    "authorizationPolicies",
    "stateMachines",
    "validationRules",
    "queryAndIndexSpecs",
    "dashboardMetricSpecs",
    "csvExportSpecs",
    "dataLifecycleRules",
    "auditEvents",
    "securityPrivacyNotes",
    "failureModes",
    "operationalNotes",
    "implementationSlices",
    "blockingQuestions",
    "deferredQuestions",
    "developerMilestones",
)
ROUTE_SPEC_REQUIRED_KEYS = ("method", "route", "auth", "errorCases", "tests")
AUTH_POLICY_REQUIRED_KEYS = ("role", "scope", "rules")
CSV_EXPORT_REQUIRED_KEYS = ("columns", "roleAccess", "auditEvent")


@dataclass(frozen=True)
class DeveloperPlanValidationResult:
    """
    Stores developer-plan validation results.

    Args:
        ok: Whether validation passed.
        content: Parsed content when valid.
        errors: Internal validation errors when invalid.
    """

    ok: bool
    content: JsonObject
    errors: tuple[str, ...]


class DeveloperPlanValidationService:
    """
    Validates generated developer-plan content.
    """

    def validateDeveloperPlanText(self, raw_text: str) -> DeveloperPlanValidationResult:
        """
        Parses and validates raw developer-plan text.

        Args:
            raw_text: Raw generated plan text.

        Returns:
            DeveloperPlanValidationResult with parsed content or errors.
        """
        parsed_content = parseFirstJsonObject(raw_text)
        if parsed_content is None:
            return DeveloperPlanValidationResult(
                ok=False,
                content={},
                errors=("Response did not contain a valid JSON object.",),
            )
        return self.validateDeveloperPlanContent(parsed_content)

    def validateDeveloperPlanContent(
        self,
        content: Mapping[str, Any],
    ) -> DeveloperPlanValidationResult:
        """
        Validates parsed developer-plan content.

        Args:
            content: Parsed developer-plan mapping.

        Returns:
            DeveloperPlanValidationResult with normalized content or errors.
        """
        errors: list[str] = []
        normalized_content = dict(content)
        for key in REQUIRED_DEVELOPER_PLAN_KEYS:
            if key not in normalized_content:
                errors.append(f"Missing required key: {key}")
        if not str(normalized_content.get("implementationOverview", "")).strip():
            errors.append("implementationOverview must be a non-empty string.")
        for key in REQUIRED_LIST_KEYS:
            value = normalized_content.get(key)
            if not isinstance(value, list) or len(value) == 0:
                errors.append(f"Required list must be non-empty: {key}")
        if not isinstance(normalized_content.get("mvpCutLine"), dict):
            errors.append("mvpCutLine must be an object.")
        if not isinstance(normalized_content.get("testPlan"), dict):
            errors.append("testPlan must be an object.")
        errors.extend(validateRouteSpecs(normalized_content.get("routeSpecs")))
        errors.extend(
            validateAuthorizationPolicies(normalized_content.get("authorizationPolicies"))
        )
        errors.extend(validateCsvExportSpecs(normalized_content.get("csvExportSpecs")))
        return DeveloperPlanValidationResult(
            ok=not errors,
            content=normalized_content if not errors else {},
            errors=tuple(errors),
        )


def parseFirstJsonObject(raw_text: str) -> JsonObject | None:
    """
    Parses the first JSON object found in raw text.

    Args:
        raw_text: Raw generated text.

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


def validateRouteSpecs(value: object) -> tuple[str, ...]:
    """
    Validates route specs contain method, route, auth, errors, and tests.

    Args:
        value: Route spec list value.

    Returns:
        Validation errors.
    """
    if not isinstance(value, list) or not value:
        return ("routeSpecs must be a non-empty list.",)
    errors: list[str] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            errors.append(f"routeSpecs[{index}] must be an object.")
            continue
        for key in ROUTE_SPEC_REQUIRED_KEYS:
            if not row.get(key):
                errors.append(f"routeSpecs[{index}] must include {key}.")
    return tuple(errors)


def validateAuthorizationPolicies(value: object) -> tuple[str, ...]:
    """
    Validates authorization policies contain role, scope, and rules.

    Args:
        value: Authorization policy list value.

    Returns:
        Validation errors.
    """
    if not isinstance(value, list) or not value:
        return ("authorizationPolicies must be a non-empty list.",)
    errors: list[str] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            errors.append(f"authorizationPolicies[{index}] must be an object.")
            continue
        for key in AUTH_POLICY_REQUIRED_KEYS:
            if not row.get(key):
                errors.append(f"authorizationPolicies[{index}] must include {key}.")
    return tuple(errors)


def validateCsvExportSpecs(value: object) -> tuple[str, ...]:
    """
    Validates CSV export specs contain columns, role access, and audit event.

    Args:
        value: CSV export spec list value.

    Returns:
        Validation errors.
    """
    if not isinstance(value, list) or not value:
        return ("csvExportSpecs must be a non-empty list.",)
    errors: list[str] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            errors.append(f"csvExportSpecs[{index}] must be an object.")
            continue
        for key in CSV_EXPORT_REQUIRED_KEYS:
            if not row.get(key):
                errors.append(f"csvExportSpecs[{index}] must include {key}.")
    return tuple(errors)
