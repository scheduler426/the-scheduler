class GroupEmailTemplateFactory:
    def __init__(self):
        pass

    def buildInvitationEmail(self, groupName: str, token: str) -> str:
        return f"You have been invited to join {groupName}. Use this token to accept: {token}"