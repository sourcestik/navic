# Worldwide navigation (version 2)

The [public app](https://navic-delhi.onrender.com/) and its [C++ API](https://navic-delhi.onrender.com/docs) run together on Render. The original project report and stored performance measurements describe version 1's Delhi routing graph.

* **Map:** Leaflet starts with a world overview and moves to the detected or chosen origin. It allows worldwide panning, zooming, and click selection. Online tiles require network access. The explicitly labeled bundled offline road layer covers Delhi only.
* **Location:** Opening the planner requests device location over HTTPS with high accuracy and a 10-second timeout. Denial, timeout or missing GPS triggers a browser-side FreeIPAPI request with a six-second timeout. The site labels an IP pin as approximate and provides Retry GPS. If both attempts fail, manual search and map clicks remain available. A pending result cannot replace a manually edited origin. Browser GPS permission can be changed in the browser's site settings.
* **Search:** GET /geocode?q=Paris,France returns Photon matches with geographic context, supplemented with local landmarks. It sends no country or bounding-box parameter. GET /reverse-geocode works worldwide. For a disconnected Delhi demo use scope=local on forward search. A provider failure can fall back to usable local matches.
* **Routes:** POST /route accepts WGS84 coordinates worldwide. Use algorithm=world for OSRM everywhere. Existing API callers using astar or dijkstra (default astar) retain local shortest-distance behavior inside the saved graph. Outside the extract the API calls OSRM and identifies the actual provider and algorithm in the response. The frontend defaults to world, and the sample journeys select local A*. OSRM uses separate driving, walking and cycling profiles. Estimated duration and basic directions come from the selected profile. A road border crossing can work when mapped and traversable; disconnected networks or a point more than 1 km from a routable segment can return NO_ROUTE. A service outage produces a retryable error, not a fabricated straight line.
* **Privacy:** Device geolocation is optional. The visitor's browser contacts FreeIPAPI for IP fallback, the map tile service for the visible area, and the Navic API for search and route requests. Navic forwards worldwide place searches to Photon and global route endpoints to the routing provider. It does not store a travel history.

## Configuring and running

The C++ API links libcurl for certificate-verified HTTPS. Debian builds require libcurl4-openssl-dev; the runtime needs libcurl4 and ca-certificates. The Dockerfile includes these. No provider key is required for the default small educational demo.

| Variable | Scope | Default |
|---|---|---|
| PHOTON_BASE_URL | Backend | https://photon.komoot.io |
| OSRM_BASE_URL | Backend | https://routing.openstreetmap.de |
| VITE_IP_LOCATION_URL | Frontend build | https://free.freeipapi.com/api/v1/json/ |

Use base URLs without trailing slashes for the backend. An alternate OSRM gateway must expose routed-car, routed-foot and routed-bike prefixes. IP responses must contain numeric latitude and longitude. GPS requires HTTPS or localhost.

[FOSSGIS](https://routing.openstreetmap.de/about.html) permits at most one routing request per second; the single service instance enforces that across visitors. Shared routing and [Photon search](https://github.com/komoot/photon) are best-effort demo services. [FreeIPAPI](https://freeipapi.com/) can rate-limit estimates. Larger audiences need dedicated providers or self-hosted instances and shared throttling if the API is scaled horizontally.

## Verification

Run sh scripts/build.sh, python -m pytest and node --test frontend/test/location.test.js. The HTTP suite uses local provider fixtures to test mode dispatch, longitude/latitude order, cross-border routing, reverse geocoding, disconnected networks and outages. The location tests use synthetic positions for GPS success, denial, timeout, unavailable responses and cancellation.

On 2 November 2026, Render served version 2.0.0 at https://navic-delhi.onrender.com (release 883c946). The public API returned a Paris–Brussels driving route of 311.9 km in an estimated 3 h 37 min and rejected New York–London with 404 NO_ROUTE. Berlin search, Tokyo reverse lookup, walking and cycling in Paris also passed. See [worldwide results](../artifacts/worldwide-smoke.json) and [Delhi regression results](../artifacts/public-smoke-test.json).
