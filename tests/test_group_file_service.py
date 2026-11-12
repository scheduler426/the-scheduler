"""Group file validation, storage, and metadata rollback tests."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from scheduler.domain.group import Group
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_file_repository import GroupFileRepository
from scheduler.repositories.group_repository import GroupRepository
from scheduler.services.group_file_service import GroupFileService


@pytest.fixture
def fileContext(tmp_path):
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    groupId = groupRepo.save(Group(None, "IT 426"))
    groupRepo.addMember(groupId, 17)
    fileRepo = GroupFileRepository(db)
    service = GroupFileService(fileRepo, groupRepo, str(tmp_path))
    yield db, groupRepo, fileRepo, service, groupId
    db.close()


def test_attachFileToGroupStoresContentsAndMetadata(fileContext, tmp_path):
    db, _, fileRepo, service, groupId = fileContext
    content = b"Group notes"

    fileId = service.attachFileToGroup(groupId, r"..\notes.TXT", content, 17)

    groupFile = fileRepo.findById(fileId)
    assert groupFile.fileName == "notes.TXT"
    assert groupFile.groupId == groupId
    assert groupFile.uploadedAt is not None
    assert os.path.basename(os.path.dirname(groupFile.filePath)) == str(groupId)
    assert Path(groupFile.filePath).read_bytes() == content
    assert db.sql("SELECT fileId FROM groupFiles WHERE fileId = ?", [fileId]).fetchone() == (fileId,)


@pytest.mark.parametrize(
    "fileName,fileBytes,message",
    [
        ("", b"contents", "A file name and contents are required"),
        ("notes.txt", b"", "A file name and contents are required"),
        ("notes.exe", b"contents", "Group files must be .txt, .pdf, or .docx"),
        ("notes.txt", b"x" * (20 * 1024 * 1024 + 1), "Files must be 20 MiB or smaller"),
    ],
)
def test_attachFileToGroupRejectsInvalidInput(fileContext, fileName, fileBytes, message):
    _, _, fileRepo, service, groupId = fileContext

    with pytest.raises(ValueError, match=message):
        service.attachFileToGroup(groupId, fileName, fileBytes, 17)

    assert fileRepo.findByGroupId(groupId) == []


def test_attachFileToGroupRejectsNonMembers(fileContext):
    _, _, fileRepo, service, groupId = fileContext

    with pytest.raises(PermissionError, match="Only group members can upload files"):
        service.attachFileToGroup(groupId, "notes.txt", b"contents", 99)

    assert fileRepo.findByGroupId(groupId) == []


def test_attachFileToGroupRemovesFileWhenMetadataSaveFails(fileContext, monkeypatch, tmp_path):
    _, _, fileRepo, service, groupId = fileContext

    def failSave(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(fileRepo, "saveFileMetadata", failSave)

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.attachFileToGroup(groupId, "notes.txt", b"contents", 17)

    assert list((tmp_path / str(groupId)).iterdir()) == []


def test_getFileStreamReturnsNameAndAbsolutePath(fileContext):
    _, _, _, service, groupId = fileContext
    fileId = service.attachFileToGroup(groupId, "notes.txt", b"Group notes", 17)

    fileName, filePath = service.getFileStream(fileId, 17)

    assert fileName == "notes.txt"
    assert Path(filePath).is_absolute()
    assert Path(filePath).read_bytes() == b"Group notes"


def test_getFileStreamRejectsMissingFileMetadata(fileContext):
    _, _, _, service, _ = fileContext

    with pytest.raises(LookupError, match="File not found"):
        service.getFileStream(999, 17)


def test_getFileStreamRequiresGroupMembership(fileContext):
    _, _, _, service, groupId = fileContext
    fileId = service.attachFileToGroup(groupId, "notes.txt", b"Group notes", 17)

    with pytest.raises(PermissionError, match="Only group members can open this file"):
        service.getFileStream(fileId, 99)


def test_getFileStreamRejectsOutsideStoragePathAndKeepsMetadata(fileContext, tmp_path):
    _, _, fileRepo, service, groupId = fileContext
    outsidePath = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outsidePath.write_bytes(b"outside")
    fileId = fileRepo.saveFileMetadata(groupId, "outside.txt", str(outsidePath), datetime.now())

    with pytest.raises(LookupError, match="File not found"):
        service.getFileStream(fileId, 17)

    assert fileRepo.findById(fileId) is not None
    outsidePath.unlink()


def test_getFileStreamRejectsMissingDiskFileAndKeepsMetadata(fileContext, tmp_path):
    _, _, fileRepo, service, groupId = fileContext
    missingPath = tmp_path / str(groupId) / "missing.txt"
    fileId = fileRepo.saveFileMetadata(groupId, "missing.txt", str(missingPath), datetime.now())

    with pytest.raises(LookupError, match="File not found"):
        service.getFileStream(fileId, 17)

    assert fileRepo.findById(fileId) is not None


def test_removeFileFromGroupDeletesBytesThenMetadataAndIsSafeToRepeat(fileContext):
    _, _, fileRepo, service, groupId = fileContext
    fileId = service.attachFileToGroup(groupId, "notes.txt", b"Group notes", 17)
    filePath = Path(fileRepo.findById(fileId).filePath)

    service.removeFileFromGroup(fileId, 17)

    assert not filePath.exists()
    assert fileRepo.findById(fileId) is None
    with pytest.raises(LookupError, match="File not found"):
        service.removeFileFromGroup(fileId, 17)


def test_removeFileFromGroupDeletesMetadataWhenBytesAreAlreadyGone(fileContext):
    _, _, fileRepo, service, groupId = fileContext
    fileId = service.attachFileToGroup(groupId, "notes.txt", b"Group notes", 17)
    Path(fileRepo.findById(fileId).filePath).unlink()

    service.removeFileFromGroup(fileId, 17)

    assert fileRepo.findById(fileId) is None


def test_removeFileFromGroupRejectsMissingMetadata(fileContext):
    _, _, _, service, _ = fileContext

    with pytest.raises(LookupError, match="File not found"):
        service.removeFileFromGroup(999, 17)


def test_removeFileFromGroupRequiresGroupMembership(fileContext):
    _, _, fileRepo, service, groupId = fileContext
    fileId = service.attachFileToGroup(groupId, "notes.txt", b"Group notes", 17)
    filePath = Path(fileRepo.findById(fileId).filePath)

    with pytest.raises(PermissionError, match="Only group members can delete this file"):
        service.removeFileFromGroup(fileId, 99)

    assert filePath.exists()
    assert fileRepo.findById(fileId) is not None


def test_removeFileFromGroupKeepsMetadataWhenDiskDeleteFails(fileContext, monkeypatch):
    _, _, fileRepo, service, groupId = fileContext
    fileId = service.attachFileToGroup(groupId, "notes.txt", b"Group notes", 17)
    filePath = Path(fileRepo.findById(fileId).filePath)

    def failRemove(path):
        raise PermissionError("access denied")

    monkeypatch.setattr(os, "remove", failRemove)
    with pytest.raises(RuntimeError, match="The file bytes could not be deleted and the record was kept"):
        service.removeFileFromGroup(fileId, 17)

    assert filePath.exists()
    assert fileRepo.findById(fileId) is not None


def test_removeFileFromGroupReportsMetadataFailureAfterDeletingBytes(fileContext, monkeypatch):
    _, _, fileRepo, service, groupId = fileContext
    fileId = service.attachFileToGroup(groupId, "notes.txt", b"Group notes", 17)
    filePath = Path(fileRepo.findById(fileId).filePath)

    def failDelete(fileId):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(fileRepo, "deleteById", failDelete)
    with pytest.raises(RuntimeError, match="The file bytes were deleted and the metadata row remains"):
        service.removeFileFromGroup(fileId, 17)

    assert not filePath.exists()
    assert fileRepo.findById(fileId) is not None


def test_removeGroupFilesRemovesEveryGroupFile(fileContext):
    _, _, fileRepo, service, groupId = fileContext
    fileIds = [
        service.attachFileToGroup(groupId, "first.txt", b"first", 17),
        service.attachFileToGroup(groupId, "second.txt", b"second", 17),
    ]

    service.removeGroupFiles(groupId, 17)

    assert fileRepo.findByGroupId(groupId) == []
    assert all(fileRepo.findById(fileId) is None for fileId in fileIds)


def test_removeGroupFilesStopsAndPropagatesOnFirstFailure(fileContext, monkeypatch):
    _, _, fileRepo, service, groupId = fileContext
    firstFileId = service.attachFileToGroup(groupId, "first.txt", b"first", 17)
    secondFileId = service.attachFileToGroup(groupId, "second.txt", b"second", 17)
    calls = []

    def failFirst(fileId, userId):
        calls.append(fileId)
        raise RuntimeError("delete failed")

    monkeypatch.setattr(service, "removeFileFromGroup", failFirst)
    with pytest.raises(RuntimeError, match="delete failed"):
        service.removeGroupFiles(groupId, 17)

    assert calls == [firstFileId]
    assert fileRepo.findById(firstFileId) is not None
    assert fileRepo.findById(secondFileId) is not None
