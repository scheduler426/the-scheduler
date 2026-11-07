from __future__ import annotations

from scheduler.domain.user import User
from scheduler.domain.vote import Vote
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.repositories.vote_repository import VoteRepository


class VotingService:
    """Casts a vote and lists members who have not voted. It does not report poll status."""
    def __init__(self, voteRepo: VoteRepository, pollRepo: MeetingPollRepository, groupRepo: GroupRepository):
        self._voteRepo = voteRepo
        self._pollRepo = pollRepo
        self._groupRepo = groupRepo

    def castVote(self, userId: int, pollId: int, suggestionId: int, preference: str) -> Vote:
        poll = self._pollRepo.findById(pollId)
        if poll is None:
            raise LookupError("Poll not found")
        if not self._groupRepo.isMember(poll.groupId, userId):
            raise PermissionError("Only group members can vote in this poll")
        vote = self._voteRepo.findByPollAndUser(pollId, userId)
        if vote is None:
            vote = Vote(None, pollId, userId, suggestionId, preference)
        else:
            vote.changeVote(suggestionId, preference)
        vote.submitVote(poll)
        self._voteRepo.save(vote)
        return vote

    def getUnvotedMembers(self, groupId: int) -> list[User]:
        poll = self._pollRepo.findActiveByGroupId(groupId)
        if poll is None:
            raise LookupError("This group has no active poll")
        voted = set(poll.alreadyVoted)
        return [member for member in self._groupRepo.findMembers(groupId) if member.userId not in voted]
