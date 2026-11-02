# Phase 4 — React and Leaflet interface

This phase records the original Delhi implementation. For the deployed worldwide default, provider choices, GPS/IP flow and updated verification, read the [worldwide release notes](worldwide.md).

Implemented: debounced keyboard autocomplete, click-to-set endpoints, swapping/clearing, browser geolocation, travel modes, algorithm selection, route polyline, markers, ETA/distance, instruction list, search metrics, loading/errors, coverage boundary, responsive layout, information dialog and a local road backdrop for offline demos.

Run `sh scripts/build_frontend.sh` from the root, then start `./build/navic-api` and open `http://127.0.0.1:8080`. For hot-reload development on a standard Node setup, run `pnpm run dev` inside frontend while the C++ API runs separately. Vite proxies API requests.

Check search with NSUT/Vegas Mall, select with arrow keys/Enter, compute, change to Walk, recalculate, switch the algorithm and inspect Under the hood. Switch Road map to Offline roads to render the bundled graph backdrop. Confirm the dotted rectangle and error messages keep the scope visible. Mobile CSS stacks the planner and map; desktop CSS shows them side by side.

Browser checks performed: autocomplete keyboard selection, actual driving route/steps, walking recalculation, offline road layer and 390 px narrow layout with no horizontal overflow. Desktop route and mobile offline screenshots are saved in docs/screenshots. Browser location permission is not automatically granted during QA; actual-device geolocation remains a manual acceptance check.

Viva note: React tracks state; Leaflet owns its map instance. Effects synchronize map layers to state and clean up resources. A request revision plus AbortController prevents old responses from replacing a newer route selection.

## Three-line revision
React controls application state; Leaflet displays tiles, markers and route geometry.
The API sends [longitude, latitude]; the map component converts to Leaflet's order.
Input changes invalidate the old route, and the offline demo uses local vectors instead of scraped tiles.
