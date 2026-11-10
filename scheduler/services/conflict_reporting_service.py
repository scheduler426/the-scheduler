# Emails the other group members when someone reports a conflict with a meeting.

from __future__ import annotations

from scheduler.infrastructure.email_service import EmailService
from scheduler.infrastructure.scheduling_email_template_factory import SchedulingEmailTemplateFactory
from scheduler.repositories.group_repository import GroupRepository
from scheduler.services.meeting_retrieval_service import MeetingRetrievalService


class ConflictReportingService:
    def __init__(
        self,
        emailService: EmailService,
        templateFactory: SchedulingEmailTemplateFactory,
        retrievalService: MeetingRetrievalService,
        groupRepo: GroupRepository,
    ):
        self._emailService = emailService
        self._templateFactory = templateFactory
        self._retrievalService = retrievalService
        self._groupRepo = groupRepo

    # Tell the rest of the group that this member has a conflict. Nothing is saved.
    def reportConflict(self, userId: int, meetingId: int, reason: str) -> None:
        if not reason or not reason.strip():
            raise ValueError("A reason is required")
        # Raises LookupError("Meeting not found") if the user can't see it or it is cancelled
        meeting = self._retrievalService.getMeetingForUser(userId, meetingId)
        members = self._groupRepo.findMembers(meeting.groupId)
        reporter = next((m for m in members if m.userId == userId), None)
        if reporter is None:
            raise LookupError("Meeting not found")
        recipients = [m for m in members if m.userId != userId and m.allowEmailReminders]
        if not recipients:
            return
        # MailDeliveryError is not caught here, so it goes up to the caller
        self._emailService.sendBulkEmail(
            [r.email for r in recipients],
            "Schedule conflict reported",
            self._templateFactory.buildConflictNoticeEmail(meeting, reporter, reason),
        )