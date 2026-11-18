"""Handles authenticated requests to upload and download group files."""

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.group_file_service import GroupFileService


class GroupFileController:
    """Turns group file requests into GroupFileService calls and Responses."""

    def __init__(self, fileService: GroupFileService, authService: AuthenticationService):
        self._fileService = fileService
        self._authService = authService

    def handleUploadFile(self, request: dict) -> Response:
        return respond(lambda: self._uploadFile(request))

    def handleDownloadFile(self, request: dict) -> Response:
        return respond(lambda: self._downloadFile(request))

    def handleDeleteFile(self, request: dict) -> Response:
        try:
            return respond(lambda: self._deleteFile(request))
        except RuntimeError as error:
            return Response(Response.FILE_ERROR, message=str(error))

    def _uploadFile(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        groupId = self._required(request, "groupId")
        fileName = self._required(request, "fileName")
        fileBytes = self._required(request, "fileBytes")
        fileId = self._fileService.attachFileToGroup(groupId, fileName, fileBytes, session.userId)
        return {"fileId": fileId, "fileName": fileName}

    def _downloadFile(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        fileId = self._required(request, "fileId")
        fileName, path = self._fileService.getFileStream(fileId, session.userId)
        return {"fileName": fileName, "path": path}

    def _deleteFile(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        fileId = self._required(request, "fileId")
        self._fileService.removeFileFromGroup(fileId, session.userId)

    @staticmethod
    def _required(request: dict, key: str):
        if request.get(key) is None:
            raise ValueError(f"{key} is required")
        return request[key]