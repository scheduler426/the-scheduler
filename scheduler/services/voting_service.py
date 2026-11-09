from __future__ import annotations

from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.domain.user import User
from scheduler.domain.vote import Vote
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.repositories.vote_repository import VoteRepository

# Turns what the user typed into the stored value
_PREFERENCES = {
    "yes": "yes",
    "if need be": "maybe",
    "maybe": "maybe",
    "can't make it": "no",
    "no": "no",
}

class VotingService:
    """Casts a vote, lists members who have not voted, and reports poll status."""
    def __init__(self, voteRepo: VoteRepository, pollRepo: MeetingPollRepository, groupRepo: GroupRepository):
        self._voteRepo = voteRepo
        self._pollRepo = pollRepo
        self._groupRepo = groupRepo

    def castVote(self, userId: int, pollId: int, suggestionId: int, preference: str) -> Vote:
        stored = _PREFERENCES.get(str(preference).strip().lower())
        if stored is None:
            raise ValueError("Vote must be Yes, If need be, or Can't make it")
        poll = self._pollRepo.findById(pollId)
        if poll is None:
            raise LookupError("Poll not found")
        if not self._groupRepo.isMember(poll.groupId, userId):
            raise PermissionError("Only group members can vote in this poll")
        vote = self._voteRepo.findByPollUserAndSuggestion(pollId, userId, suggestionId)
        if vote is None:
            vote = Vote(None, pollId, userId, suggestionId, stored)
        else:
            vote.changeVote(suggestionId, stored)
        vote.submitVote(poll)
        self._voteRepo.save(vote)
        return vote

    def getUnvotedMembers(self, groupId: int, userId: int) -> list[User]:
        if not self._groupRepo.isMember(groupId, userId):
            raise PermissionError("Only group members can view this poll")
        poll = self._pollRepo.findActiveByGroupId(groupId)
        if poll is None:
            raise LookupError("This group has no active poll")
        voted = set(poll.alreadyVoted)
        return [member for member in self._groupRepo.findMembers(groupId) if member.userId not in voted]

    def getPollStatus(self, groupId: int, userId: int) -> MeetingPoll:
        if not self._groupRepo.isMember(groupId, userId):
            raise PermissionError("Only group members can view this poll")
        poll = self._pollRepo.findActiveByGroupId(groupId)
        if poll is None:
            raise LookupError("This group has no active poll")
        return poll
