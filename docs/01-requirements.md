# Phase 1 — problem and scope

This phase records the original Delhi implementation. For the deployed worldwide default, provider choices, GPS/IP flow and updated verification, read the [worldwide release notes](worldwide.md).

## Problem statement
Build Navic, an educational map navigator for a Delhi NCR pilot area. A user selects two places, chooses driving, walking or cycling, and receives a shortest-distance road route, estimated travel time and basic maneuver instructions. Expose the same functionality through a documented, publicly deployed C++ HTTP API.

## Objectives
1. Implement and explain Dijkstra and A* from scratch in C++.
2. Convert real OpenStreetMap data into a directed, weighted, mode-aware graph.
3. Separate map display, place search and route computation.
4. Test correctness, invalid input and resource use with reproducible evidence.
5. Deliver source, deployment configuration, report and a viva learning pack.

## One-page requirements
| ID | Requirement | Acceptance criterion |
|---|---|---|
| F01 | Search places | Local index returns ranked names and WGS84 coordinates; UI offers autocomplete |
| F02 | Set endpoints | Search, map click and browser geolocation work; endpoint labels remain consistent |
| F03 | Route | API returns GeoJSON LineString, road distance, ETA and maneuver list |
| F04 | Algorithms | Both algorithms return the same optimal distance on reachable test graphs |
| F05 | Modes | Driving respects supported one-way/access rules; walking/cycling use distinct permissions |
| F06 | Coverage | Visible boundary; coordinates outside it return a descriptive 422 error |
| F07 | Edge cases | Same snapped node, disconnected components and excessive snapping are handled |
| F08 | Explainability | UI exposes visited nodes and search timing; report explains heuristic |
| N01 | Public API | HTTPS /health and /route succeed from the actual deployed URL |
| N02 | Reliability | Validated JSON, bounded body size, CORS allowlist, bounded rate limiting and logs |
| N03 | Cost | No paid API key or paid hosting plan; check provider limits before deployment |
| N04 | Usability | Responsive layout, accessible labels, keyboard search, loading and error states |
| N05 | Reproducibility | Pinned libraries, persisted graph, automated tests and full setup commands |
| N06 | Offline demo | Local API and bundled road geometry work without internet; no tile scraping |

## Must-have and optional features
All F01–F08 and N01–N06 are must-have. Alternative routes and comparison with OSRM are optional extensions. Live traffic, public transport, spoken navigation, continuous GPS tracking and lane guidance are out of scope.

## Coverage and assumptions
Initial graph: 28.50–28.70° N, 76.98–77.25° E, covering Dwarka and parts of west/central Delhi. This is a Delhi NCR pilot, **not all of Delhi NCR**. A configurable data-preparation command permits expansion after measuring RAM. Roads at the boundary are clipped; a route that requires leaving the box may be unreachable or suboptimal relative to the full road network.

The frontend is React + Leaflet. Backend is C++17 + cpp-httplib + nlohmann/json. Python is used only for reproducible data preparation and test automation, not for the deployed routing API. Native adjacency lists replace NetworkX; direct Overpass ingestion replaces OSMnx, making the graph-building logic explicit and keeping heavy Python GIS dependencies off the server.

## Honest limitations
Distance is the optimization objective; ETA uses fixed mode/road speeds and does not include traffic, signal waiting or elevation. Turn instructions are derived from geometry, not a professional guidance engine. OSM turn-restriction relations, conditional restrictions, barrier nodes, lane restrictions and full regional access defaults are not modeled. Local search is a limited gazetteer, not a complete address geocoder. Do not present this academic prototype as a safety-critical navigation product.

## Run/test and viva note
Review this requirements table against the UI, API tests and deployment checklist at the end. No software is needed to validate this phase. Explain that a map tile is an image; a routing graph is a data structure and can work without map tiles.

## Three-line revision
Navic computes shortest-distance routes on a real, bounded OSM road graph.
C++ implements the API and algorithms; React/Leaflet presents the results.
Public deployment, verified tests and clearly stated coverage are acceptance requirements.
