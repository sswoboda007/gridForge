# -*- coding: utf-8 -*-
# gridforge/services/missingDetailService.py
"""
Evaluates guided intake coverage and fit-risk flags.

The service identifies which blueprint detail categories are missing and flags
scope risks such as unclear budget, offline-first requests, or native mobile
requests before blueprint generation begins.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass
from typing import Mapping

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)

CATEGORY_FIELDS: Mapping[str, tuple[str, ...]] = {
    "business_context": (
        "organizationName",
        "workflowDescription",
        "currentTools",
        "desiredOutcome",
        "successDefinition",
    ),
    "users_and_permissions": ("usersPermissions",),
    "workflow_lifecycle": ("workflowLifecycle", "statuses"),
    "data_forms_and_files": ("formsDataFiles",),
    "dashboards_and_reports": ("dashboardsReports",),
    "integrations_and_notifications": ("integrationsNotifications",),
    "additional_context": ("additionalContext",),
}

RISK_FLAG_UNCLEAR_BUDGET = "unclear_budget"
RISK_FLAG_OFFLINE_FIRST_REQUESTED = "offline_first_requested"
RISK_FLAG_NATIVE_MOBILE_REQUESTED = "native_mobile_requested"
RISK_FLAG_COMPLIANCE_REVIEW_NEEDED = "compliance_review_needed"
RISK_FLAG_SENSITIVE_BUSINESS_INFO = "sensitive_business_info"


@dataclass(frozen=True)
class MissingDetailResult:
    """
    Stores intake coverage and deterministic fit-risk results.

    Args:
        covered_categories: Categories with enough information.
        missing_categories: Categories needing follow-up.
        coverage_count: Number of covered categories.
        coverage_total: Total number of tracked categories.
        completion_percent: Rounded completion percentage.
        risk_flags: Deterministic fit-risk flags.
    """

    covered_categories: tuple[str, ...]
    missing_categories: tuple[str, ...]
    coverage_count: int
    coverage_total: int
    completion_percent: int
    risk_flags: tuple[str, ...]


class MissingDetailService:
    """
    Evaluates guided intake coverage and deterministic risk flags.
    """

    def evaluateIntakeCoverage(self, answers: Mapping[str, object]) -> MissingDetailResult:
        """
        Calculates covered/missing detail categories and fit-risk flags.

        Args:
            answers: Normalized intake answer mapping.

        Returns:
            MissingDetailResult for the intake.
        """
        covered_categories: list[str] = []
        missing_categories: list[str] = []
        for category, field_names in CATEGORY_FIELDS.items():
            if any(hasMeaningfulValue(answers.get(field_name)) for field_name in field_names):
                covered_categories.append(category)
            else:
                missing_categories.append(category)

        coverage_total = len(CATEGORY_FIELDS)
        coverage_count = len(covered_categories)
        completion_percent = round((coverage_count / coverage_total) * 100)
        return MissingDetailResult(
            covered_categories=tuple(covered_categories),
            missing_categories=tuple(missing_categories),
            coverage_count=coverage_count,
            coverage_total=coverage_total,
            completion_percent=completion_percent,
            risk_flags=self.extractRiskFlags(answers),
        )

    def extractRiskFlags(self, answers: Mapping[str, object]) -> tuple[str, ...]:
        """
        Extracts deterministic fit-risk flags from intake answers.

        Args:
            answers: Normalized intake answer mapping.

        Returns:
            Ordered tuple of risk flag identifiers.
        """
        combined_text = " ".join(stringifyValue(value).lower() for value in answers.values())
        risk_flags: list[str] = []
        budget_answer = stringifyValue(answers.get("budgetRange") or answers.get("budgetAnswer"))
        if not budget_answer or containsAny(
            budget_answer.lower(), ("not sure", "unclear", "unknown")
        ):
            risk_flags.append(RISK_FLAG_UNCLEAR_BUDGET)
        if containsAny(combined_text, ("offline first", "offline-first", "offline sync")):
            risk_flags.append(RISK_FLAG_OFFLINE_FIRST_REQUESTED)
        if containsAny(combined_text, ("native mobile", "ios app", "android app")):
            risk_flags.append(RISK_FLAG_NATIVE_MOBILE_REQUESTED)
        if containsAny(combined_text, ("hipaa", "ferpa", "soc2", "legal compliance")):
            risk_flags.append(RISK_FLAG_COMPLIANCE_REVIEW_NEEDED)
        if containsAny(combined_text, ("sensitive business", "private workflow", "customer data")):
            risk_flags.append(RISK_FLAG_SENSITIVE_BUSINESS_INFO)
        return tuple(dict.fromkeys(risk_flags))


def hasMeaningfulValue(value: object) -> bool:
    """
    Checks whether an answer has meaningful content.

    Args:
        value: Raw answer value.

    Returns:
        True when the value contains non-empty content.
    """
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return any(hasMeaningfulValue(item) for item in value)
    return value is not None


def stringifyValue(value: object) -> str:
    """
    Converts an intake answer value into searchable text.

    Args:
        value: Raw answer value.

    Returns:
        Text representation for coverage/risk evaluation.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return " ".join(stringifyValue(item) for item in value)
    return str(value).strip()


def containsAny(value: str, needles: tuple[str, ...]) -> bool:
    """
    Checks whether value contains any target phrase.

    Args:
        value: Text to inspect.
        needles: Phrases to find.

    Returns:
        True when at least one phrase appears in value.
    """
    return any(needle in value for needle in needles)
