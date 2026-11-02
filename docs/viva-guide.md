# Navic: understanding and defending the project

Read this with the source open. Do not memorize an explanation that you cannot demonstrate. Deployment is a separate acceptance item: only say “publicly deployed” after the live smoke test has passed.

## 1. Two-minute walkthrough
“My project is Navic, a worldwide road planner with a custom routing engine for the Delhi pilot. A user searches for a source and destination, selects driving, walking or cycling, and gets a road route, distance, estimated travel time and basic turn instructions.

“The frontend uses React for user-interface state and Leaflet for the map. The backend is a C++17 HTTP API. I implemented Dijkstra and A* from scratch using adjacency lists and a minimum-priority queue. OpenStreetMap provides the road data. A Python preparation script converts a downloaded extract into a directed, weighted graph; Python is not the production API language.

“In the local engine, when a request arrives, the API validates coordinates, checks coverage and snaps the selected points to nearby usable road nodes. It prefers nodes on a shared weakly connected component so an isolated parking loop does not defeat an otherwise reasonable route. The final algorithm still checks directed reachability. Dijkstra expands according to distance already traveled. A* adds a straight-line geographic estimate to the destination. Both optimize distance and should return the same minimum cost.

“The result is a GeoJSON line. ETA is the sum of segment travel times using fixed speeds, not live traffic. The API also supports local place search, approximate reverse geocoding, health checks and Swagger documentation. Tests cover algorithms, permissions, HTTP validation, CORS and rate limiting.

“The local engine’s limitations are bounded coverage, incomplete OSM restrictions, nearest-node snapping and approximate guidance. I distinguish the educational algorithm from a production navigation engine.”

“The worldwide mode delegates to OSRM; I did not implement its engine. Photon supplies global search. We verified Paris to Brussels on the public API. GPS estimates can be replaced manually; IP fallback is visibly marked as approximate.”

## 2. Five-minute walkthrough
**Minute 1 — problem and scope.** Start with the college brief: a map navigator plus a publicly deployed API. Demonstrate a source and destination. Explain the chosen area, three modes and distinction between distance optimization and time estimation. The graph is a static snapshot, not live traffic. OSM data is open under ODbL; a free public tile server has a usage policy.

**Minute 2 — data and representation.** OSM nodes give coordinates. OSM ways list node IDs and tags such as highway, name, access and oneway. Relations can describe a university boundary or a turn restriction. The importer includes named relations in the gazetteer, but does not implement turn-restriction relations. Consecutive way nodes become edges. Two directions may have different mode bits. Each edge stores distance, three time estimates and a road-name index. The compressed snapshot is unpacked before running the API; records are loaded incrementally to control memory.

**Minute 3 — algorithm.** Trace a small graph with S→A=2, S→B=5, A→B=1 and B→T=3. Dijkstra discovers B at 5 but improves it to 3 through A; T then has cost 6. The priority queue may retain the old entry for B, so the stale-entry check skips it. A* changes queue priority from g to g+h. Haversine gives a great-circle distance in meters. Every edge is at least its endpoint haversine distance; triangle inequality therefore makes the heuristic consistent. Stop when the destination is removed with its current best distance, then follow parent edge IDs backwards.

**Minute 4 — API and UI.** Show /health, /openapi.json and /docs. Send a POST /route request. Point out type checks, finite values, coverage, modes and errors. React holds endpoints, mode, algorithm, loading and route state. A debounced search calls the worldwide geocoder, supplemented by the local index; stale requests are aborted. Leaflet draws geometry, while route metrics and instructions are normal React elements. Explain coordinate ordering: JSON endpoint objects are explicit lat/lon; GeoJSON positions are lon/lat.

**Minute 5 — verification, deployment and limits.** Show the independent algorithm oracle, API tests and recorded benchmark. Distinguish search timing from whole-request timing, and local timing from free-host timing. Docker separates frontend build, C++ compilation and the smaller runtime. Render supplies the public port and TLS; Netlify can serve the frontend separately with an environment-configured API URL. The graph is inside the image, so an ephemeral filesystem restart does not require fetching OSM again. Demonstrate the local offline road backdrop. Finish with two concrete future improvements: edge-based turn restrictions and a spatial index for faster snapping.

