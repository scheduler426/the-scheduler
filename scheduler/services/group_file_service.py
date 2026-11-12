"""Stores group file contents and their metadata."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from scheduler.repositories.group_file_repository import GroupFileRepository
from scheduler.repositories.group_repository import GroupRepository


class GroupFileService:
    def __init__(self, fileRepo: GroupFileRepository, groupRepo: GroupRepository, storageDirectory: str):
        self._fileRepo = fileRepo
        self._groupRepo = groupRepo
        self._storageDirectory = storageDirectory

    def attachFileToGroup(self, groupId: int, fileName: str, fileBytes: bytes, userId: int) -> int:
        group = self._groupRepo.findById(groupId)
        if group is None:
            raise LookupError("Group not found")
        if not self._groupRepo.isMember(groupId, userId):
            raise PermissionError("Only group members can upload files")
        if not fileName or not fileBytes:
            raise ValueError("A file name and contents are required")
        if len(fileBytes) > 20 * 1024 * 1024:
            raise ValueError("Files must be 20 MiB or smaller")

        baseName = os.path.basename(fileName)
        if os.path.splitext(baseName)[1].lower() not in {".txt", ".pdf", ".docx"}:
            raise ValueError("Group files must be .txt, .pdf, or .docx")

        groupDirectory = os.path.join(self._storageDirectory, str(groupId))
        os.makedirs(groupDirectory, exist_ok=True)
        path = os.path.join(groupDirectory, f"{uuid.uuid4()}-{baseName}")
        with open(path, "wb") as file:
            file.write(fileBytes)

        try:
            return self._fileRepo.saveFileMetadata(groupId, baseName, path, datetime.now())
        except Exception:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            raise

    def getFileStream(self, fileId: int, userId: int) -> tuple[str, str]:
        """Return a member-accessible file's name and resolved absolute path."""
        groupFile = self._fileRepo.findById(fileId)
        if groupFile is None:
            raise LookupError("File not found")
        if not self._groupRepo.isMember(groupFile.groupId, userId):
            raise PermissionError("Only group members can open this file")

        try:
            storageRoot = Path(self._storageDirectory).resolve(strict=True)
            filePath = Path(groupFile.filePath).resolve(strict=True)
        except FileNotFoundError as error:
            raise LookupError("File not found") from error

        try:
            filePath.relative_to(storageRoot)
        except ValueError as error:
            raise LookupError("File not found") from error
        if not filePath.is_file():
            raise LookupError("File not found")

        return groupFile.fileName, str(filePath)

    def removeFileFromGroup(self, fileId: int, userId: int) -> None:
        groupFile = self._fileRepo.findById(fileId)
        if groupFile is None:
            raise LookupError("File not found")
        if not self._groupRepo.isMember(groupFile.groupId, userId):
            raise PermissionError("Only group members can delete this file")

        storageRoot = Path(self._storageDirectory).resolve()
        filePath = Path(groupFile.filePath).resolve()
        try:
            filePath.relative_to(storageRoot)
        except ValueError as error:
            raise LookupError("File not found") from error

        try:
            os.remove(filePath)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise RuntimeError("The file bytes could not be deleted and the record was kept") from error

        try:
            self._fileRepo.deleteById(fileId)
        except Exception as error:
            raise RuntimeError("The file bytes were deleted and the metadata row remains") from error

    def removeGroupFiles(self, groupId: int, userId: int) -> None:
        """Remove every file belonging to a group, stopping on the first failure."""
        for groupFile in self._fileRepo.findByGroupId(groupId):
            self.removeFileFromGroup(groupFile.fileId, userId)
    