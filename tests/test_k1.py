"""K1: the groupFiles table and GroupRepository.isMember."""

from __future__ import annotations

from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_repository import GroupRepository
from scheduler.services.group_service import GroupService


def test_groupFilesTableStartsEmpty():
    db = DuckDBConnection(":memory:")
    assert db.sql("SELECT * FROM groupFiles").fetchall() == []


def test_isMember():
    groupRepo = GroupRepository(DuckDBConnection(":memory:"))
    group = GroupService(groupRepo).createGroup(1, "G")
    assert groupRepo.isMember(group.groupId, 1) is True
    assert groupRepo.isMember(group.groupId, 999) is False


def test_deleteGroupWithNoFiles():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    group = GroupService(groupRepo).createGroup(1, "G")
    groupRepo.delete(group.groupId)
    assert groupRepo.findById(group.groupId) is None


def test_deleteGroupRemovesFileRows():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    group = GroupService(groupRepo).createGroup(1, "G")
    db.sql(
        "INSERT INTO groupFiles (groupId, fileName, filePath, uploadedAt) VALUES (?, ?, ?, now())",
        [group.groupId, "a.txt", "uploads/a.txt"],
    )
    groupRepo.delete(group.groupId)
    assert db.sql("SELECT * FROM groupFiles").fetchall() == []