## 3. Important source blocks: what, why, and what fails without them

### backend/include/navic/graph.hpp
| Block | What it does | Why / failure if removed |
|---|---|---|
| Point and radians | Store latitude/longitude and convert degrees to radians | C++ trigonometric functions expect radians; using degrees gives incorrect distances |
| haversine | Computes spherical distance with a clamped intermediate value | Great-circle units match edge weights; clamping prevents round-off from making asin invalid |
| bearing | Computes an initial heading from one coordinate to the next | Signed heading changes drive approximate turn text |
| Mode and mode_bit | Map driving/walking/cycling to bit values 1/2/4 | An edge can support multiple modes without three graph copies |
| Node | Stores OSM ID, coordinate, outgoing edge IDs and mode masks | Adjacency traversal becomes O(out-degree), rather than scanning every edge |
| Edge | Stores endpoints, length, per-mode seconds, name index and permissions | Parent edge IDs preserve the correct parallel edge and its attributes |
| Path and Snap | Return search results and snapping results as explicit values | Distinguish no route from a valid zero-length route |
| add_edge | Validates edge indices, costs and modes; appends adjacency; enforces distance lower bound | Bad graph records could cause out-of-range access or invalidate A* correctness |
| load | Parses one header, N nodes and E edges, then indexes components | Full-document parsing creates large temporary memory; truncation must fail startup clearly |
| index_components | Uses disjoint-set union with path compression and rank for each mode | Reveals isolated networks cheaply; weak components alone do not prove directed reachability |
| contains | Checks the rectangular coverage boundary | A coordinate outside the data area must not silently snap to a remote edge |
| nearest | Scans eligible nodes for minimum haversine distance | Mode-specific source needs an outgoing edge; destination needs an incoming edge |
| snap_pair | Finds nearest candidates per weak component and minimizes combined snapping gaps across shared components | Campus centroids can sit near disconnected internal roads; the chosen pair can differ from independently nearest nodes |
| shortest_path initialization | Allocates best costs and parent edge IDs, sets source cost to zero | “Unknown” must be infinity; zero would suppress every positive relaxation |
| compare and priority_queue | Inverts C++'s default max-heap ordering | Without inversion, expensive candidates would be expanded first |
| heuristic | Returns haversine for A*, zero for Dijkstra | Same core search and objective make comparison meaningful |
| stale-entry check | Ignores an older, worse queued distance | Duplicate queue entries are intentional; processing old costs wastes work and can confuse metrics |
| relaxation | Replaces an edge target's best known cost when a cheaper path is found | This is the central shortest-path update: candidate=g(u)+w(u,v) |
| destination check | Stops after the target's current best entry is popped | Stopping when the target is first discovered can return a nonoptimal path |
| reconstruction | Follows parent edges backward, sums times, then reverses the list | Without reversal, geometry would run destination to source |
| describe | Builds GeoJSON and groups instructions by name/heading | The graph answer must become a usable API response; road curves can produce imperfect guidance |
| two-point zero route | Duplicates a coordinate for a stationary route | GeoJSON LineString requires at least two positions |

Trace the fixture before discussing the 300,000-node graph. The algorithm is exactly the same; only the input size changes.

