"""Built-in data sources, used when Muse hasn't pushed today's briefing."""

from __future__ import annotations

import logging
from datetime import datetime

from ..config import Config
from ..model import Briefing
from .calendar import events_for_day
from .todos import read_todos
from .weather import fetch_weather

log = logging.getLogger(__name__)


def collect(cfg: Config, now: datetime | None = None) -> Briefing:
    """Gather everything configured. A failing source is logged and left out,
    so one dead calendar never blanks the whole screen."""
    now = now or datetime.now(cfg.tz)
    b = Briefing(day=now.date(), title=cfg.title, updated=now.strftime("%H:%M"))

    if cfg.calendars:
        try:
            b.events = events_for_day(cfg.calendars, now.date(), cfg.tz)[: cfg.max_events]
        except Exception:
            log.exception("calendar failed")
    if cfg.todos_file:
        try:
            b.todos = read_todos(cfg.todos_file)[: cfg.max_todos]
        except Exception:
            log.exception("to-dos failed")
    if cfg.latitude is not None and cfg.longitude is not None:
        try:
            b.weather = fetch_weather(cfg.latitude, cfg.longitude, cfg.timezone, cfg.units)
        except Exception:
            log.exception("weather failed")
    return b
