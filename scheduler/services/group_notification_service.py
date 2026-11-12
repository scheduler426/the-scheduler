# Emails chosen group members, skipping anyone who turned off email reminders.

from __future__ import annotations
from datetime import datetime

from scheduler.domain.notification import Notification
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.infrastructure.email_service import EmailService, MailDeliveryError
from scheduler.infrastructure.group_email_template_factory import GroupEmailTemplateFactory
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.notification_repository import NotificationRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.repositories.user_repository import UserRepository



class GroupNotificationService:
    def __init__(
        self,
        emailService: EmailService,
        groupRepo: GroupRepository,
        templateFactory: GroupEmailTemplateFactory,
        notificationRepo: NotificationRepository,
        meetingRepo: ScheduledMeetingRepository,
        userRepo: UserRepository,
    ):
        self._emailService = emailService
        self._groupRepo = groupRepo
        self._templateFactory = templateFactory
        self._notificationRepo = notificationRepo
        self._meetingRepo = meetingRepo
        self._userRepo = userRepo
    
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
    # Store a reminder for one of the user's scheduled meetings. Returns the reminder id.
    def scheduleMeetingReminder(self, userId: int, meetingId: int, sendAt: datetime) -> int:
        meeting = next(
            (
                m
                for m in self._meetingRepo.findAllByUserId(userId)
                if m.meetingId == meetingId and m.status == ScheduledMeeting.SCHEDULED
            ),
            None,
        )
        if meeting is None:
            raise LookupError("Meeting not found")
        if sendAt <= datetime.now():
            raise ValueError("Reminder time must be in the future")
        notification = Notification(None, meeting.groupId, userId, meetingId, "", sendAt, Notification.SCHEDULED)
        # The first slot's start time goes in the message. A meeting with no slots just gets its name.
        slots = meeting.scheduledSlots
        text = f'Reminder: "{meeting.meetingName}"'
        if slots:
            text += f" starts {slots[0].startTime}"
        notification.setMessage(text)
        return self._notificationRepo.save(notification)
    # Send every reminder whose time has come. A failed send stays scheduled for the next run.
    def deliverDueReminders(self, now: datetime) -> None:
        for notification in self._notificationRepo.findDue(now):
            user = self._userRepo.findById(notification.userId)
            if user is None or not user.allowEmailReminders:
                # Nobody to email, so close it out without sending
                notification.markSent()
                self._notificationRepo.save(notification)
                continue
            try:
                self._emailService.sendEmail(user.email, "Meeting reminder", notification.message)
            except MailDeliveryError:
                # Leave it scheduled and move on to the next one
                continue
            notification.markSent()
            self._notificationRepo.save(notification)