from datetime import date, datetime
from zoneinfo import ZoneInfo

from muse_briefing.config import Config
from muse_briefing.sources import collect
from muse_briefing.sources.calendar import events_for_day
from muse_briefing.sources.todos import read_todos
from muse_briefing.sources.weather import build_url, parse

TZ = ZoneInfo("Asia/Kolkata")

ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:1
DTSTART:20261001T033000Z
DTEND:20261001T040000Z
RRULE:FREQ=WEEKLY;BYDAY=TH
SUMMARY:Swimming
LOCATION:Club pool
END:VEVENT
BEGIN:VEVENT
UID:2
DTSTART;VALUE=DATE:20261015
DTEND;VALUE=DATE:20261016
SUMMARY:Diwali holidays
END:VEVENT
BEGIN:VEVENT
UID:3
DTSTART;TZID=Asia/Kolkata:20261015T080000
DTEND;TZID=Asia/Kolkata:20261015T083000
SUMMARY:Cancelled thing
STATUS:CANCELLED
END:VEVENT
BEGIN:VEVENT
UID:4
DTSTART;TZID=Asia/Kolkata:20261015T070000
DTEND;TZID=Asia/Kolkata:20261015T073000
SUMMARY:School run
END:VEVENT
BEGIN:VEVENT
UID:5
DTSTART;TZID=Asia/Kolkata:20261016T070000
SUMMARY:Tomorrow
END:VEVENT
END:VCALENDAR
"""


def test_calendar_expands_sorts_and_filters(tmp_path):
    f = tmp_path / "family.ics"
    f.write_text(ICS)
    events = events_for_day([str(f), str(f)], date(2026, 10, 15), TZ)  # same feed twice: deduped
    assert [(e.time, e.title) for e in events] == [
        ("", "Diwali holidays"),
        ("07:00", "School run"),
        ("09:00", "Swimming"),  # 03:30 UTC weekly, shown in local time
    ]
    assert events[2].location == "Club pool"


def test_todos(tmp_path):
    f = tmp_path / "todo.md"
    f.write_text("# House\n- [ ] Pay bill\n- [x] Done thing\n* Milk\n\n2. Call grandma\nplain line\n")
    assert read_todos(str(f)) == ["Pay bill", "Milk", "Call grandma", "plain line"]


def test_weather_parse_and_url():
    w = parse({
        "current": {"temperature_2m": 18.4},
        "daily": {"weather_code": [61], "temperature_2m_max": [24.1], "temperature_2m_min": [16.0],
                  "precipitation_probability_max": [70]},
    }, "C")
    assert (w.summary, w.icon, w.now, w.high, w.low, w.precip) == ("Light rain", "rain", 18.4, 24.1, 16.0, 70)
    assert "temperature_unit=fahrenheit" in build_url(1, 2, "UTC", "F")


def test_collect_survives_a_broken_source(tmp_path):
    todo = tmp_path / "t.txt"
    todo.write_text("Milk\n")
    cfg = Config(timezone="Asia/Kolkata", calendars=[str(tmp_path / "missing.ics")], todos_file=str(todo))
    b = collect(cfg, now=datetime(2026, 10, 15, 7, 0, tzinfo=TZ))
    assert b.events == [] and b.todos == ["Milk"] and b.updated == "07:00"
