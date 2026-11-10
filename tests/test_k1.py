"""K1: the groupFiles table and GroupRepository.isMember."""

from __future__ import annotations

import pytest

from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_file_repository import GroupFileRepository
from scheduler.repositories.group_repository import GroupRepository
from scheduler.services.group_file_service import GroupFileService
from scheduler.services.group_service import GroupService


def createGroupService(db, groupRepo, storageDirectory="."):
    fileService = GroupFileService(GroupFileRepository(db), groupRepo, str(storageDirectory))
    return GroupService(groupRepo, fileService)


def test_groupFilesTableStartsEmpty():
    db = DuckDBConnection(":memory:")
    assert db.sql("SELECT * FROM groupFiles").fetchall() == []


def test_isMember():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    group = createGroupService(db, groupRepo).createGroup(1, "G")
    assert groupRepo.isMember(group.groupId, 1) is True
    assert groupRepo.isMember(group.groupId, 999) is False


def test_modifyGroupDetailsAllowsMembers():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    groupService = createGroupService(db, groupRepo)
    group = groupService.createGroup(1, "G")

    groupService.modifyGroupDetails(group.groupId, "Updated", None, 1)

    updatedGroup = groupRepo.findById(group.groupId)
    assert updatedGroup.groupName == "Updated"
    assert updatedGroup.description == ""


def test_modifyGroupDetailsRejectsNonMembers():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    groupService = createGroupService(db, groupRepo)
    group = groupService.createGroup(1, "G")

    with pytest.raises(PermissionError, match="Only group members can edit this group"):
        groupService.modifyGroupDetails(group.groupId, "Updated", None, 999)

    assert groupRepo.findById(group.groupId).groupName == "G"


def test_modifyGroupDetailsRequiresExistingGroup():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    groupService = createGroupService(db, groupRepo)

    with pytest.raises(LookupError, match="Group not found"):
        groupService.modifyGroupDetails(999, "Updated", None, 1)


def test_deleteGroupWithNoFiles():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    groupService = createGroupService(db, groupRepo)
    group = groupService.createGroup(1, "G")
    groupService.deleteGroup(group.groupId, 1)
    assert groupRepo.findById(group.groupId) is None


def test_deleteGroupRemovesFileRows():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    groupService = createGroupService(db, groupRepo)
    group = groupService.createGroup(1, "G")
    db.sql(
        "INSERT INTO groupFiles (groupId, fileName, filePath, uploadedAt) VALUES (?, ?, ?, now())",
        [group.groupId, "a.txt", "uploads/a.txt"],
    )
    groupService.deleteGroup(group.groupId, 1)
    assert db.sql("SELECT * FROM groupFiles").fetchall() == []


def test_deleteGroupDoesNotDeleteGroupWhenFileCleanupFails():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    groupService = createGroupService(db, groupRepo)
    group = groupService.createGroup(1, "G")

    def failCleanup(groupId, userId):
        raise RuntimeError("file cleanup failed")

    groupService._fileService.removeGroupFiles = failCleanup
    with pytest.raises(RuntimeError, match="file cleanup failed"):
        groupService.deleteGroup(group.groupId, 1)

    assert groupRepo.findById(group.groupId) is not None
