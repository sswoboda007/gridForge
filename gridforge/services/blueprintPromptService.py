# -*- coding: utf-8 -*-
# gridforge/services/blueprintPromptService.py
"""
Builds customer-blueprint prompt payloads for GridForge.

The prompt service produces deterministic, customer-safe prompt text from intake
and workflow project records without exposing internal developer plans or raw AI
metadata to customer routes.

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
from gridforge.domain.records import CustomerWorkflowProject, IntakeResponse

CUSTOMER_BLUEPRINT_PROMPT_VERSION = "customer-blueprint-v1"


@dataclass(frozen=True)
class BlueprintPrompt:
    """
    Represents the prompt sent to a customer-blueprint AI client.

    Args:
        prompt_version: Stable prompt version identifier.
        prompt_text: Prompt text for the AI provider or fake client.
    """

    prompt_version: str
    prompt_text: str


class BlueprintPromptService:
    """
    Builds prompts for customer-facing workflow blueprints.
    """

    def buildCustomerBlueprintPrompt(
        self,
        project: CustomerWorkflowProject,
        intake: IntakeResponse,
    ) -> BlueprintPrompt:
        """
        Builds a deterministic prompt for customer blueprint generation.

        Args:
            project: Workflow project context.
            intake: Intake response context.

        Returns:
            BlueprintPrompt for the AI client.
        """
        prompt_payload = {
            "instruction": "Create a customer-facing workflow webapp blueprint.",
            "guardrails": (
                "Do not promise compliance certification, legal advice, medical advice, "
                "guaranteed offline-first behavior, fixed pricing, fixed timelines, or "
                "production code delivery."
            ),
            "requiredOutput": "Return one JSON object using the customer blueprint schema.",
            "project": {
                "projectName": project.project_name,
                "workflowType": project.workflow_type,
                "painfulWorkflowDescription": project.painful_workflow_description,
                "currentTools": project.current_tools,
                "desiredOutcome": project.desired_outcome,
                "successDefinition": project.success_definition,
                "riskFlags": project.risk_flags,
            },
            "intake": {
                "usersPermissions": intake.users_permissions_answer,
                "workflowLifecycle": intake.workflow_lifecycle_answer,
                "statuses": intake.statuses_answer,
                "formsDataFiles": intake.forms_data_files_answer,
                "dashboardsReports": intake.dashboards_reports_answer,
                "integrationsNotifications": intake.integrations_notifications_answer,
                "additionalContext": intake.additional_context_answer,
                "followUpQuestions": intake.follow_up_questions,
            },
        }
        return BlueprintPrompt(
            prompt_version=CUSTOMER_BLUEPRINT_PROMPT_VERSION,
            prompt_text=json.dumps(prompt_payload, sort_keys=True),
        )
