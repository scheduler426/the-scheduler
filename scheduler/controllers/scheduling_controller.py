# Entry point for generating suggestions, resetting a poll, and confirming a meeting time

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.meeting_finalization_service import MeetingFinalizationService
from scheduler.services.meeting_suggestion_service import MeetingSuggestionService


class SchedulingController:
    def __init__(
        self,
        suggestionService: MeetingSuggestionService,
        finalizationService: MeetingFinalizationService,
        authService: AuthenticationService,
    ):
        self._suggestionService = suggestionService
        self._finalizationService = finalizationService
        self._authService = authService

    # Build a poll of suggested meeting times for a group
    def handleGenerateSuggestions(self, request: dict) -> Response:
        return respond(lambda: self._generateSuggestions(request))

    def _generateSuggestions(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        groupId, windowStart, windowEnd = self._required(request, "groupId", "windowStart", "windowEnd")
        constraints = {
            "windowStart": windowStart,
            "windowEnd": windowEnd,
            "durationMinutes": request.get("durationMinutes", 60),
            "stepMinutes": request.get("stepMinutes", 30),
            "maxSuggestions": request.get("maxSuggestions", 5),
            "cadence": request.get("cadence", "weekly"),
        }
        if request.get("pollClosesAt") is not None:
            constraints["pollClosesAt"] = request["pollClosesAt"]
        poll = self._suggestionService.generateSuggestions(groupId, constraints, session.userId)
        return self._pollData(poll)

    @staticmethod
    def _pollData(poll) -> dict:
        return {
            "pollId": poll.pollId,
            "groupId": poll.groupId,
            "closesAt": poll.closesAt,
            "isActive": poll.isActive,
            "suggestions": [
                {
                    "suggestionId": suggestionId,
                    "startTime": slot.startTime,
                    "endTime": slot.endTime,
                    "cadence": slot.cadence,
                }
                for suggestionId, slot in poll.suggestions.items()
            ],
        }
    # Return the values for keys, raising ValueError for the first one that is missing
    @staticmethod
    def _required(request: dict, *keys: str) -> list:
        for key in keys:
            if request.get(key) is None:
                raise ValueError(f"{key} is required")
        return [request[key] for key in keys]    
    
    # Throw away the group's active poll so suggestions can start over
    def handleResetPoll(self, request: dict) -> Response:
        return respond(lambda: self._resetPoll(request))

    def _resetPoll(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        (groupId,) = self._required(request, "groupId")
        self._suggestionService.resetActivePoll(groupId, session.userId)

    # Lock in the final meeting time (the top-voted one if no suggestionId is given)
    def handleFinalizeMeeting(self, request: dict) -> Response:
        return respond(lambda: self._finalizeMeeting(request))

    def _finalizeMeeting(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        (groupId,) = self._required(request, "groupId")
        meeting = self._finalizationService.confirmFinalTime(
            groupId,
            request.get("suggestionId"),
            session.userId,
            request.get("meetingName") or "Group meeting",
        )
        return {
            "meetingId": meeting.meetingId,
            "groupId": meeting.groupId,
            "meetingName": meeting.meetingName,
            "status": meeting.status,
            "scheduledSlots": [
                {"startTime": s.startTime, "endTime": s.endTime, "cadence": s.cadence}
                for s in meeting.scheduledSlots
            ],
        }
    # Cancel a meeting and email the other members
    def handleCancelMeeting(self, request: dict) -> Response:
        return respond(lambda: self._cancelMeeting(request))

    def _cancelMeeting(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        (meetingId,) = self._required(request, "meetingId")
        self._finalizationService.cancelMeeting(meetingId, session.userId)