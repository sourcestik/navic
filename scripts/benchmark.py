#!/usr/bin/env python3
"""Record local or deployed HTTP latency separately from algorithm search time."""
import argparse
import json
import platform
import time
import urllib.parse
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark.json"))
    args = parser.parse_args()

    def call(path, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(args.base_url.rstrip("/") + path, data=payload,
            headers={"Content-Type": "application/json"} if payload else {})
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.load(response)

    source = call("/geocode?scope=local&q=NSUT")["results"][0]
    rows = []
    for query in ("Vegas", "India Gate"):
        destination = call("/geocode?scope=local&q=" + urllib.parse.quote(query))["results"][0]
        for mode in ("driving", "walking", "cycling"):
            for algorithm in ("dijkstra", "astar"):
                body = {"source": {k: source[k] for k in ("lat", "lon")},
                    "destination": {k: destination[k] for k in ("lat", "lon")}, "mode": mode, "algorithm": algorithm}
                start = time.perf_counter()
                route = call("/route", body)
                rows.append({"journey": f'NSUT to {destination["name"]}', "mode": mode, "algorithm": algorithm,
                    "http_ms": (time.perf_counter() - start) * 1000, **{k: route[k] for k in
                        ("distance_m", "duration_s", "visited_nodes", "search_ms", "cached")}, "snap_gaps_m": [route["snapped"][k]["distance_m"] for k in ("source", "destination")]})
    record = {"base_url": args.base_url, "client_machine": platform.platform(), "health": call("/health"),
        "notes": "One request per case; observational measurements, not a load test. Cache hits are labeled and must not be compared as fresh searches.", "results": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
