# Entry point for listing a user's meetings (conflict reports and .ics export come in later tasks).

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.meeting_retrieval_service import MeetingRetrievalService


class MeetingController:
    def __init__(
        self,
        retrievalService: MeetingRetrievalService,
        conflictService,
        icsExporter,
        authService: AuthenticationService,
    ):
        self._retrievalService = retrievalService
        # None until D3-10 (conflict reports) and D3-9 (.ics export) exist
        self._conflictService = conflictService
        self._icsExporter = icsExporter
        self._authService = authService

    # List the signed-in user's meetings that are still on
    def handleGetMyMeetings(self, request: dict) -> Response:
        return respond(lambda: self._getMyMeetings(request))

    def _getMyMeetings(self, request: dict) -> list[dict]:
        session = self._authService.requireSession(request.get("token"))
        meetings = self._retrievalService.getUserMeetings(session.userId)
        return [
            {
                "meetingId": m.meetingId,
                "groupId": m.groupId,
                "meetingName": m.meetingName,
                "status": m.status,
                "scheduledSlots": [
                    {"startTime": s.startTime, "endTime": s.endTime, "cadence": s.cadence}
                    for s in m.scheduledSlots
                ],
            }
            for m in meetings
        ]
    # Return one meeting as an .ics file for the front end to write
    def handleExportIcs(self, request: dict) -> Response:
        return respond(lambda: self._exportIcs(request))

    def _exportIcs(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        meetingId = request.get("meetingId")
        # A missing or cancelled meeting raises LookupError, which comes back notFound
        meeting = self._retrievalService.getMeetingForUser(session.userId, meetingId)
        return {
            "fileName": f"meeting-{meetingId}.ics",
            "content": self._icsExporter.exportMeetingToIcs(meeting),
        }
        # Tell the group the signed-in user has a conflict with a meeting
    def handleReportConflict(self, request: dict) -> Response:
        return respond(lambda: self._reportConflict(request))

    def _reportConflict(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        meetingId = request.get("meetingId")
        reason = request.get("reason")
        self._conflictService.reportConflict(session.userId, meetingId, reason)
        return {"meetingId": meetingId, "reason": reason}