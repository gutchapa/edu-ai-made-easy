"""A filled-in briefing for previews and tests; no network needed."""

from __future__ import annotations

from datetime import date

from .model import Briefing, Event, Weather


def sample(day: date | None = None) -> Briefing:
    return Briefing(
        day=day or date(2026, 10, 15),
        title="Good morning, Chapa family",
        events=[
            Event("", "Diwali holidays begin"),
            Event("07:45", "School run", "Greenwood Primary"),
            Event("09:30", "Dentist – Arjun", "Smile Clinic"),
            Event("13:00", "Lunch with Priya"),
            Event("16:30", "Swimming class"),
            Event("19:00", "Family movie night"),
        ],
        todos=[
            "Pay electricity bill",
            "Buy milk, bread and diyas",
            "Sign school permission slip",
            "Call grandma",
        ],
        weather=Weather(summary="Light rain", icon="rain", now=18, high=24, low=16, precip=70),
        note="Library books due back Friday",
        updated="07:00",
    )
