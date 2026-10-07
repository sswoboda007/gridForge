# -*- coding: utf-8 -*-
# gridforge/services/auditService.py
"""
Provides audit-event creation helpers for GridForge workflows.

The service creates safe, structured audit records for sensitive state changes
without exposing raw prompts, internal notes, secrets, or customer-private data.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
import time
import uuid

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.domain.enums import UserRole
from gridforge.domain.records import AuditEvent, JsonObject
from gridforge.repositories.memoryRepo import RecordRepository


def currentTimeMs() -> int:
    """
    Returns the current Unix timestamp in milliseconds.

    Returns:
        Current timestamp in milliseconds.
    """
    return int(time.time() * 1000)


def createRecordId(prefix: str) -> str:
    """
    Creates a prefixed random record identifier.

    Args:
        prefix: Record id prefix without trailing underscore.

    Returns:
        Identifier in the format `<prefix>_<hex>`.
    """
    return f"{prefix}_{uuid.uuid4().hex}"


class AuditService:
    """
    Creates and stores safe audit events.
    """

    def __init__(self, audit_event_repo: RecordRepository[AuditEvent]) -> None:
        """
        Initializes the service.

        Args:
            audit_event_repo: Repository used to persist audit events.

        Returns:
            None.
        """
        self._audit_event_repo = audit_event_repo

    def recordEvent(
        self,
        *,
        event_type: str,
        record_type: str,
        record_id: str,
        safe_summary: str,
        organization_id: str | None = None,
        project_id: str | None = None,
        actor_user_id: str | None = None,
        actor_role: UserRole | None = None,
        customer_visible: bool = False,
        before_after_json: JsonObject | None = None,
        current_time_ms: int | None = None,
    ) -> AuditEvent:
        """
        Creates and stores one audit event.

        Args:
            event_type: Machine-readable event type.
            record_type: Related record type.
            record_id: Related record id.
            safe_summary: Non-sensitive event summary.
            organization_id: Optional organization id.
            project_id: Optional project id.
            actor_user_id: Optional actor user id.
            actor_role: Optional actor role.
            customer_visible: Whether this event can be shown to customers.
            before_after_json: Optional safe change summary.
            current_time_ms: Optional deterministic timestamp for tests.

        Returns:
            Stored AuditEvent.
        """
        event = AuditEvent(
            id=createRecordId("audit"),
            organization_id=organization_id,
            project_id=project_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            record_type=record_type,
            record_id=record_id,
            safe_summary=safe_summary,
            customer_visible=customer_visible,
            before_after_json=before_after_json or {},
            created_at_ms=current_time_ms if current_time_ms is not None else currentTimeMs(),
        )
        return self._audit_event_repo.createRecord(event)
