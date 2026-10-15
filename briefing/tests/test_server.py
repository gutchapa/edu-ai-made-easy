import json
import threading
import urllib.error
import urllib.request
from datetime import date, datetime
from http.server import ThreadingHTTPServer
from zoneinfo import ZoneInfo

import pytest

from muse_briefing.config import Config
from muse_briefing.model import Briefing
from muse_briefing.render import HEIGHT, WIDTH
from muse_briefing.server import State, make_handler

TZ = ZoneInfo("UTC")
TODAY = datetime(2026, 10, 15, 7, 0, tzinfo=TZ)


@pytest.fixture
def server():
    calls = []

    def collector(cfg):
        calls.append(1)
        return Briefing(day=TODAY.date(), todos=["from sources"])

    cfg = Config(timezone="UTC", push_token="s3cret", port=0)
    state = State(cfg, collector=collector, clock=lambda: TODAY)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", state, calls
    httpd.shutdown()
    httpd.server_close()


def req(url, method="GET", body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def test_device_gets_raw_rgb565_and_cache_is_used(server):
    base, _, calls = server
    status, headers, body = req(base + "/briefing.rgb565")
    assert status == 200 and len(body) == WIDTH * HEIGHT * 2
    assert headers["Content-Type"] == "application/octet-stream"
    req(base + "/briefing.png")
    assert len(calls) == 1
    req(base + "/briefing.png?refresh=1")
    assert len(calls) == 2


def test_push_needs_token_and_valid_json(server):
    base, _, _ = server
    body = {"day": "2026-10-15", "todos": ["pushed"]}
    assert req(base + "/briefing", "POST", body)[0] == 401
    assert req(base + "/briefing", "POST", body, token="wrong")[0] == 401
    assert req(base + "/briefing", "POST", {"day": "nope"}, token="s3cret")[0] == 400

    status, _, out = req(base + "/briefing", "POST", body, token="s3cret")
    assert status == 200
    assert json.loads(out)["draw_url"].endswith("/briefing.rgb565")
    data = json.loads(req(base + "/briefing.json")[2])
    assert data["source"] == "pushed" and data["briefing"]["todos"] == ["pushed"]

    assert req(base + "/briefing", "DELETE", token="s3cret")[0] == 200
    data = json.loads(req(base + "/briefing.json")[2])
    assert data["source"] == "sources"


def test_stale_push_is_ignored(server):
    base, state, _ = server
    state.push(Briefing(day=date(2026, 10, 14), todos=["yesterday"]))
    data = json.loads(req(base + "/briefing.json")[2])
    assert data["briefing"]["todos"] == ["from sources"]


def test_index_and_404(server):
    base, _, _ = server
    status, _, body = req(base + "/")
    assert status == 200 and b"/briefing.rgb565" in body
    assert req(base + "/nope")[0] == 404