### backend/src/main.cpp
| Block | What and why | Failure if absent |
|---|---|---|
| ApiError | Carries HTTP status and machine-readable error code | Input errors become generic 500s or inconsistent strings |
| env | Reads configuration with explicit defaults | Deployment port/origins would be hard-coded |
| send/error | Centralizes JSON serialization and content type | Clients cannot reliably parse responses |
| lower | ASCII case folding using unsigned char | Passing negative signed chars to tolower is undefined; this still is not full Unicode normalization |
| number/point/query_number | Reject wrong types, nonfinite values, invalid ranges and trailing query junk | A string or NaN could enter geographic math |
| parse_mode/string_field | Enforces enum/string contracts | Unsupported modes could select the wrong cost/mask |
| read_file | Fails clearly if the checked-in artifacts are absent | A half-configured server must not claim readiness |
| RouteCache | Mutex-protected FIFO of at most 64 route responses | An unbounded cache leaks memory; races corrupt shared state |
| RateLimiter | Token bucket per socket peer, 180/minute default, bounded identity count | An anonymous API otherwise accepts unlimited CPU work |
| immutable graph | Loaded once and shared by four workers | Loading per request adds seconds and large transient memory |
| request limits | 16 KiB body, timeouts, bounded worker queue | Oversized/slow requests can consume all memory or workers |
| pre-routing hook | Applies origin policy, preflight and endpoint limits | Browser access and expensive calls become uncontrolled |
| post-routing hook | Adds allowed-origin, Vary and basic security headers | Caches/browsers can interpret responses incorrectly |
| logger | Records method, path and status only | No diagnostic trail; logging bodies instead would disclose user coordinates |
| exception/error handlers | Convert failures to stable JSON without exposing internals | A bad request can produce HTML errors or crash handling |
| /health | Reports readiness after loading all necessary data | A service can appear alive but be unable to route |
| /coverage | Exposes bounds, modes, provenance and snapping strategy | Frontend and backend could disagree about supported territory |
| /geocode | Ranks exact/prefix/substring/alias matches, suppresses repeated names | Search becomes nondeterministic or floods with many segments of the same road |
| /reverse-geocode | Scans named places for the closest coordinate | It is a nearest-place lookup, not exact address reconstruction |
| /route validation | Checks content type, JSON, endpoints, coverage and enums | Later algorithm code would have to defend every malformed input |
| /route cache key | Uses snapped node IDs, mode and algorithm | Raw coordinates would create redundant entries; omitting mode would return wrong permissions |
| /route warnings | Reports snapping gaps and model limitations | Distance/ETA would be easy to misrepresent as a complete doorstep journey |
| /network | Serves local road geometry | Offline demonstration would depend on cached third-party tiles |
| /docs and /openapi.json | Human UI plus machine contract | API deployment is much harder to inspect during viva |
| static mount | Serves the built frontend from the C++ app locally or on Render | Separate frontend hosting is optional for the local demo |
| listen | Binds HOST/PORT and blocks while serving | Binding only localhost inside a cloud container makes it inaccessible externally |

The worker model is synchronous per request. Multiple requests run on a bounded pool of threads. The frontend uses asynchronous fetch; that does not make the C++ routing function asynchronous.

### Worldwide routing and origin detection
In backend/include/navic/world.hpp, get bounds the HTTPS time and response size; encode escapes search text; places converts Photon GeoJSON into suggestions; route chooses the travel profile and converts OSRM geometry and maneuvers. Without profile selection, a walking trip could silently receive driving directions. NO_ROUTE means no connected path was returned, whereas PROVIDER_UNAVAILABLE means the service could not answer.
In frontend/src/location.js, locateOrigin tries GPS first, then ipEstimate asks from the visitor’s browser. Asking from Render would estimate the server’s location. Manual selection cancels pending updates so a late IP estimate cannot move a pin the user already placed.

### scripts/prepare_data.py
`make_query` selects roads and named node/way/relation features inside a bbox. A cached extract can be rebuilt without new network requests. `permissions` applies general access, then more specific mode tags, then direction rules. It rejects non-road features, construction and area=yes polygons. `speeds` uses conservative defaults, recognizes simple maxspeed values and converts mph. These are estimates, not observed travel speeds.

`build` keeps the richest duplicate element, clips coordinates to the bbox, and gives sparse OSM IDs compact integer indices. `node_index` deduplicates shared road nodes: without it, intersecting ways would appear disconnected. `add_place` builds a name/alias index from OSM features; the explicit NSUT alias requires a university/institute name, preventing unrelated Netaji Subhash landmarks from matching it. Area centers are search coordinates, not guaranteed entrances.

