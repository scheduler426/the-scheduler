# Entry point for casting votes and viewing poll status.

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.voting_service import VotingService


class VoteController:
    def __init__(self, votingService: VotingService, authService: AuthenticationService):
        self._votingService = votingService
        self._authService = authService

    # Return the values for keys, raising ValueError for the first one that is missing
    @staticmethod
    def _required(request: dict, *keys: str) -> list:
        for key in keys:
            if request.get(key) is None:
                raise ValueError(f"{key} is required")
        return [request[key] for key in keys]

    # Cast one vote per choice in the request
    def handleCastVote(self, request: dict) -> Response:
        return respond(lambda: self._castVote(request))

    def _castVote(self, request: dict) -> list[dict]:
        session = self._authService.requireSession(request.get("token"))
        pollId, choices = self._required(request, "pollId", "choices")
        if not isinstance(choices, list):
            raise ValueError("choices must be a list")
        # Check every choice before saving any, so one bad choice saves nothing
        for choice in choices:
            if not isinstance(choice, dict) or choice.get("suggestionId") is None or choice.get("preference") is None:
                raise ValueError("each choice needs suggestionId and preference")
        votes = [
            self._votingService.castVote(session.userId, pollId, c["suggestionId"], c["preference"])
            for c in choices
        ]
        return [
            {
                "voteId": v.voteId,
                "pollId": v.pollId,
                "userId": v.userId,
                "suggestionId": v.suggestionId,
                "votePreference": v.votePreference,
            }
            for v in votes
        ]

    # Show the group's active poll, its tally, and who has not voted
    def handleGetPollStatus(self, request: dict) -> Response:
        return respond(lambda: self._getPollStatus(request))

    def _getPollStatus(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        (groupId,) = self._required(request, "groupId")
        poll = self._votingService.getPollStatus(groupId, session.userId)
        unvoted = self._votingService.getUnvotedMembers(groupId, session.userId)
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
            "voteTally": poll.voteTally,
            "alreadyVoted": list(poll.alreadyVoted),
            "unvotedMembers": [self._publicUser(m) for m in unvoted],
        }

    @staticmethod
    def _publicUser(user) -> dict:
        return {
            "userId": user.userId,
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
            "allowEmailReminders": user.allowEmailReminders,
        }