"""Today's events from one or more ICS feeds (URL or file), recurrences expanded."""

from __future__ import annotations

import urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events

from ..model import Event

TIMEOUT_S = 20


def read_ics(source: str) -> bytes:
    if source.startswith(("http://", "https://", "webcal://")):
        url = "https://" + source[len("webcal://"):] if source.startswith("webcal://") else source
        req = urllib.request.Request(url, headers={"User-Agent": "muse-briefing"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return r.read()
    return Path(source).expanduser().read_bytes()


def events_for_day(sources: list[str], day: date, tz: ZoneInfo) -> list[Event]:
    found: list[tuple[datetime, Event]] = []
    seen: set[tuple[str, str]] = set()
    start = datetime.combine(day, time.min, tz)
    end = start + timedelta(days=1)
    for src in sources:
        cal = icalendar.Calendar.from_ical(read_ics(src))
        for comp in recurring_ical_events.of(cal).between(start, end):
            if str(comp.get("STATUS", "")).upper() == "CANCELLED":
                continue
            title = str(comp.get("SUMMARY", "")).strip() or "(no title)"
            dt = comp.decoded("DTSTART")
            if isinstance(dt, datetime):
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                dt = dt.astimezone(tz)
                # Multi-day timed events that began earlier show from midnight.
                key_time = max(dt, start)
                label = "" if dt < start else dt.strftime("%H:%M")
            else:  # all-day
                key_time = start - timedelta(seconds=1)
                label = ""
            key = (label, title)
            if key in seen:  # same event shared into two calendars
                continue
            seen.add(key)
            loc = str(comp.get("LOCATION", "")).strip()
            found.append((key_time, Event(time=label, title=title, location=loc)))
    found.sort(key=lambda p: p[0])
    return [e for _, e in found]
