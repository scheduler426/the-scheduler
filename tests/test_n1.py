"""N1: backupDatabase."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from scheduler.infrastructure.backup import backupDatabase
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


def test_backupMakesDatedCopy(tmp_path):
    sourcePath = str(tmp_path / "scheduler.duckdb")
    db = DuckDBConnection(sourcePath)
    db.sql("INSERT INTO groups (groupName) VALUES ('G')")
    db.close()

    copyPath = backupDatabase(sourcePath, str(tmp_path / "backups"))

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert os.path.basename(copyPath) == f"scheduler-{today}.duckdb"
    assert os.path.getsize(copyPath) == os.path.getsize(sourcePath)
    restored = DuckDBConnection(copyPath)
    assert restored.sql("SELECT groupName FROM groups").fetchall() == [("G",)]
    restored.close()


def test_backupTwiceSameDayOverwrites(tmp_path):
    sourcePath = tmp_path / "data.duckdb"
    sourcePath.write_bytes(b"first")
    backupDatabase(str(sourcePath), str(tmp_path / "backups"))
    sourcePath.write_bytes(b"second!")
    copyPath = backupDatabase(str(sourcePath), str(tmp_path / "backups"))
    assert len(os.listdir(tmp_path / "backups")) == 1
    assert open(copyPath, "rb").read() == b"second!"


def test_missingSourceRaises(tmp_path):
    with pytest.raises(FileNotFoundError):
        backupDatabase(str(tmp_path / "missing.duckdb"), str(tmp_path / "backups"))