Every consecutive node pair in a permitted way becomes up to two directed edges. All intermediate road geometry is retained; no OSMnx simplification is applied. Haversine lengths are unrounded floats so precision is preserved. Names are interned in one array. The writer emits a header and individual NDJSON records, plus deterministic gzip and a SHA-256 checksum. A road GeoJSON file supplies the offline backdrop. Metadata records the actual OSM timestamp and graph counts. Missing data or an Overpass partial-result remark fails the build.

### frontend/src/main.jsx
`App` owns the source, destination, mode, algorithm, route and status. `initialize` loads readiness, with cancellation. `invalidate` increments a request revision, aborts current work and clears stale route information whenever route inputs change. Without that, the UI could show a driving result after switching to walking.

`pick` assigns a clicked position to the selected endpoint. `compute` sends a JSON POST and only accepts the result if the request still corresponds to current inputs. `useLocation` delegates location permission to the browser and falls back to IP if GPS fails. `example` searches the real index rather than inserting invented results. The form, metric panel, direction list and information dialog are different presentations of the same state. React escapes strings by default; OSM names are not injected as HTML.

### frontend/src/SearchBox.jsx
The component stores the editable query separately from the selected place. `useId` links labels and accessibility attributes. A 500 ms timer reduces request frequency; an AbortController cancels superseded searches. Outside-click handling closes suggestions. Arrow keys and Enter select a result; Escape closes the menu. An editing ref prevents a parent selection reset from erasing the user's first replacement keystroke. Empty search results are shown honestly instead of inventing addresses.

### frontend/src/MapView.jsx
A ref holds the Leaflet instance because Leaflet manages its own DOM. Initialization creates tiles, layers, zoom and scale controls, and a click handler. A ResizeObserver updates the canvas when the layout changes. Separate effects manage the current map center, endpoint markers, route lines and the offline layer. Cleanup removes the map and cancels pending requests. GeoJSON coordinates are swapped to Leaflet lat/lng order. Dashed connectors show snapping gaps; they are not included in route distance. Tooltip labels use textContent. The tile layer follows the standard OSM URL and displays attribution. Offline mode loads local vector roads; it does not scrape tiles.

### Other frontend files
`api.js` centralizes the base URL, 90-second cold-start timeout, error parsing and formatting. An empty base URL uses the same origin; Netlify needs the real deployed API URL at build time. `icons.jsx` contains original inline SVG UI icons. `styles.css` defines the two-column desktop layout, stacked mobile layout, focus states and reduced-motion behavior. Web fonts have system fallbacks; the application remains usable without fetching fonts. `index.html` mounts React; `vite.config.js` proxies development API calls and builds static assets. `package.json` and its lockfile specify reproducible dependencies.

### Tests and deployment files
The C++ tests compare against Floyd–Warshall on seeded small random graphs, plus directed/mode/disconnected cases. Python tests launch a real C++ process, poll readiness, make HTTP requests, and terminate only their own processes. A synthetic graph used for unreachable tests is explicitly separate from real map data. `pytest.ini` limits discovery to tests/, avoiding execution of operational scripts as tests.

`generate_openapi.py` creates a checked-in schema. `unpack_data.py` verifies the graph checksum before writing its runtime file. `smoke_test.py` checks the URL it is actually given. Docker's web stage builds React, its C++ stage compiles and runs algorithm tests, and the final image contains only runtime files and a non-root user. `render.yaml` chooses a free Docker web service; `netlify.toml` selects the frontend build directory and headers. `.gitignore` excludes credentials, raw downloads and reproducible build outputs. CI repeats compilation, API tests and frontend build on Linux; a workflow file alone is not evidence that CI ran.

## 4. Concept primers

### Graphs, nodes, edges, weights and direction
A graph is a collection of things and links. Here the things are road coordinates and the links are traversable road segments. A weight is the cost of a link, here meters. A one-way road is a directed edge. Two different roads can connect the same nodes, making this a directed multigraph. An adjacency list stores each node's outgoing edges. For a sparse road graph it takes O(V+E) memory; an adjacency matrix uses O(V²), which is impractical for this graph.

