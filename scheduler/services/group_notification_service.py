# Emails chosen group members, skipping anyone who turned off email reminders.

from __future__ import annotations

from scheduler.infrastructure.email_service import EmailService
from scheduler.infrastructure.group_email_template_factory import GroupEmailTemplateFactory
from scheduler.repositories.group_repository import GroupRepository


class GroupNotificationService:
    def __init__(
        self,
        emailService: EmailService,
        groupRepo: GroupRepository,
        templateFactory: GroupEmailTemplateFactory,
    ):
        self._emailService = emailService
        self._groupRepo = groupRepo
        self._templateFactory = templateFactory
    
    # Email the chosen members of a group, skipping anyone who turned off reminders
    def dispatchManualReminder(
        self, groupId: int, targetUserIds: list[int], message: str, senderUserId: int | None = None
    ) -> None:
        if not message or not message.strip():
            raise ValueError("Reminder message is required")
        group = self._groupRepo.findById(groupId)
        if group is None:
            raise LookupError("Group not found")
        # Only checked when a sender is given. Finalize and cancel call this without one.
        if senderUserId is not None and not self._groupRepo.isMember(groupId, senderUserId):
            raise PermissionError("Only group members can send reminders")
        recipients = [
            member
            for member in self._groupRepo.findMembers(groupId)
            if member.userId in targetUserIds and member.allowEmailReminders
        ]
        if not recipients:
            return
        # MailDeliveryError is not caught here, so it goes up to the caller
        self._emailService.sendBulkEmail(
            [member.email for member in recipients],
            f"Reminder from {group.groupName}",
            self._templateFactory.buildReminderEmail(group.groupName, message),
        )