"""Authenticated group file requests through GroupFileController."""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
import scheduler.services.group_file_service as group_file_service_module


@pytest.fixture
def groupFileApp(tmp_path, monkeypatch):
    monkeypatch.setenv("GROUP_FILE_DIR", str(tmp_path))
    app = buildApplication(DuckDBConnection(":memory:"), "test-secret", mailHost="console")
    registered = app.userController.handleRegisterUser(
        {"email": "file.member@ilstu.edu", "password": "secret12", "firstName": "File", "lastName": "Member"}
    )
    token = app.sessionManager.createSession(registered.data["userId"]).token
    group = app.groupController.handleCreateGroup({"token": token, "name": "IT 426"})
    yield app, token, group.data["groupId"]
    app.close()


def test_uploadAndDownloadFile(groupFileApp):
    app, token, groupId = groupFileApp
    contents = b"Group notes"

    upload = app.groupFileController.handleUploadFile(
        {"token": token, "groupId": groupId, "fileName": "notes.txt", "fileBytes": contents}
    )

    assert upload.status == "ok"
    assert upload.data["fileName"] == "notes.txt"
    assert isinstance(upload.data["fileId"], int)

    download = app.groupFileController.handleDownloadFile({"token": token, "fileId": upload.data["fileId"]})

    assert download.status == "ok"
    assert download.data["fileName"] == "notes.txt"
    assert Path(download.data["path"]).read_bytes() == contents


def test_handleDeleteFileRemovesFile(groupFileApp):
    app, token, groupId = groupFileApp
    upload = app.groupFileController.handleUploadFile(
        {"token": token, "groupId": groupId, "fileName": "notes.txt", "fileBytes": b"Group notes"}
    )
    path = Path(app.groupFileController.handleDownloadFile(
        {"token": token, "fileId": upload.data["fileId"]}
    ).data["path"])

    response = app.groupFileController.handleDeleteFile({"token": token, "fileId": upload.data["fileId"]})

    assert response.status == "ok" and response.data is None
    assert not path.exists()


def test_handleDeleteFileMapsRuntimeErrorToFileError(groupFileApp, monkeypatch):
    app, token, groupId = groupFileApp
    upload = app.groupFileController.handleUploadFile(
        {"token": token, "groupId": groupId, "fileName": "notes.txt", "fileBytes": b"Group notes"}
    )
    errorMessage = "The file bytes could not be deleted and the record was kept"

    def failDelete(fileId, userId):
        raise RuntimeError(errorMessage)

    monkeypatch.setattr(app.groupFileController._fileService, "removeFileFromGroup", failDelete)

    response = app.groupFileController.handleDeleteFile({"token": token, "fileId": upload.data["fileId"]})

    assert response.status == "fileError"
    assert response.message == errorMessage


def test_uploadingPptxCreatesNoFileOrMetadata(groupFileApp, tmp_path):
    app, token, groupId = groupFileApp

    response = app.groupFileController.handleUploadFile(
        {"token": token, "groupId": groupId, "fileName": "slides.pptx", "fileBytes": b"slides"}
    )

    assert response.status == "invalid"
    assert app.database.sql("SELECT count(*) FROM groupFiles").fetchone()[0] == 0
    assert list(tmp_path.rglob("*")) == []


def test_readOnlyStorageFailureReturnsFileError(groupFileApp, monkeypatch):
    app, token, groupId = groupFileApp
    upload = app.groupFileController.handleUploadFile(
        {"token": token, "groupId": groupId, "fileName": "notes.txt", "fileBytes": b"Group notes"}
    )
    fileId = upload.data["fileId"]
    storedPath = app.groupFileController.handleDownloadFile({"token": token, "fileId": fileId}).data["path"]

    def denyRemoval(path):
        raise PermissionError("storage folder is read-only")

    monkeypatch.setattr(group_file_service_module, "os", SimpleNamespace(remove=denyRemoval))

    response = app.groupFileController.handleDeleteFile({"token": token, "fileId": fileId})

    assert response.status == "fileError"
    assert app.database.sql("SELECT count(*) FROM groupFiles WHERE fileId = ?", [fileId]).fetchone()[0] == 1
    assert Path(storedPath).exists()


def test_deletingGroupThroughControllerRemovesItsFilesAndRows(groupFileApp):
    app, token, groupId = groupFileApp
    uploads = [
        app.groupFileController.handleUploadFile(
            {"token": token, "groupId": groupId, "fileName": fileName, "fileBytes": contents}
        )
        for fileName, contents in [("first.txt", b"first"), ("second.pdf", b"second")]
    ]
    storedPaths = [
        app.groupFileController.handleDownloadFile({"token": token, "fileId": upload.data["fileId"]}).data["path"]
        for upload in uploads
    ]

    response = app.groupController.handleDeleteGroup({"token": token, "groupId": groupId})

    assert response.status == "ok"
    assert all(not Path(path).exists() for path in storedPaths)
    assert app.database.sql("SELECT count(*) FROM groupFiles WHERE groupId = ?", [groupId]).fetchone()[0] == 0
    assert app.database.sql("SELECT 1 FROM groups WHERE groupId = ?", [groupId]).fetchone() is None


@pytest.mark.parametrize(
    "handler,payload",
    [
        ("handleUploadFile", {"groupId": 1, "fileName": "notes.txt", "fileBytes": b"data"}),
        ("handleDownloadFile", {"fileId": 1}),
        ("handleDeleteFile", {"fileId": 1}),
    ],
)
def test_groupFileHandlersRequireSession(groupFileApp, handler, payload):
    app, _, _ = groupFileApp

    response = getattr(app.groupFileController, handler)(payload)

    assert response.status == "unauthenticated"
