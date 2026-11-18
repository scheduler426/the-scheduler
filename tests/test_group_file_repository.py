"""GroupFileRepository metadata persistence tests."""

from __future__ import annotations

from datetime import datetime

from scheduler.domain.group_file import GroupFile
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_file_repository import GroupFileRepository


def test_groupFileRepositoryLifecycle():
    db = DuckDBConnection(":memory:")
    repository = GroupFileRepository(db)
    uploadedAt = datetime(2026, 11, 5)

    fileId = repository.saveFileMetadata(1, "notes.txt", "/tmp/x", uploadedAt)
    assert fileId > 0

    groupFile = repository.findById(fileId)
    assert isinstance(groupFile, GroupFile)
    assert (groupFile.fileId, groupFile.groupId, groupFile.fileName, groupFile.filePath, groupFile.uploadedAt) == (
        fileId,
        1,
        "notes.txt",
        "/tmp/x",
        uploadedAt,
    )

    groupFiles = repository.findByGroupId(1)
    assert len(groupFiles) == 1
    assert (
        groupFiles[0].fileId,
        groupFiles[0].groupId,
        groupFiles[0].fileName,
        groupFiles[0].filePath,
        groupFiles[0].uploadedAt,
    ) == (fileId, 1, "notes.txt", "/tmp/x", uploadedAt)
    assert repository.findById(999) is None

    repository.deleteById(fileId)
    assert repository.findById(fileId) is None
    db.close()
