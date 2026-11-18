# Builds the text of group emails.

from __future__ import annotations


class GroupEmailTemplateFactory:
    def __init__(self):
        self.templateCache: dict[str, str] = {}

    # Text for a reminder: the group name, then the message. No subject.
    def buildReminderEmail(self, groupName: str, message: str) -> str:
        return f'Reminder from your group "{groupName}":\n\n{message}'