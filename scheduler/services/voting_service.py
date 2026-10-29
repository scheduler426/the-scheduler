from __future__ import annotations

from scheduler.domain.user import User
from scheduler.domain.vote import Vote
from scheduler.repositories.group_roster_repository import GroupRosterRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.repositories.vote_repository import VoteRepository


class VotingService:
    def __init__(self, voteRepo: VoteRepository, pollRepo: MeetingPollRepository, rosterRepo: GroupRosterRepository):
        self._voteRepo = voteRepo
        self._pollRepo = pollRepo
        self._rosterRepo = rosterRepo

    def castVote(self, userId: int, pollId: int, suggestionId: int, preference: str) -> Vote:
        poll = self._pollRepo.findById(pollId)
        if poll is None:
            raise LookupError("Poll not found")
        if not any(member.userId == userId for member in self._rosterRepo.findByGroupId(poll.groupId)):
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
        return [member for member in self._rosterRepo.findByGroupId(groupId) if member.userId not in voted]