Road-shape points are also nodes, not just intersections. The graph is not necessarily planar: bridges and tunnels may cross on the map without sharing a node. Connectivity requires a shared OSM node ID, not merely matching drawn pixels.

### Dijkstra, taught with a trace
For S→A=2, S→B=5, A→B=1, B→T=3: initialize S=0 and other nodes=infinity. Pop S, discover A=2/B=5. Pop A, improve B to 3. Pop B at 3, discover T=6. Skip the obsolete B=5 entry. Pop T and stop. Backtrack T←B←A←S. Nonnegative edge costs mean an already cheapest popped node cannot be improved by a path through a more expensive unsettled node.

Do not use BFS here: it minimizes the number of edges when weights are equal. One long motorway segment could be one edge, while a short curved street could contain ten edges. Do not use a greedy nearest-neighbor algorithm: a locally attractive direction can lead into a dead end.

### A*, admissibility and consistency
A* orders the queue by f(n)=g(n)+h(n). g is known cost from the source; h estimates remaining cost. Admissibility means h never exceeds the true shortest remaining cost. Consistency means h(u)≤w(u,v)+h(v) on every permitted edge. Our great-circle h is consistent because triangle inequality holds and each road edge length is at least its endpoint great-circle distance. h(target)=0. Setting h=0 recovers Dijkstra. A* does not promise a different or shorter answer; it can reduce explored nodes.

If optimizing travel time, raw distance is the wrong-unit heuristic. A lower bound is distance divided by a valid upper bound on speed across every eligible edge. Using an average speed could overestimate time on a fast road and break admissibility. A heuristic multiplied by a number greater than one is weighted A* and can lose optimality.

### Time and space complexity
For this lazy-duplicate binary-heap implementation, a precise bound is O((V+E) log(E+1)) time and O(V+E) auxiliary space in the worst case; on ordinary sparse road graphs this is commonly written O((V+E) log V). Best-distance and parent arrays require O(V); the heap can contain O(E) entries. A* has the same worst-case bound with a consistent heuristic, though practical exploration differs. Per-mode union-find preprocessing is near-linear O(E α(V)); its arrays use O(V). Current snapping scans the whole graph, O(V), and place search scans P entries, O(P) plus sorting matches. Saying “every request is O(log V)” would be wrong.

### Haversine and WGS84
Latitude φ measures north/south, longitude λ east/west, in degrees in our API. Convert to radians before trig. Let a=sin²(Δφ/2)+cos φ₁ cos φ₂ sin²(Δλ/2), c=2 asin(√a), d=R c. We use R=6,371,008.8 m and clamp a into [0,1]. This is a spherical approximation to Earth, not an exact ellipsoidal WGS84 geodesic. WGS84 provides the geographic reference system; the implementation chooses a sphere for simple, consistent distance calculations.

Latitude ranges from -90 to 90, longitude from -180 to 180. A degree of longitude gets shorter towards the poles, so Euclidean degree distance is not a distance in meters. At the equator one degree of longitude is about 111.2 km. Longitude comes first in GeoJSON because its position convention is x,y; Leaflet accepts latitude,longitude.

### Tiles and Web Mercator
A raster map tile is a small image, commonly 256×256 pixels. At zoom z, a conventional slippy-map grid has 2^z tiles in each direction. The URL includes z/x/y. Web Mercator projects Earth onto a flat view: x is proportional to longitude and y to ln(tan(π/4+φ/2)). Its poles are unusable, so web maps stop near ±85.0511°. Scale distortion grows with latitude. Tile images are a visualization, not the graph used for routing. Downloading OSM vectors does not grant unlimited use of OSM's public tile servers.

### OSM data model, geocoding and reverse geocoding
A node is a coordinate and optional tags. A way is an ordered node list, often a road or polygon. A relation groups elements with roles. Tags are key/value attributes such as highway=residential. The same name can appear on many segments. Names are not unique IDs. Geocoding maps a name to coordinates; reverse geocoding maps coordinates to a nearby name or address. Navic's functions are local gazetteer search and nearest named feature, not a worldwide address database. Polygon centers can fall far from a usable entrance.

