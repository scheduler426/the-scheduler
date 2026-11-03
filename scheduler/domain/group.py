"""A named group whose members schedule meetings together.

Group stores an id, a name, and a description. GroupRepository persists
that record. Members, invites, polls, and meetings live in their own
repositories. This class does not hold those collections.
"""

from __future__ import annotations

from typing import Optional


class Group:
    """Identity of one group.

    The name is required and stored without surrounding spaces. GroupService
    saves the row and adds the creator to the roster as a separate step.
    """
    def __init__(self, groupId: Optional[int], groupName: str, description: str = ""):
        if not groupName or not groupName.strip():
            raise ValueError("groupName is required")
        self._groupId = groupId
        self._groupName = groupName.strip()
        self._description = description or ""

    @property
    def groupId(self) -> Optional[int]:
        return self._groupId

    @property
    def groupName(self) -> str:
        return self._groupName

    @property
    def description(self) -> str:
        return self._description
