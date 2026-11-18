"""Handles authenticated requests to create, edit, delete, and list groups."""

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.domain.group import Group
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.group_service import GroupService


class GroupController:
    """Turns group requests into GroupService calls and Responses."""

    def __init__(self, groupService: GroupService, authService: AuthenticationService):
        self._groupService = groupService
        self._authService = authService

    def handleCreateGroup(self, request: dict) -> Response:
        return respond(lambda: self._createGroup(request))

    def handleGetMyGroups(self, request: dict) -> Response:
        return respond(lambda: self._getMyGroups(request))

    def handleEditGroup(self, request: dict) -> Response:
        return respond(lambda: self._editGroup(request))

    def handleDeleteGroup(self, request: dict) -> Response:
        return respond(lambda: self._deleteGroup(request))

    def _createGroup(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        group = self._groupService.createGroup(
            session.userId, request.get("name"), request.get("description", "")
        )
        return self._groupData(group)

    def _getMyGroups(self, request: dict) -> list[dict]:
        session = self._authService.requireSession(request.get("token"))
        return [self._groupData(group) for group in self._groupService.getGroups(session.userId)]

    def _editGroup(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        (groupId,) = self._required(request, "groupId")
        self._groupService.modifyGroupDetails(
            groupId, request.get("name"), request.get("description"), session.userId
        )

    def _deleteGroup(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        (groupId,) = self._required(request, "groupId")
        self._groupService.deleteGroup(groupId, session.userId)

    @staticmethod
    def _required(request: dict, *keys: str) -> list:
        for key in keys:
            if request.get(key) is None:
                raise ValueError(f"{key} is required")
        return [request[key] for key in keys]

    @staticmethod
    def _groupData(group: Group) -> dict:
        return {
            "groupId": group.groupId,
            "groupName": group.groupName,
            "description": group.description,
        }
    