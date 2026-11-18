from __future__ import annotations

from datetime import datetime
from typing import Optional


class GroupFile:
    def __init__(self, fileId: Optional[int], groupId: int, fileName: str, filePath: str, uploadedAt: datetime):
        self._fileId = fileId
        self._groupId = groupId
        self._fileName = fileName
        self._filePath = filePath
        self._uploadedAt = uploadedAt

    @property
    def fileId(self) -> Optional[int]:
        return self._fileId

    @property
    def groupId(self) -> int:
        return self._groupId

    @property
    def fileName(self) -> str:
        return self._fileName

    @property
    def filePath(self) -> str:
        return self._filePath

    @property
    def uploadedAt(self) -> datetime:
        return self._uploadedAt