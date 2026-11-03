"""Reads and writes user rows. Account rules stay in the services.

UserService and AuthenticationService decide when a save or lookup is
allowed. findByEmail and findById return profile fields only; availability
is loaded by AvailabilityScheduleRepository. delete removes that user's
roster links, availability slots, and votes, then the user row. Invitations
that name the user stay stored. Deleting a whole group is GroupRepository's job.
"""

from __future__ import annotations

from typing import Optional

from scheduler.domain.user import User
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class UserRepository:
    """DuckDB access for the users table through DuckDBConnection.

    save inserts when userId is missing and updates the same columns when
    it is present. This class does not hash passwords or open sessions.
    """
    _COLUMNS = "userId, email, passwordHash, firstName, lastName, allowEmailReminders"

    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findByEmail(self, email: str) -> Optional[User]:
        """Return the user with this email, ignoring case, or None."""
        row = self._db.sql(f"SELECT {self._COLUMNS} FROM users WHERE lower(email) = lower(?)", [email]).fetchone()
        return User(*row[:5], bool(row[5])) if row else None

    def findById(self, userId: int) -> Optional[User]:
        row = self._db.sql(f"SELECT {self._COLUMNS} FROM users WHERE userId = ?", [userId]).fetchone()
        return User(*row[:5], bool(row[5])) if row else None

    def save(self, user: User) -> int:
        """Insert or update the user and return the user id."""
        values = [user.email, user.passwordHash, user.firstName, user.lastName, user.allowEmailReminders]
        if user.userId is None:
            return self._db.sql(
                "INSERT INTO users (email, passwordHash, firstName, lastName, allowEmailReminders) "
                "VALUES (?, ?, ?, ?, ?) RETURNING userId",
                values,
            ).fetchone()[0]
        self._db.sql(
            "UPDATE users SET email = ?, passwordHash = ?, firstName = ?, lastName = ?, "
            "allowEmailReminders = ? WHERE userId = ?",
            values + [user.userId],
        )
        return user.userId

    def delete(self, id: int) -> None:
        """Remove the user's roster rows, availability slots, votes, and account row."""
        self._db.sql("DELETE FROM groupRoster WHERE userId = ?", [id])
        self._db.sql("DELETE FROM availabilitySlots WHERE userId = ?", [id])
        self._db.sql("DELETE FROM votes WHERE userId = ?", [id])
        self._db.sql("DELETE FROM users WHERE userId = ?", [id])
