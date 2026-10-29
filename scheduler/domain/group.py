from __future__ import annotations

from typing import Optional


class Group:
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
