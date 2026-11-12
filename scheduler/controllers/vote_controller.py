# Entry point for casting votes and viewing poll status.

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.voting_service import VotingService


class VoteController:
    def __init__(self, votingService: VotingService, authService: AuthenticationService):
        self._votingService = votingService
        self._authService = authService

    # Cast one vote per choice in the request
    def handleCastVote(self, request: dict) -> Response:
        return respond(lambda: self._castVote(request))

    def _castVote(self, request: dict) -> list[dict]:
        session = self._authService.requireSession(request.get("token"))
        choices = request.get("choices")
        if not isinstance(choices, list):
            raise ValueError("choices must be a list")
        votes = [
            self._votingService.castVote(
                session.userId, request.get("pollId"), choice["suggestionId"], choice["preference"]
            )
            for choice in choices
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
        groupId = request.get("groupId")
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