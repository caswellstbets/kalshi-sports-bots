"""Small shared helpers: HTTP with retries, time, JSON/JSONL files, normal distribution."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from statistics import NormalDist
from zoneinfo import ZoneInfo

import requests

ET = ZoneInfo("America/New_York")
_N = NormalDist()
_session = requests.Session()
# ESPN rejects user agents with "bot" in the name, so the requests default is kept
_session.headers.update({"Accept": "application/json"})
_last_call: dict[str, float] = {}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    # ESPN sends minutes-only timestamps like 2026-11-15T00:00Z
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_json(url: str, params: dict | None = None, *, min_gap: float = 0.0, tries: int = 5, timeout: int = 30):
    """GET a JSON document. Spaces calls to the same host by min_gap seconds and
    backs off on 429 / 5xx. Raises after the last try."""
    host = url.split("/")[2]
    err: Exception | None = None
    for attempt in range(tries):
        wait = _last_call.get(host, 0) + min_gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            r = _session.get(url, params=params, timeout=timeout)
            _last_call[host] = time.monotonic()
            if r.status_code == 429 or r.status_code >= 500:
                err = RuntimeError(f"{r.status_code} from {host}")
                time.sleep(1.5 * (attempt + 1))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"GET {url} -> {r.status_code}: {r.text[:200]}")
            return r.json()
        except (requests.ConnectionError, requests.Timeout, ValueError) as e:
            err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {tries} tries: {err}")


def norm_cdf(x: float) -> float:
    return _N.cdf(x)


def norm_inv(p: float) -> float:
    return _N.inv_cdf(min(max(p, 1e-4), 1 - 1e-4))


def read_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, separators=(",", ":"), sort_keys=True)
    os.replace(tmp, path)


def read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path: str, rows: list[dict]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")


def r4(x):
    return None if x is None else round(float(x), 4)
