from __future__ import annotations

from datetime import datetime


class ExternalCalendarFile(): 
    def __init__(self, fileName: str, fileSize: int, fileContent: bytes, uploadedAt: datetime):
        self._fileName = fileName
        self._fileSize = fileSize
        self._fileContent = fileContent
        self._uploadedAt = uploadedAt

    @property
    def fileName(self) -> str: 
        return self._fileName

    @property
    def fileSize(self) -> int: 
        return self._fileSize
    
    @property
    def fileContent(self) -> bytes: 
        return self._fileContent
    
    @property
    def uploadedAt(self) -> datetime: 
        return self._uploadedAt
