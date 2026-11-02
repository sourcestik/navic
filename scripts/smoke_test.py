#!/usr/bin/env python3
"""Check a supplied live URL; never treat a generated configuration as a deployment."""
import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("base_url")
parser.add_argument("--output", type=Path, default=Path("artifacts/smoke-test.json"))
args = parser.parse_args()
base = args.base_url.rstrip("/")
parsed = urllib.parse.urlparse(base)
if parsed.scheme not in {"http", "https"} or not parsed.netloc:
    parser.error("Supply an actual HTTP(S) API base URL")


def call(path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(base + path, data=payload,
        headers={"Content-Type": "application/json"} if payload else {})
    with urllib.request.urlopen(request, timeout=120) as response:
        assert response.status == 200
        return json.load(response)


health = call("/health")
assert health["status"] == "ok"
source = call("/geocode?q=NSUT")["results"][0]
destination = call("/geocode?q=Vegas")["results"][0]
results = []
for mode in ("driving", "walking", "cycling"):
    body = {"source": {k: source[k] for k in ("lat", "lon")}, "destination": {k: destination[k] for k in ("lat", "lon")}, "mode": mode, "algorithm": "astar"}
    start = time.perf_counter()
    route = call("/route", body)
    assert route["geometry"]["type"] == "LineString" and route["distance_m"] > 0
    results.append({"mode": mode, "distance_m": route["distance_m"], "duration_s": route["duration_s"], "request_ms": (time.perf_counter() - start) * 1000})
record = {"base_url": base, "public_https_candidate": parsed.scheme == "https" and parsed.hostname not in {"localhost", "127.0.0.1"},
          "health": health, "route_checks": results}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
