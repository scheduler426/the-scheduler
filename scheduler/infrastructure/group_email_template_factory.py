# Builds the text of group emails.

from __future__ import annotations


class GroupEmailTemplateFactory:
    def __init__(self):
        self.templateCache: dict[str, str] = {}

    # Text for an invitation: the group name and the token to accept with.
    def buildInvitationEmail(self, groupName: str, token: str) -> str:
        return f"You have been invited to join {groupName}. Use this token to accept: {token}"

    # Text for a reminder: the group name, then the message. No subject.
    def buildReminderEmail(self, groupName: str, message: str) -> str:
        return f'Reminder from your group "{groupName}":\n\n{message}'