### REST, HTTP and JSON
An API is a defined interface between programs. A REST-style HTTP API identifies resources and uses HTTP semantics. GET retrieves data; POST /route accepts a structured calculation request. This POST does not persist a route. 200 means success, 204 an empty successful response, 400 malformed input, 404 missing resource/no route in our contract, 422 invalid values/coverage, 429 excessive requests and 500 unexpected server failure. JSON represents objects, arrays, strings, numbers, booleans and null; it has no valid NaN or Infinity literal. Parsing JSON is not the same as validating its meaning.

### CORS and security
An origin is scheme + host + port. A browser considers localhost:5173 and localhost:8080 different origins. JSON cross-origin POST usually triggers an OPTIONS preflight. The server returns allowed-origin/method/header values only for configured origins. CORS restricts browser reads; it is not authentication and does not stop curl. Rate limiting, body-size bounds and safe output are separate controls. The prototype has no accounts, payments or user data database. It does not trust client-supplied forwarding headers as identity. A cloud proxy may make many users share a bucket.

### Sync, async, threads and shared state
Synchronous C++ search runs until it returns. The HTTP server has a bounded thread pool, so several such operations can run concurrently. JavaScript fetch returns a Promise and lets the UI remain responsive while awaiting the network. Parallelism is actual simultaneous execution; concurrency is overlapping progress. Immutable graph data is safe to read across threads. Cache and token-bucket updates require a mutex. Route-local arrays require no shared mutex. A race occurs if two threads modify shared data without proper synchronization.

### Environments, containers, deployment, cold starts and caching
Environment variables configure a process without hard-coding values. A frontend VITE_ variable becomes public JavaScript at build time and must never contain a secret. A backend secret, if ever needed, belongs in a host secret/environment store. There are no paid API keys in this project.

A container packages an application with its user-space dependencies. It shares the host kernel, unlike a full virtual machine. A multi-stage build avoids shipping compilers and node_modules in the runtime. Deployment runs the artifact on another machine with a public URL, correct binding, health checks and TLS. A local preview or a Dockerfile alone does not satisfy the public-API requirement. A free service can sleep after inactivity; its next request triggers a cold start. The browser uses a longer timeout, and the demo is warmed up by deliberately visiting /health before presenting, not by abusive continuous pings.

There are three different caches: a saved graph on disk, the graph loaded into RAM, and a bounded cache of route results. Route cache entries are process-local and disappear on restart. That is acceptable because they are derived data. Keys include source/destination nodes, mode and algorithm. Graph updates require a restart, which also clears stale cached paths. A cache hit reports zero new search work instead of pretending the old timing was freshly measured.

