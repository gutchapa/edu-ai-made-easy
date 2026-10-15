from datetime import date

import pytest

from muse_briefing.model import Briefing, icon_for_summary
from muse_briefing.sample import sample


def test_round_trip():
    b = sample()
    assert Briefing.from_json(b.to_json()) == b


def test_minimal_and_loose_input():
    b = Briefing.from_json({
        "day": "2026-10-15",
        "events": ["Bins out", {"time": "09:00", "title": "Standup"}],
        "todos": ["Milk"],
        "weather": {"summary": "Heavy rain showers", "high": "21", "precip": 80.0},
    })
    assert b.day == date(2026, 10, 15)
    assert b.events[0].time == "" and b.events[1].title == "Standup"
    assert b.weather.icon == "rain" and b.weather.high == 21 and b.weather.precip == 80


@pytest.mark.parametrize("bad", [
    [],
    {},
    {"day": "tomorrow"},
    {"day": "2026-10-15", "events": "x"},
    {"day": "2026-10-15", "events": [{"time": "9"}]},
    {"day": "2026-10-15", "weather": {"high": 3}},
    {"day": "2026-10-15", "weather": {"summary": "x", "icon": "tornado"}},
    {"day": "2026-10-15", "weather": {"summary": "x", "high": "warm"}},
])
def test_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        Briefing.from_json(bad)


@pytest.mark.parametrize("summary,icon", [
    ("Sunny", "sun"), ("Partly cloudy", "partly"), ("Overcast", "cloud"),
    ("Light drizzle", "rain"), ("Snow flurries", "snow"), ("Thunderstorms", "storm"), ("Mist", "fog"),
])
def test_icon_for_summary(summary, icon):
    assert icon_for_summary(summary) == icon
