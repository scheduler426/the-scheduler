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

    # Return the values for keys, raising ValueError for the first one that is missing
    @staticmethod
    def _required(request: dict, *keys: str) -> list:
        for key in keys:
            if request.get(key) is None:
                raise ValueError(f"{key} is required")
        return [request[key] for key in keys]

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
        (rawSlots,) = self._required(request, "slots")
        if not isinstance(rawSlots, list):
            raise ValueError("slots must be a list")
        slots = []
        for s in rawSlots:
            if not isinstance(s, dict):
                raise ValueError("each slot must be an object")
            for key in ("startTime", "endTime", "cadence"):
                if s.get(key) is None:
                    raise ValueError(f"{key} is required")
            slots.append(TimeSlot(s["startTime"], s["endTime"], s["cadence"]))
        self._availabilityService.saveManualSchedule(session.userId, slots)
    def handleUploadIcs(self, request: dict) -> Response:
        return respond(lambda: self._uploadIcs(request))

    def _uploadIcs(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        fileName, fileBytes = self._required(request, "fileName", "fileBytes")
        if not isinstance(fileBytes, bytes):
            raise ValueError("fileBytes must be bytes")
        # The service checks the file and raises ValueError if it is not a valid calendar
        self._availabilityService.importIcsCalendar(session.userId, fileName, fileBytes)