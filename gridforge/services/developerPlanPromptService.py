# -*- coding: utf-8 -*-
# gridforge/services/developerPlanPromptService.py
"""
Builds internal developer-plan prompt payloads for GridForge.

The prompt service translates approved customer blueprint context into a private
technical-planning payload. Developer plans are internal-only and must not be
rendered to customer routes.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass
import json

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.records import CustomerBlueprint, CustomerWorkflowProject

DEVELOPER_PLAN_PROMPT_VERSION = "developer-plan-v3"


@dataclass(frozen=True)
class DeveloperPlanPrompt:
    """
    Represents the internal prompt used for developer-plan generation.

    Args:
        prompt_version: Stable prompt version identifier.
        prompt_text: Internal prompt text for a plan generator.
    """

    prompt_version: str
    prompt_text: str


class DeveloperPlanPromptService:
    """
    Builds internal developer-plan prompt payloads.
    """

    def buildDeveloperPlanPrompt(
        self,
        project: CustomerWorkflowProject,
        blueprint: CustomerBlueprint,
    ) -> DeveloperPlanPrompt:
        """
        Builds deterministic developer-plan prompt context.

        Args:
            project: Workflow project context.
            blueprint: Approved customer blueprint context.

        Returns:
            DeveloperPlanPrompt for deterministic generation.
        """
        prompt_payload = {
            "instruction": "Create an internal developer-only implementation plan.",
            "guardrails": (
                "Keep this content private to GridForge internal roles. Include route, "
                "permission, validation, export, QA, and implementation-slice details."
            ),
            "requiredOutput": "Return one JSON object using the developer plan schema.",
            "project": {
                "projectId": project.id,
                "projectName": project.project_name,
                "workflowType": project.workflow_type,
                "shortSummary": project.short_summary,
                "approvedBlueprintId": project.approved_blueprint_id,
            },
            "blueprint": {
                "title": blueprint.title,
                "summary": blueprint.app_summary,
                "problem": blueprint.problem_being_solved,
                "targetUsers": blueprint.target_users_json,
                "authorityMatrix": blueprint.authority_matrix_json,
                "mainWorkflows": blueprint.main_workflows_json,
                "recommendedPages": blueprint.recommended_pages_json,
                "dataObjects": blueprint.data_objects_json,
                "mvpScope": blueprint.mvp_scope_json,
                "risksAndUnknowns": blueprint.risks_and_unknowns_json,
                "suggestedMilestones": blueprint.suggested_build_milestones_json,
            },
        }
        return DeveloperPlanPrompt(
            prompt_version=DEVELOPER_PLAN_PROMPT_VERSION,
            prompt_text=json.dumps(prompt_payload, sort_keys=True),
        )
