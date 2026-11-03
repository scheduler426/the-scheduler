"""Creates, edits, lists, and deletes groups.

GroupRepository stores the group. GroupRosterRepository records the creator
as a member. deleteGroup goes through GroupRepository, which also deletes
that group's polls, meetings, invitations, and roster. This service does
not invite members or schedule meetings.
"""

from __future__ import annotations

from typing import Optional

from scheduler.domain.group import Group
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.group_roster_repository import GroupRosterRepository


class GroupService:
    """Group records for someone creating or listing them.

    createGroup saves the group, then adds userId to the roster.
    modifyGroupDetails leaves a name or description unchanged when the
    caller passes None.
    """
    def __init__(self, groupRepo: GroupRepository, rosterRepo: GroupRosterRepository):
        self._groupRepo = groupRepo
        self._rosterRepo = rosterRepo

    def createGroup(self, userId: int, name: str, desc: str = "") -> Group:
        """Save the group, add the creator to the roster, and return the stored group."""
        groupId = self._groupRepo.save(Group(None, name, desc))
        self._rosterRepo.save(groupId, userId)
        return self._requireGroup(groupId)

    def modifyGroupDetails(self, groupId: int, name: Optional[str], desc: Optional[str]) -> None:
        """Update the name, the description, or both. None keeps the current value."""
        group = self._requireGroup(groupId)
        self._groupRepo.save(
            Group(
                groupId,
                group.groupName if name is None else name,
                group.description if desc is None else desc,
            )
        )

    def deleteGroup(self, groupId: int) -> None:
        """Delete the group after checking that it exists. Related rows go with GroupRepository.delete."""
        self._requireGroup(groupId)
        self._groupRepo.delete(groupId)

    def getGroups(self, userId: int) -> list[Group]:
        return self._groupRepo.findAllByUserId(userId)

    def _requireGroup(self, groupId: int) -> Group:
        group = self._groupRepo.findById(groupId)
        if group is None:
            raise LookupError("Group not found")
        return group
