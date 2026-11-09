"""DuckDB implementation of Database and the tables the repositories use.

Repositories receive this object as a Database and call sql on it instead
of opening their own database. Construction creates the sequences and
tables for users, groups, rosters, invitations, availability, polls, votes,
meetings, and group file metadata. There are no tables for conflict reports
or outbound mail.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import duckdb

from scheduler.infrastructure.database import Database


class DuckDBConnection(Database):
    """One DuckDB database, in memory unless connectionPath is a file.

    cursor and sql are the operations repositories need. Who may vote, and
    which poll is closed, is decided by domain objects and services.
    """
    _SCHEMA = (
        "CREATE SEQUENCE IF NOT EXISTS userIdSeq START 1",
        "CREATE SEQUENCE IF NOT EXISTS groupIdSeq START 1",
        "CREATE SEQUENCE IF NOT EXISTS pollIdSeq START 1",
        "CREATE SEQUENCE IF NOT EXISTS voteIdSeq START 1",
        "CREATE SEQUENCE IF NOT EXISTS meetingIdSeq START 1",
        "CREATE SEQUENCE IF NOT EXISTS fileIdSeq START 1",
        """
        CREATE TABLE IF NOT EXISTS users (
            userId INTEGER PRIMARY KEY DEFAULT nextval('userIdSeq'),
            email VARCHAR NOT NULL UNIQUE,
            passwordHash VARCHAR NOT NULL,
            firstName VARCHAR NOT NULL,
            lastName VARCHAR NOT NULL,
            allowEmailReminders BOOLEAN NOT NULL DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS groups (
            groupId INTEGER PRIMARY KEY DEFAULT nextval('groupIdSeq'),
            groupName VARCHAR NOT NULL,
            description VARCHAR
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS groupRoster (
            groupId INTEGER NOT NULL,
            userId INTEGER NOT NULL,
            PRIMARY KEY (groupId, userId)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS groupInvitations (
            inviteToken VARCHAR PRIMARY KEY,
            groupId INTEGER NOT NULL,
            inviterUserId INTEGER NOT NULL,
            inviteeEmail VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            expiresAt TIMESTAMP NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS availabilitySlots (
            userId INTEGER NOT NULL,
            startTime TIMESTAMP NOT NULL,
            endTime TIMESTAMP NOT NULL,
            cadence VARCHAR NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS meetingPolls (
            pollId INTEGER PRIMARY KEY DEFAULT nextval('pollIdSeq'),
            groupId INTEGER NOT NULL,
            closesAt TIMESTAMP NOT NULL,
            isActive BOOLEAN NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS pollSuggestions (
            pollId INTEGER NOT NULL,
            suggestionId INTEGER NOT NULL,
            startTime TIMESTAMP NOT NULL,
            endTime TIMESTAMP NOT NULL,
            cadence VARCHAR NOT NULL,
            PRIMARY KEY (pollId, suggestionId)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS votes (
            voteId INTEGER PRIMARY KEY DEFAULT nextval('voteIdSeq'),
            pollId INTEGER NOT NULL,
            userId INTEGER NOT NULL,
            suggestionId INTEGER NOT NULL,
            votePreference VARCHAR NOT NULL,
            UNIQUE (pollId, userId, suggestionID)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS scheduledMeetings (
            meetingId INTEGER PRIMARY KEY DEFAULT nextval('meetingIdSeq'),
            groupId INTEGER NOT NULL,
            meetingName VARCHAR NOT NULL,
            status VARCHAR NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS meetingSlots (
            meetingId INTEGER NOT NULL,
            startTime TIMESTAMP NOT NULL,
            endTime TIMESTAMP NOT NULL,
            cadence VARCHAR NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS groupFiles (
            fileId INTEGER PRIMARY KEY DEFAULT nextval('fileIdSeq'),
            groupId INTEGER NOT NULL,
            fileName VARCHAR NOT NULL,
            filePath VARCHAR NOT NULL,
            uploadedAt TIMESTAMP NOT NULL
        )
        """,
    )

    def __init__(self, connectionPath: str = ":memory:"):
        self._connectionPath = connectionPath
        self._connection = duckdb.connect(connectionPath)
        self._initializeSchema()

    def cursor(self) -> duckdb.DuckDBPyConnection:
        return self._connection.cursor()

    def sql(self, query: str, params: Optional[Sequence[Any]] = None) -> duckdb.DuckDBPyConnection:
        """Run query with params and return the DuckDB result."""
        return self._connection.execute(query, list(params or []))

    def close(self) -> None:
        self._connection.close()

    def _initializeSchema(self) -> None:
        for statement in self._SCHEMA:
            self.sql(statement)
