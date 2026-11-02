# Phase 3 — C++ API and routing engine

Implemented: directed adjacency-list graph, Dijkstra/A*, haversine, mode permissions, component-aware snapping, parent-edge reconstruction, distance/ETA/maneuvers, local geocoder/reverse lookup, graph cache, bounded response cache, CORS, token-bucket rate limiting, logs, errors and OpenAPI endpoints. Python prepares data and runs integration tests; C++ serves all API endpoints.

Run and verify from the project root:
```sh
python3 scripts/unpack_data.py
sh scripts/build.sh
./build/navic-api
```
In another terminal, `curl -s http://127.0.0.1:8080/health` confirms graph readiness. Set up pytest with `python3 -m venv .venv` and `.venv/bin/python -m pip install -r requirements.txt`, then run `.venv/bin/python -m pytest -q`.

The loaded graph stays immutable. Four workers share it, while each search has its own arrays. The route cache retains at most 64 entries; responses above 64 KiB serialized are not cached. JSON allocation overhead is additional. The graph's data version changes only through an intentional data rebuild and restart.

Snapping first looks for nearby endpoints on a shared weak component. It does not add invented connections through buildings or gates. Each gap must remain within 800 m and is exposed in the result. The algorithm still returns NO_ROUTE when a directed path does not exist. All returned distance/time metrics describe the snapped road path.

Viva note: the priority queue is a min-heap via a reversed comparator. Lazy stale entries are skipped. The route is optimal for the represented graph/objective, not automatically for every real-world legal road restriction.

## Three-line revision
C++ owns the deployed API and custom routing algorithms; Python is offline/test tooling.
Validate and snap first, search permitted directed edges, then reconstruct exact edge IDs.
Use immutable graph data, bounded shared state and meaningful HTTP errors.