## 5. Why this choice over the alternatives?
| Decision | Chosen and defended | Alternative and trade-off |
|---|---|---|
| Backend language | C++17 meets preference and exposes graph data structures | FastAPI is faster to scaffold but would not meet the preferred backend language |
| HTTP library | cpp-httplib is lightweight and inspectable | Drogon/Crow offer richer frameworks but introduce more build/framework concepts |
| JSON | nlohmann/json provides parsing and clear validation | Hand-writing a JSON parser risks correctness and security errors |
| Graph | Native adjacency lists and compact integer indices | NetworkX is excellent for exploration but requires Python and has larger object overhead |
| Import | Explicit standard-library Python Overpass converter | OSMnx handles many GIS tasks but is unnecessary for a transparent bounded importer |
| Default algorithm | A* uses geographic information to focus search | Dijkstra remains the baseline and has no heuristic requirements |
| Weight | Distance in meters | Fastest-time routing needs a changed cost and compatible time heuristic |
| Snapping | Nearby shared-component nodes with reported gaps | Independent nearest nodes often land on disconnected campus/parking loops; edge snapping is more precise but more complex |
| Search | Local gazetteer supports autocomplete and offline demo | Public Nominatim forbids autocomplete; self-hosted geocoding needs much more data/resources |
| External routing | Not required for the core | OSRM comparison is useful future work, but equal route shapes cannot be assumed across different cost profiles |
| Frontend | React separates state from rendering | Plain JS has fewer dependencies but becomes harder to coordinate for stale requests and controls |
| Map library | Leaflet 1.9.4 stable raster/vector rendering | MapLibre is powerful for vector styling but adds a style/tile pipeline unnecessary here |
| Persisted graph | NDJSON + gzip, streamed once at startup | One enormous JSON DOM increases peak memory; a binary format would be smaller/faster but less inspectable |
| Storage | Read-only files, no user database | Postgres is unnecessary for immutable graph data and introduces operations work |
| Route cache | Bounded in-memory FIFO, simple to explain | LRU/Redis can improve hit rates or sharing but adds complexity |
| Worker model | Four blocking HTTP workers | An async networking framework improves IO concurrency; route computation is still CPU work |
| Hosting | Render free Docker with visible limits | Railway was not selected; its current plan would need separate verification |
| Frontend hosting | Netlify free static hosting | Render can also serve the built frontend in the same image, simplifying CORS and offline rehearsal |
| Testing | C++ oracle tests plus pytest real HTTP tests | Only happy-path browser testing misses algorithm and protocol errors |
| Security | Input checks, bounds, CORS, rate limits, non-root image | Authentication would be needed if accounts, private data or privileged changes were added |

## 6. Weaknesses an examiner may probe
| Probe | Confident, honest answer | Concrete improvement |
|---|---|---|
| “Is this all Delhi NCR?” | No. It is a bounded pilot with an explicit bbox shown in the UI. | Partitioned regional extracts and measured scaling |
| “Could the route make an illegal turn?” | Yes. Turn-restriction relations and conditional restrictions are not represented. | Edge-based state or turn-expanded graph with relation parsing |
| “What about gates?” | Barrier nodes are not modeled; access profiles are conservative but incomplete. | Barrier and conditional-access parsing with profile tests |
| “Why no route from a building?” | Buildings are represented by centers. Shared-component snapping can find nearby roads, but the access gap remains excluded. | Entrance selection and point-to-edge snapping |
| “Is ETA accurate?” | It is a static estimate with documented speeds, not a traffic prediction. | Traffic/turn-delay/elevation models; separate time optimization |
| “Why does reverse geocoding not give my address?” | It returns the nearest named indexed feature and labels that result approximate. | Address interpolation or a dedicated local geocoder |
| “Why does A* sometimes not beat Dijkstra?” | A weak heuristic, graph geometry, ties, caches and timing noise can reduce the benefit. | Benchmark uncached workloads and report distributions |
| “Can many users use it?” | Workers, CPU and rate limits are small; free hosting is for demonstration. | Spatial indexing, load tests, query budgets and paid/scaled infrastructure if permitted |
| “Does offline mean hosted app works without internet?” | No. The fully offline demonstration runs the local API and built frontend with local road geometry. | A deliberately designed offline browser runtime/packaged app |
| “Did you independently write everything?” | This project uses open-source libraries and was built with AI assistance. I can trace, test and modify the routing implementation; I should acknowledge assistance under college rules. | Demonstrate understanding by changing an edge/test and explaining the outcome |

## 7. Learning order and mock viva protocol
1. Run the app and narrate one request without reading the code.
2. Hand-trace the four-node shortest-path example.
3. Read graph.hpp and explain every state variable in the search loop.
4. Inspect an actual /route request and response; identify all units and coordinate order.
5. Run the tests and explain one independent oracle case and one HTTP validation case.
6. Practice a failure: select a disconnected road pair, then demonstrate offline roads locally.
7. Read the question bank and cheat sheet; answer aloud before revealing answers.

After the build and deployment are complete, the live mock viva is interactive: one question, your answer, a score out of 10, what was missed, and the ideal answer. Difficulty increases from architecture to algorithms, data, deployment and defense. The session continues until you say stop. A written question bank does not replace that interactive session.
