"""Storage contract the repositories depend on instead of a specific engine.

Repositories hold a Database and call sql on it. DuckDBConnection is the
current implementation; another engine is added by writing a new subclass
and passing it to the repositories, without editing them. Repository SQL
sticks to syntax DuckDB, SQLite, and PostgreSQL share (ON CONFLICT,
RETURNING) with ? placeholders, which an implementation translates if its
driver uses a different style.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol, Sequence


class QueryResult(Protocol):
    """Rows returned by Database.sql."""
    def fetchone(self) -> Optional[tuple]: ...

    def fetchall(self) -> list[tuple]: ...


class Database(ABC):
    """A connection that runs parameterized SQL and returns its rows."""
    @abstractmethod
    def cursor(self) -> Any:
        """Return a cursor for work that needs its own connection state."""
        ...

    @abstractmethod
    def sql(self, query: str, params: Optional[Sequence[Any]] = None) -> QueryResult:
        """Run query with params bound to its ? placeholders."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release the connection."""
        ...
