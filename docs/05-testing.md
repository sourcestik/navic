# Phase 5 — integration, correctness and performance

## Test plan and recorded results
Run the native core checks, then pytest against isolated real C++ HTTP processes, then the frontend production build and browser checks. Algorithm fixtures are small and controlled; real-data tests use the delivered OSM snapshot. Inspect artifacts/pytest-results.xml, artifacts/benchmark.json, artifacts/resource-check.json and artifacts/local-smoke-test.json.

Recorded final local results: **16,529 native checks passed; 52 pytest tests and 6 browser-location unit tests passed; Vite production build passed.** Native checks include an independent Floyd–Warshall oracle, so the test suite does not merely compare two implementations that might share a bug. These counts describe assertions/test items, not coverage percentages.

| Input / scenario | Expected | Actual |
|---|---|---|
| Seeded random graphs, both algorithms | Oracle shortest cost/reachability | Pass: native oracle comparisons |
| Known expensive direct edge vs cheaper two-edge route | Choose cheaper total, reconstruct exact edges | Pass |
| Reverse traversal of one-way edge | Unreachable | Pass |
| Footpath with driving mode | Excluded; walking still permitted | Pass |
| Isolated nearest roads with shared nearby alternative | Snap within limit to compatible network | Pass |
| NSUT to Vegas, each of 3 modes | 200, valid geometry/steps, equal algorithm cost | Pass |
| Identical source/destination | Zero road distance/time; valid two-position line | Pass |
| Disconnected synthetic components | 404 NO_ROUTE | Pass |
| Point beyond 800 m from usable nodes | 422 SNAP_TOO_FAR | Pass |
| Outside the Delhi extract | Delegate to worldwide routing | Pass: Paris–Brussels, 311.9 km |
| New York–London driving | No road connection | Public HTTP 404 NO_ROUTE |
| Latitude 200, string/bool/null coordinates | 422 with structured error | Pass |
| Malformed JSON | 400 INVALID_JSON | Pass |
| Missing endpoint/object | 422 | Pass |
| Unknown mode/algorithm or wrong enum type | 422 | Pass |
| Wrong content type | 415 | Pass |
| Body over 16 KiB | 413 | Pass |
| Exact NSUT alias, unknown search | Campus result / empty result list | Pass |
| Reverse lookup at named feature | Approximate=true and near-zero distance | Pass |
| NaN/trailing query text/invalid limit | 400 | Pass |
| Allowed Origin and OPTIONS | CORS headers / 204 | Pass |
| Disallowed Origin | 403 with no allow-origin header | Pass |
| Exhausted two-token test limiter, forged X-Forwarded-For | 429 + Retry-After; header does not bypass limit | Pass |
| Cacheable repeated route | cached=true, zero new search work | Pass |
| OSM access, one-way exceptions, mph speed | Correct masks and speed conversion | Pass |
| Keyboard autocomplete, then route | Selected places retained and line/metrics shown | Browser verified |
| Switch Drive to Walk | Old result cleared, recalculation changes ETA | Browser verified: about 7 min to 36 min |
| Offline road layer | Route remains visible over local road vectors | Browser verified |
| 390 px viewport | Stacked layout; no horizontal overflow | Browser verified: content width=viewport width=390 px |
| Geolocation on an actual device | Permission handling and valid source | Not exercised with personal location |
| Render/Netlify public endpoint | HTTPS routes work from another device | All three modes passed over public HTTPS; a physical second-device test is separate. |
| Docker/Linux CI | Container build and platform tests pass | GitHub Actions passed; Render built and started the Docker image. |

## Worldwide mobile browser check
On the deployed site, a fresh Chrome context at 390 × 844 CSS pixels used simulated coordinates. GPS denial triggered the labeled IP origin and a pin. Retry GPS replaced both the input and marker with the simulated Paris origin; the page fit the viewport. Selecting a live Brussels autocomplete result produced a 308.3 km route with turn instructions. That result used a different destination pin from the fixed-coordinate 311.9 km API test. No personal GPS reading was collected.

## Responsive layout verification
Using the production frontend and a live local C++ route from NSUT to Vegas Mall, the browser was resized to 320×568, 390×844, 844×390, 768×1024, 1024×768, 1440×900 and 1920×1080 CSS pixels. At every size the document fit horizontally and both endpoint markers remained inside the map. At 390×844, “View map” focused the map and exposed its full 608 px height. “Plan route” returned focus to the route planner. These checks used browser viewport emulation. The mobile capture is in [navic-phone-map.jpg](screenshots/navic-phone-map.jpg).

## Performance interpretation
The benchmark records two real journeys, three modes and both algorithms. Read the JSON for exact current timings. Search time excludes snapping, HTTP, JSON construction and browser drawing. Whole-request time includes local network and response processing. Cached responses are labeled and excluded from fresh-search comparisons. The sample is one run per case, not a percentile-based load test.

Final graph-loading measurement on this Mac: **1.83 seconds wall time; 140,656,640 bytes maximum RSS (about 134.1 MiB)**. This includes streaming load, connectivity indexing and reading static assets; it does not include sustained concurrent HTTP load. It is below the documented 512 MB free Render allocation locally, but Linux/cloud behavior must be measured after deployment.

The largest cost for short trips can be the O(V) snapping scans, not the search. A spatial index is the most direct next optimization. For longer routes A* typically explores fewer nodes than Dijkstra; the report uses actual recorded examples rather than promising universal speedups.

## Reproduction
```sh
sh scripts/build.sh
.venv/bin/python -m pytest -q --junitxml=artifacts/pytest-results.xml
sh scripts/build_frontend.sh
./build/navic-api
```
Then, in another terminal:
```sh
python3 scripts/benchmark.py
python3 scripts/smoke_test.py http://127.0.0.1:8080 --output artifacts/local-smoke-test.json
```
Restart the API before a clean uncached benchmark. Do not compare a cache hit with an uncached algorithm run. The current OSM timestamp/counts must accompany results.

## Three-line revision
Test algorithms against an independent oracle, then test the real HTTP boundary and browser flow.
Separate search time, snapping/HTTP latency, cache hits and startup memory.
Local, Linux CI and public HTTPS checks passed. Personal-device GPS accuracy was not measured.
