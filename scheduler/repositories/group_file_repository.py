"""Reads and writes file metadata attached to groups."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from scheduler.domain.group_file import GroupFile
from scheduler.infrastructure.database import Database


class GroupFileRepository:
    """Access to groupFiles through a Database."""

    def __init__(self, db: Database):
        self._db = db

    def saveFileMetadata(self, groupId: int, fileName: str, filePath: str, uploadedAt: datetime) -> int:
        """Store file metadata and return its generated id."""
        return self._db.sql(
            "INSERT INTO groupFiles (groupId, fileName, filePath, uploadedAt) "
            "VALUES (?, ?, ?, ?) RETURNING fileId",
            [groupId, fileName, filePath, uploadedAt],
        ).fetchone()[0]

    def findById(self, fileId: int) -> Optional[GroupFile]:
        """Return metadata for the id, or None if it does not exist."""
        row = self._db.sql(
            "SELECT fileId, groupId, fileName, filePath, uploadedAt FROM groupFiles WHERE fileId = ?",
            [fileId],
        ).fetchone()
        return GroupFile(*row) if row else None

    def findByGroupId(self, groupId: int) -> list[GroupFile]:
        """Return metadata for every file attached to the group."""
        rows = self._db.sql(
            "SELECT fileId, groupId, fileName, filePath, uploadedAt "
            "FROM groupFiles WHERE groupId = ? ORDER BY fileId",
            [groupId],
        ).fetchall()
        return [GroupFile(*row) for row in rows]

    def deleteById(self, fileId: int) -> None:
        """Delete metadata with the given id."""
        self._db.sql("DELETE FROM groupFiles WHERE fileId = ?", [fileId])
