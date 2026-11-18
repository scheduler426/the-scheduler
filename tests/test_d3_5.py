# Tests for D3-5: scheduling email text

from datetime import datetime

from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.time_slot import TimeSlot
from scheduler.domain.user import User
from scheduler.infrastructure.scheduling_email_template_factory import SchedulingEmailTemplateFactory


def makeMeeting():
    slot = TimeSlot(datetime(2026, 11, 2, 15, 0), datetime(2026, 11, 2, 16, 0), "weekly")
    return ScheduledMeeting(None, 1, "IT 426 weekly", [slot])


def makeUser():
    return User(1, "ada@ilstu.edu", "hash", "Ada", "Lovelace")


def test_meeting_notice_has_name_and_slot():
    text = SchedulingEmailTemplateFactory().buildMeetingNoticeEmail(makeMeeting())
    assert "IT 426 weekly" in text
    assert "2026-11-02 15:00:00" in text
    assert "2026-11-02 16:00:00" in text
    assert "weekly" in text


def test_conflict_notice_matches_example():
    text = SchedulingEmailTemplateFactory().buildConflictNoticeEmail(makeMeeting(), makeUser(), "Exam that day")
    assert text == 'Ada Lovelace reported a schedule conflict for "IT 426 weekly".\nReason: Exam that day'