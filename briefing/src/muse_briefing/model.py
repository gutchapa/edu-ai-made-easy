"""What a briefing holds, already formatted for display.

The same shape comes from the built-in sources or from Muse posting JSON to
the server, so the renderer never cares where the data came from.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass
class Event:
    time: str  # "09:30", or "" for all-day
    title: str
    location: str = ""


@dataclass
class Weather:
    summary: str  # "Partly cloudy"
    icon: str  # one of ICONS
    now: float | None = None
    high: float | None = None
    low: float | None = None
    precip: int | None = None  # chance of rain today, percent
    units: str = "C"


ICONS = ("sun", "partly", "cloud", "fog", "rain", "snow", "storm")


@dataclass
class Briefing:
    day: date
    title: str = "Good morning"
    events: list[Event] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    weather: Weather | None = None
    note: str = ""
    updated: str = ""  # "07:00"

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["day"] = self.day.isoformat()
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "Briefing":
        """Parse a posted briefing, raising ValueError on bad input."""
        if not isinstance(d, dict):
            raise ValueError("briefing must be a JSON object")
        try:
            day = date.fromisoformat(str(d["day"]))
        except (KeyError, ValueError) as e:
            raise ValueError("day must be an ISO date like 2026-10-15") from e

        events = []
        for e in _list(d, "events"):
            if isinstance(e, str):
                events.append(Event(time="", title=e))
            elif isinstance(e, dict) and e.get("title"):
                events.append(Event(time=str(e.get("time", "")), title=str(e["title"]),
                                    location=str(e.get("location", ""))))
            else:
                raise ValueError("each event needs a title")

        todos = [str(t) for t in _list(d, "todos")]

        weather = None
        w = d.get("weather")
        if w is not None:
            if not isinstance(w, dict) or not w.get("summary"):
                raise ValueError("weather needs a summary")
            icon = str(w.get("icon") or icon_for_summary(str(w["summary"])))
            if icon not in ICONS:
                raise ValueError(f"weather icon must be one of {', '.join(ICONS)}")
            weather = Weather(
                summary=str(w["summary"]), icon=icon,
                now=_num(w, "now"), high=_num(w, "high"), low=_num(w, "low"),
                precip=None if w.get("precip") is None else int(_num(w, "precip")),
                units=str(w.get("units", "C")),
            )

        return cls(day=day, title=str(d.get("title") or "Good morning"), events=events,
                   todos=todos, weather=weather, note=str(d.get("note", "")),
                   updated=str(d.get("updated", "")))


def icon_for_summary(summary: str) -> str:
    s = summary.lower()
    for words, icon in (
        (("thunder", "storm"), "storm"),
        (("snow", "sleet", "flurr"), "snow"),
        (("rain", "shower", "drizzle"), "rain"),
        (("fog", "mist", "haze"), "fog"),
        (("partly", "partial", "mostly sunny", "sun and cloud"), "partly"),
        (("cloud", "overcast"), "cloud"),
    ):
        if any(w in s for w in words):
            return icon
    return "sun"


def _list(d: dict[str, Any], key: str) -> list[Any]:
    v = d.get(key) or []
    if not isinstance(v, list):
        raise ValueError(f"{key} must be a list")
    return v


def _num(d: dict[str, Any], key: str) -> float | None:
    v = d.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError) as e:
        raise ValueError(f"weather.{key} must be a number") from e
