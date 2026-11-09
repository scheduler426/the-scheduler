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
        constraints = {
            "windowStart": request.get("windowStart"),
            "windowEnd": request.get("windowEnd"),
            "durationMinutes": request.get("durationMinutes", 60),
            "stepMinutes": request.get("stepMinutes", 30),
            "maxSuggestions": request.get("maxSuggestions", 5),
            "cadence": request.get("cadence", "weekly"),
        }
        # Leave pollClosesAt out when not given, so the poll closes in 2 days
        if request.get("pollClosesAt") is not None:
            constraints["pollClosesAt"] = request["pollClosesAt"]
        poll = self._suggestionService.generateSuggestions(request.get("groupId"), constraints, session.userId)
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
    
    # Throw away the group's active poll so suggestions can start over
    def handleResetPoll(self, request: dict) -> Response:
        return respond(lambda: self._resetPoll(request))

    def _resetPoll(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        self._suggestionService.resetActivePoll(request.get("groupId"), session.userId)