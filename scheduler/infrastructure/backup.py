"""Makes a dated copy of the DuckDB database file.

An operator runs this once a day; the app does not call it. It copies the
DuckDB database file directly rather than going through Database. To
restore, copy a backup back to the path DuckDBConnection opens, while the
app is stopped.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


def backupDatabase(sourcePath: str, destinationDirectory: str) -> str:
    """Copy sourcePath to destinationDirectory/<name>-<YYYY-MM-DD><ext> and return the copy's path.

    The date is today's UTC date, so a second run on the same day overwrites that day's copy.
    """
    source = Path(sourcePath)
    if not source.is_file():
        raise FileNotFoundError(f"Database file not found: {sourcePath}")
    destination = Path(destinationDirectory)
    destination.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    copyPath = destination / f"{source.stem}-{today}{source.suffix}"
    shutil.copy2(source, copyPath)
    return str(copyPath)
