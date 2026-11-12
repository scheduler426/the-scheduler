class GroupEmailTemplateFactory:
    def __init__(self, templateCache: dict[str, str]):
        self.templateCache = templateCache

    def buildInvitationEmail(self, groupName: str, token: str) -> str:
        template = self.templateCache.get("invitation")
        if template is None:
            raise ValueError("Invitation email template not found")
        return template.format(groupName=groupName, token=token)