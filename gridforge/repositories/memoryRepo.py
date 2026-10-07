# -*- coding: utf-8 -*-
# gridforge/repositories/memoryRepo.py
"""
Provides reusable in-memory repository primitives for GridForge.

The in-memory repository implements create, read, update, list, and scoped list
operations so services can be developed and tested before durable storage is
introduced.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from collections.abc import Sequence
from typing import Generic, Protocol, TypeVar

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)


class StoredRecord(Protocol):
    """
    Describes the minimum shape required for in-memory persistence.
    """

    @property
    def id(self) -> str:
        """
        Returns the record identifier.

        Returns:
            Stable record id.
        """
        ...


TRecord = TypeVar("TRecord", bound=StoredRecord)


class RecordRepository(Protocol[TRecord]):
    """
    Describes repository behavior shared by Phase 1 domain records.
    """

    def createRecord(self, record: TRecord) -> TRecord:
        """
        Stores a new record.

        Args:
            record: Record to store.

        Returns:
            Stored record.
        """
        ...

    def getRecord(self, record_id: str) -> TRecord | None:
        """
        Looks up a record by id.

        Args:
            record_id: Record identifier.

        Returns:
            Matching record, or None when missing.
        """
        ...

    def updateRecord(self, record: TRecord) -> TRecord | None:
        """
        Replaces an existing record.

        Args:
            record: Replacement record.

        Returns:
            Updated record, or None when missing.
        """
        ...

    def listRecords(self) -> tuple[TRecord, ...]:
        """
        Lists all stored records in insertion order.

        Returns:
            Stored records.
        """
        ...

    def listByOrganization(self, organization_id: str) -> tuple[TRecord, ...]:
        """
        Lists records matching an organization id when present.

        Args:
            organization_id: Organization identifier.

        Returns:
            Matching records.
        """
        ...

    def listByProject(self, project_id: str) -> tuple[TRecord, ...]:
        """
        Lists records matching a project id when present.

        Args:
            project_id: Project identifier.

        Returns:
            Matching records.
        """
        ...


class InMemoryRecordRepository(Generic[TRecord]):
    """
    Stores records in process memory for tests and early MVP slices.
    """

    def __init__(self, records: Sequence[TRecord] = ()) -> None:
        """
        Initializes the repository with optional seed records.

        Args:
            records: Initial records to store.

        Returns:
            None.
        """
        self._records: dict[str, TRecord] = {}
        for record in records:
            self.createRecord(record)

    def createRecord(self, record: TRecord) -> TRecord:
        """
        Stores a new record and rejects duplicate identifiers.

        Args:
            record: Record to store.

        Returns:
            Stored record.

        Raises:
            ValueError: If a record with the same id already exists.
        """
        if record.id in self._records:
            raise ValueError(f"Record already exists: {record.id}")
        self._records[record.id] = record
        return record

    def getRecord(self, record_id: str) -> TRecord | None:
        """
        Looks up a record by id.

        Args:
            record_id: Record identifier.

        Returns:
            Matching record, or None when missing.
        """
        return self._records.get(record_id)

    def updateRecord(self, record: TRecord) -> TRecord | None:
        """
        Replaces an existing record.

        Args:
            record: Replacement record.

        Returns:
            Updated record, or None when missing.
        """
        if record.id not in self._records:
            return None
        self._records[record.id] = record
        return record

    def listRecords(self) -> tuple[TRecord, ...]:
        """
        Lists all stored records in insertion order.

        Returns:
            Stored records.
        """
        return tuple(self._records.values())

    def listByOrganization(self, organization_id: str) -> tuple[TRecord, ...]:
        """
        Lists records matching an organization id when present.

        Args:
            organization_id: Organization identifier.

        Returns:
            Matching records.
        """
        return tuple(
            record
            for record in self._records.values()
            if getattr(record, "organization_id", None) == organization_id
        )

    def listByProject(self, project_id: str) -> tuple[TRecord, ...]:
        """
        Lists records matching a project id when present.

        Args:
            project_id: Project identifier.

        Returns:
            Matching records.
        """
        return tuple(
            record
            for record in self._records.values()
            if getattr(record, "project_id", None) == project_id
        )
