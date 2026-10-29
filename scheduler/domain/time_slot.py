from __future__ import annotations

from datetime import datetime, timedelta


class TimeSlot:
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    _PERIODS = {DAILY: timedelta(days=1), WEEKLY: timedelta(weeks=1)}
    _REFERENCE = datetime(2000, 1, 3)

    def __init__(self, startTime: datetime, endTime: datetime, cadence: str = ONCE):
        if endTime <= startTime:
            raise ValueError("endTime must be after startTime")
        if cadence != self.ONCE and cadence not in self._PERIODS:
            raise ValueError(f"Unsupported cadence: {cadence}")
        if cadence in self._PERIODS and endTime - startTime > self._PERIODS[cadence]:
            raise ValueError("A recurring slot cannot be longer than its cadence period")
        self.startTime = startTime
        self.endTime = endTime
        self._cadence = cadence

    @property
    def cadence(self) -> str:
        return self._cadence

    def getDuration(self) -> int:
        return int((self.endTime - self.startTime).total_seconds())

    def overlaps(self, other: TimeSlot) -> bool:
        if self._isRecurring() and other._isRecurring():
            return self._patternsOverlap(other)
        if self._isRecurring():
            return other.overlaps(self)
        return any(
            self._intervalOverlaps(occurrence)
            for occurrence in other._occurrencesWithin(self.startTime, self.endTime)
        )

    def occursAt(self, dateTime: datetime) -> bool:
        return any(
            occurrence.startTime <= dateTime < occurrence.endTime
            for occurrence in self._occurrencesWithin(dateTime, dateTime)
        )

    def covers(self, other: TimeSlot) -> bool:
        return any(
            occurrence.startTime <= other.startTime and other.endTime <= occurrence.endTime
            for occurrence in self._occurrencesWithin(other.startTime, other.endTime)
        )

    def _isRecurring(self) -> bool:
        return self._cadence != self.ONCE

    def _occurrencesWithin(self, rangeStart: datetime, rangeEnd: datetime) -> list[TimeSlot]:
        if not self._isRecurring():
            return [self]
        if rangeEnd < self.startTime:
            return []
        period = self._PERIODS[self._cadence]
        duration = self.endTime - self.startTime
        skipped = max(0, (rangeStart - duration - self.startTime) // period)
        current = self.startTime + period * skipped
        occurrences = []
        while current <= rangeEnd:
            occurrences.append(TimeSlot(current, current + duration))
            current += period
        return occurrences

    def _intervalOverlaps(self, other: TimeSlot) -> bool:
        return self.startTime < other.endTime and other.startTime < self.endTime

    def _patternsOverlap(self, other: TimeSlot) -> bool:
        bothWeekly = self._cadence == other._cadence == self.WEEKLY
        period = self._PERIODS[self.WEEKLY if bothWeekly else self.DAILY]
        selfOffset = (self.startTime - self._REFERENCE) % period
        otherOffset = (other.startTime - self._REFERENCE) % period
        selfLength = self.endTime - self.startTime
        otherLength = other.endTime - other.startTime
        return any(
            selfOffset < otherOffset + shift + otherLength and otherOffset + shift < selfOffset + selfLength
            for shift in (-period, timedelta(0), period)
        )
