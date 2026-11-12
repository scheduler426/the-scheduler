# Entry point for viewing, editing, and importing a user's availability

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.domain.time_slot import TimeSlot
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.availability_service import AvailabilityService


class AvailabilityController:
    def __init__(self, availabilityService: AvailabilityService, authService: AuthenticationService):
        self._availabilityService = availabilityService
        self._authService = authService

    # Return the signed-in user's saved slots
    def handleGetSchedule(self, request: dict) -> Response:
        return respond(lambda: self._getSchedule(request))

    def _getSchedule(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        schedule = self._availabilityService.getUserAvailability(session.userId)
        slots = schedule.retrieveAvailabilitySchedule()
        return {
            "slots": [
                {"startTime": s.startTime, "endTime": s.endTime, "cadence": s.cadence}
                for s in slots
            ]
        }
    # Replace the signed-in user's slots with the list in the request
    def handleUpdateSchedule(self, request: dict) -> Response:
        return respond(lambda: self._updateSchedule(request))

    def _updateSchedule(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        rawSlots = request.get("slots")
        if not isinstance(rawSlots, list):
            raise ValueError("slots must be a list")
        # TimeSlot raises ValueError for a bad slot, which comes back as invalid
        slots = [TimeSlot(s["startTime"], s["endTime"], s["cadence"]) for s in rawSlots]
        # An empty list clears the schedule
        self._availabilityService.saveManualSchedule(session.userId, slots)
        # Replace the signed-in user's slots with the events in an uploaded .ics file
    def handleUploadIcs(self, request: dict) -> Response:
        return respond(lambda: self._uploadIcs(request))

    def _uploadIcs(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        fileName = request.get("fileName")
        fileBytes = request.get("fileBytes")
        if not isinstance(fileBytes, bytes):
            raise ValueError("fileBytes must be bytes")
        # The service checks the file and raises ValueError if it is not a valid calendar
        self._availabilityService.importIcsCalendar(session.userId, fileName, fileBytes)