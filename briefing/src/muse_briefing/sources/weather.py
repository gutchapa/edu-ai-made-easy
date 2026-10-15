"""Today's weather from Open-Meteo (free, no API key)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from ..model import Weather

URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_S = 20

# WMO weather interpretation codes -> (summary, icon)
WMO = {
    0: ("Clear", "sun"),
    1: ("Mostly clear", "sun"),
    2: ("Partly cloudy", "partly"),
    3: ("Overcast", "cloud"),
    45: ("Fog", "fog"),
    48: ("Freezing fog", "fog"),
    51: ("Light drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Heavy drizzle", "rain"),
    56: ("Freezing drizzle", "rain"),
    57: ("Freezing drizzle", "rain"),
    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"),
    67: ("Freezing rain", "rain"),
    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Rain showers", "rain"),
    81: ("Rain showers", "rain"),
    82: ("Violent showers", "rain"),
    85: ("Snow showers", "snow"),
    86: ("Snow showers", "snow"),
    95: ("Thunderstorm", "storm"),
    96: ("Thunderstorm, hail", "storm"),
    99: ("Thunderstorm, hail", "storm"),
}


def build_url(lat: float, lon: float, timezone: str, units: str) -> str:
    q = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "timezone": timezone,
        "current": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": "1",
        "temperature_unit": "fahrenheit" if units == "F" else "celsius",
    }
    return URL + "?" + urllib.parse.urlencode(q)


def parse(data: dict, units: str) -> Weather:
    daily = data["daily"]
    current = data.get("current", {})
    code = int(daily["weather_code"][0])
    summary, icon = WMO.get(code, ("Unknown", "cloud"))
    precip = daily.get("precipitation_probability_max", [None])[0]
    return Weather(
        summary=summary,
        icon=icon,
        now=current.get("temperature_2m"),
        high=daily["temperature_2m_max"][0],
        low=daily["temperature_2m_min"][0],
        precip=None if precip is None else int(precip),
        units=units,
    )


def fetch_weather(lat: float, lon: float, timezone: str, units: str = "C") -> Weather:
    req = urllib.request.Request(build_url(lat, lon, timezone, units),
                                 headers={"User-Agent": "muse-briefing"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return parse(json.load(r), units)
