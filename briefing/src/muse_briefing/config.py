"""briefing.toml loading. See briefing.example.toml for every key."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass
class Config:
    timezone: str = "UTC"
    title: str = "Good morning"
    # Weather (Open-Meteo, no key needed). No coordinates, no weather.
    latitude: float | None = None
    longitude: float | None = None
    units: str = "C"
    # Calendars: ICS URLs or file paths, e.g. Google's "secret address in iCal format".
    calendars: list[str] = field(default_factory=list)
    max_events: int = 7
    # To-dos: a text/Markdown file, one per line; "- [x]" lines are skipped.
    todos_file: str = ""
    max_todos: int = 5
    # Server
    host: str = "0.0.0.0"
    port: int = 8765
    push_token: str = ""  # required as "Authorization: Bearer ..." on POST when set
    cache_minutes: int = 15

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def load(path: str | os.PathLike[str] | None) -> Config:
    if not path:
        return Config()
    p = Path(path)
    with p.open("rb") as f:
        raw = tomllib.load(f)

    general = raw.get("general", {})
    weather = raw.get("weather", {})
    calendar = raw.get("calendar", {})
    todos = raw.get("todos", {})
    server = raw.get("server", {})

    todos_file = str(todos.get("file", ""))
    if todos_file and not Path(todos_file).is_absolute():
        todos_file = str((p.parent / todos_file).resolve())

    cfg = Config(
        timezone=general.get("timezone", "UTC"),
        title=general.get("title", "Good morning"),
        latitude=weather.get("latitude"),
        longitude=weather.get("longitude"),
        units=str(weather.get("units", "C")).upper()[:1],
        calendars=list(calendar.get("sources", [])),
        max_events=int(calendar.get("max_events", 7)),
        todos_file=todos_file,
        max_todos=int(todos.get("max", 5)),
        host=server.get("host", "0.0.0.0"),
        port=int(server.get("port", 8765)),
        push_token=os.environ.get("BRIEFING_PUSH_TOKEN", server.get("push_token", "")),
        cache_minutes=int(server.get("cache_minutes", 15)),
    )
    if cfg.units not in ("C", "F"):
        raise ValueError("weather.units must be C or F")
    cfg.tz  # fail early on a bad timezone name
    return cfg
