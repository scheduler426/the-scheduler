"""Builds every repository, service, and controller once and holds the controllers.

buildApplication is the only place that creates dependencies; every other
class receives them through its constructor. Nothing is built when this
module is imported.
"""

from __future__ import annotations

from typing import Optional

from scheduler.controllers.auth_controller import AuthController
from scheduler.controllers.availability_controller import AvailabilityController
from scheduler.controllers.meeting_controller import MeetingController
from scheduler.controllers.password_recovery_controller import PasswordRecoveryController
from scheduler.controllers.scheduling_controller import SchedulingController
from scheduler.controllers.user_controller import UserController
from scheduler.controllers.vote_controller import VoteController
from scheduler.domain.meeting_generator import MeetingGenerator
from scheduler.infrastructure.auth_email_template_factory import AuthEmailTemplateFactory
from scheduler.infrastructure.database import Database
from scheduler.infrastructure.email_service import EmailService
from scheduler.infrastructure.group_email_template_factory import GroupEmailTemplateFactory
from scheduler.infrastructure.ics_parser import IcsParser
from scheduler.infrastructure.ics_exporter import IcsExporter
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.infrastructure.token_provider import TokenProvider
from scheduler.repositories.availability_schedule_repository import AvailabilityScheduleRepository
from scheduler.repositories.group_invitation_repository import GroupInvitationRepository
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.repositories.user_repository import UserRepository
from scheduler.repositories.vote_repository import VoteRepository
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.availability_service import AvailabilityService
from scheduler.services.group_membership_service import GroupMembershipService
from scheduler.services.group_notification_service import GroupNotificationService
from scheduler.services.group_service import GroupService
from scheduler.services.meeting_finalization_service import MeetingFinalizationService
from scheduler.services.meeting_retrieval_service import MeetingRetrievalService
from scheduler.services.meeting_suggestion_service import MeetingSuggestionService
from scheduler.services.password_recovery_service import PasswordRecoveryService
from scheduler.services.user_service import UserService
from scheduler.services.voting_service import VotingService


class Application:
    """The database, the session manager, and one attribute per controller."""
    def __init__(self, database: Database, sessionManager: SessionManager, mailHost: Optional[str] = None):
        self.database = database
        self.sessionManager = sessionManager
        self.mailHost = mailHost
        self.emailService = None
        self.userController = None
        self.authController = None
        self.passwordRecoveryController = None
        self.groupController = None
        self.membershipController = None
        self.groupFileController = None
        self.availabilityController = None
        self.schedulingController = None
        self.voteController = None
        self.meetingController = None
        self.notificationController = None

    def close(self) -> None:
        self.database.close()


def buildApplication(database: Database, secretKey: str, mailHost: Optional[str] = None) -> Application:
    """Create every dependency once over database and return the Application."""
    if not secretKey:
        raise ValueError("secretKey is required")

    hasher = PasswordHasher()
    tokenProvider = TokenProvider(secretKey, tokenValidityInMs=28_800_000)
    sessionManager = SessionManager(tokenProvider)
    resetTokenProvider = TokenProvider(secretKey, tokenValidityInMs=3_600_000)
    emailService = EmailService(host=mailHost)
    icsExporter = IcsExporter()        

    userRepo = UserRepository(database)
    groupRepo = GroupRepository(database)
    inviteRepo = GroupInvitationRepository(database)
    scheduleRepo = AvailabilityScheduleRepository(database)
    pollRepo = MeetingPollRepository(database)
    voteRepo = VoteRepository(database)
    meetingRepo = ScheduledMeetingRepository(database)
    retrievalService = MeetingRetrievalService(meetingRepo)

    authTemplateFactory = AuthEmailTemplateFactory()
    userService = UserService(userRepo, hasher, emailService, authTemplateFactory)
    authService = AuthenticationService(userRepo, sessionManager, hasher)
    passwordRecoveryService = PasswordRecoveryService(
        userRepo, resetTokenProvider, emailService, authTemplateFactory, hasher
    )
    groupService = GroupService(groupRepo)
    membershipService = GroupMembershipService(groupRepo, inviteRepo)
    availabilityService = AvailabilityService(scheduleRepo, IcsParser())
    notificationService = GroupNotificationService(emailService, groupRepo, GroupEmailTemplateFactory())
    suggestionService = MeetingSuggestionService(MeetingGenerator(), pollRepo, scheduleRepo, groupRepo)
    votingService = VotingService(voteRepo, pollRepo, groupRepo)
    finalizationService = MeetingFinalizationService(meetingRepo, pollRepo, notificationService, groupRepo)

    app = Application(database, sessionManager, mailHost)
    app.emailService = emailService
    app.userController = UserController(userService, authService, sessionManager)
    app.authController = AuthController(authService)
    app.passwordRecoveryController = PasswordRecoveryController(passwordRecoveryService)
    app.availabilityController = AvailabilityController(availabilityService, authService)
    app.schedulingController = SchedulingController(suggestionService, finalizationService, authService)
    app.voteController = VoteController(votingService, authService)
    app.meetingController = MeetingController(retrievalService, None, icsExporter, authService)
    return app
