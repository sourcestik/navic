# 60 viva questions with model answers and follow-ups

The graph, snapping, heuristics and benchmarks below refer to the custom Delhi engine. The worldwide default delegates to OSRM; see worldwide.md for its profiles and provider limits. Answer aloud before reading the model. Tailor answers to the implementation, not to features a production map service might have.

## Basics

### 1. What problem does Navic solve?
It lets a user choose two places worldwide and see a mode-specific road route, estimated travel time and basic turn instructions. It also exposes the same core functions as an HTTP API. A map display alone would not meet the routing or public-API requirement.
**Follow-up:** Is this a GPS navigation device? **Answer:** No. It is a browser route planner with optional one-time browser geolocation, not continuous satellite tracking or spoken navigation.

### 2. What are the main parts of the system?
React manages interface state, Leaflet displays the map, and a C++ service searches a prebuilt OSM graph. A Python script prepares data offline. Online map tiles are a separate display service; they do not compute the route.
**Follow-up:** What still works if the tile server fails? **Answer:** Local search and C++ routing still work; the offline road-geometry layer can replace the tile backdrop.

### 3. Why is this an electrical-engineering project?
It applies graph optimization, measurement, data modeling and systems integration. Similar shortest-path methods arise in communication networks and infrastructure planning. I should demonstrate the connection without pretending that this road router solves power-flow equations.
**Follow-up:** Is a minimum spanning tree the same problem? **Answer:** No. An MST minimizes the total cost to connect all vertices; a shortest path minimizes the cost between selected endpoints.

### 4. Which part did you implement from scratch?
The adjacency-list graph model, Dijkstra/A* search, path reconstruction, mode-aware snapping and basic maneuver generation are project code. HTTP parsing, JSON parsing, UI rendering and map rendering use existing libraries. OpenStreetMap supplies the data; I did not create the road survey.
**Follow-up:** Did AI help? **Answer:** Yes; assistance should be acknowledged according to college rules. Understanding and demonstrating the resulting code is my responsibility.

### 5. What does “shortest route” mean here?
It means minimum sum of edge lengths on the selected directed, mode-filtered graph between snapped endpoints. It does not mean minimum straight-line distance between the original buildings, fastest travel time or shortest path on every road in NCR.
**Follow-up:** Can the displayed distance exclude part of my journey? **Answer:** Yes. The gaps from selected points to road nodes are displayed separately and excluded from route distance/ETA.

### 6. What are your measurable deliverables?
A working interface, a C++ API, real graph data, automated test evidence, deployment files, source and documentation. The public API deliverable is complete only when the actual HTTPS URL passes /health and real /route smoke tests.
**Follow-up:** Is localhost a live public deployment? **Answer:** No. It is only a local execution environment.

## Algorithms

### 7. Explain Dijkstra's algorithm.
Initialize the source distance to zero and others to infinity. Repeatedly remove the smallest known distance from a priority queue and relax its outgoing permitted edges. With nonnegative weights, a popped current-best destination has an optimal cost; parent edge IDs reconstruct the path.
**Follow-up:** Why not stop when the destination is first discovered? **Answer:** A later route through another unsettled node may improve that first candidate.

### 8. How does A* differ?
A* orders the same frontier by f=g+h, where h estimates remaining distance. Dijkstra uses h=0. Our haversine heuristic focuses exploration toward the target while preserving optimality under the edge-length invariant.
**Follow-up:** Does A* always return a shorter route? **Answer:** No. Both return the same optimal cost; tie-breaking may choose different equal-cost paths.

### 9. What makes the heuristic admissible?
It never exceeds the true remaining road distance. Great-circle distance is no greater than the sum of segment great-circle distances, and each graph edge is at least that segment distance. Therefore the heuristic is a lower bound for the graph objective.
**Follow-up:** Can you use distance directly when the weight is seconds? **Answer:** No. The units differ. Divide by a valid maximum speed to obtain a time lower bound.

### 10. What is consistency?
For each edge u→v, consistency requires h(u)≤w(u,v)+h(v). Our distance heuristic satisfies this by triangle inequality. It prevents a better path from later requiring a re-expansion of a correctly settled node, apart from numerical considerations.
**Follow-up:** Is every admissible heuristic consistent? **Answer:** No. Admissibility constrains the total remaining estimate; consistency additionally constrains neighboring estimates. General inconsistent heuristics may require reopening nodes.

### 11. What is the complexity of your implementation?
It uses a binary heap with lazy duplicate entries. A precise worst-case time bound is O((V+E) log(E+1)), commonly simplified to O((V+E) log V) for sparse/simple road graphs. The graph is O(V+E), and per-search arrays plus the heap can use O(V+E) auxiliary memory. Snapping adds O(V) scanning.
**Follow-up:** Why can the heap use more than O(V)? **Answer:** Improving a node inserts a new entry; old entries remain until popped and skipped.

### 12. Why not BFS, DFS or Bellman–Ford?
BFS minimizes edge count when weights are equal, which is not our distance objective. DFS finds a traversal path without guaranteeing minimum cost. Bellman–Ford handles negative weights but costs O(VE); road lengths are nonnegative, so Dijkstra/A* fit better.
**Follow-up:** What happens if an edge has negative length? **Answer:** The loader rejects it. Allowing negative edges would break the assumptions behind the search and heuristic.

## Backend

### 13. Why C++ rather than FastAPI?
C++ matches the preferred backend language and makes the graph representation and algorithms explicit. It can store the graph compactly and compile to a standalone executable. FastAPI would simplify schema-driven endpoints, but would introduce a Python runtime and a different learning focus.
**Follow-up:** Does C++ automatically guarantee speed? **Answer:** No. Data structures, algorithms, IO, compiler settings and workload matter; the project measures actual behavior.

### 14. How do you represent the road graph?
Nodes have compact indices, coordinates and outgoing edge IDs. Edges store source, destination, distance, three time estimates, a name index and mode bits. Sparse OSM IDs are mapped to compact array indices during preparation.
**Follow-up:** Why store parent edges instead of only parent nodes? **Answer:** Parallel edges can connect the same nodes with different attributes; the exact selected edge must be recovered.

### 15. How does snapping work?
For each mode, the service precomputes weakly connected components. It finds nearby candidate source and destination nodes per component and prefers the shared component with the smallest combined snapping gaps, within 800 m per endpoint. Dijkstra/A* then checks directed reachability; an absent nearby node yields 422.
**Follow-up:** Does shared weak connectivity guarantee a route? **Answer:** No. Ignoring direction can connect nodes whose required directed route does not exist. The search can still return 404.

### 16. What is cached?
The graph snapshot is stored on disk and loaded once into memory. A separate bounded FIFO cache stores successful route responses keyed by snapped endpoints, mode and algorithm. Per-request snapping labels and distances are added separately so slightly different clicked points do not inherit stale gap values.
**Follow-up:** What happens after a graph update? **Answer:** Restarting loads the new graph and creates an empty in-memory route cache, avoiding cross-version results.

### 17. How do concurrent requests work?
The HTTP server uses a bounded pool of four workers. The graph is immutable after startup and can be read concurrently. Search arrays are local; shared cache and rate-limiter state are guarded by mutexes.
**Follow-up:** Is the server asynchronous? **Answer:** Each handler is synchronous. The worker pool provides concurrency; asynchronous browser fetch is a separate concept.

### 18. Why have both /health and /coverage?
/health confirms readiness and reports counts/version. /coverage exposes bounds, modes, algorithm choices, snapping strategy and data provenance. Keeping them separate lets monitoring stay simple while clients retrieve richer capabilities.
**Follow-up:** Could /health return success before the graph is loaded? **Answer:** In this implementation the listener starts only after loading graph, network geometry and docs, so it cannot report readiness prematurely.

## Frontend

### 19. What does React do here?
It maps application state to interface elements. Endpoint selections, travel mode, algorithm, loading status and route data determine what is displayed. Leaflet manages the map DOM through a ref and effects rather than React recreating a map on every render.
**Follow-up:** Why not store the Leaflet map in state? **Answer:** It is an imperative object whose mutations should not trigger React rendering; a ref is a better lifetime container.

### 20. How does autocomplete avoid excessive requests?
The component waits 300 ms after edits before querying, cancels superseded requests and limits result count. It searches our local index, so it does not send keystrokes to public Nominatim. Keyboard selection and clear/empty/error states are explicit.
**Follow-up:** Is debouncing a security rate limit? **Answer:** No. A different client can bypass it, so the server also enforces a token bucket.

### 21. How do you prevent stale route results?
Changing an endpoint, mode or algorithm invalidates the current route and aborts the request. A revision number also checks that a response still belongs to current inputs before accepting it. This protects against responses arriving in an unexpected order.
**Follow-up:** Does aborting fetch necessarily stop the C++ computation? **Answer:** No. It stops the browser waiting for the response; a server handler may already be computing.

### 22. How does “use my location” work?
The browser geolocation API asks the user for permission and returns coordinates. The app validates that they are inside coverage, sets the source and handles denied permission/timeouts. Geolocation normally requires HTTPS or a trusted local development context.
**Follow-up:** Does the server read GPS directly? **Answer:** No. The browser obtains the location, and coordinates are included in a routing request only through the app flow.

### 23. What makes the interface responsive and accessible?
CSS switches from desktop columns to a stacked mobile layout. Inputs have labels, mode controls expose selected state, suggestions support keyboard navigation, errors have alert roles, and focus states are visible. ResizeObserver informs Leaflet when its container changes size.
**Follow-up:** Does a responsive stylesheet prove accessibility? **Answer:** No. Keyboard, contrast, screen-reader and device testing are separate checks; only performed checks should be claimed.

### 24. How is the route drawn?
The API returns a GeoJSON LineString with longitude/latitude positions. The map component converts them to Leaflet latitude/longitude pairs and draws a white outline plus a green route line. Dashed lines show excluded snapping gaps.
**Follow-up:** Why can a route look wrong even with correct numbers? **Answer:** Swapping lat/lon conventions can put it in the wrong part of the world; styling or stale map state can also hide it.

## Maps and geography

### 25. What is OpenStreetMap?
It is a collaboratively maintained geographic database with nodes, ways, relations and tags. Navic downloads a bounded snapshot through Overpass and attributes OSM contributors. Data quality, completeness and freshness vary by location.
**Follow-up:** Are OSM tiles and OSM data the same service? **Answer:** No. The database is open data; a public tile service has separate capacity and usage rules.

### 26. What is the haversine formula used for?
It computes great-circle distance on a spherical Earth from two latitude/longitude points. We use it for segment lengths, snapping and the A* heuristic. Degrees are converted to radians; the output is meters using R=6,371,008.8 m.
**Follow-up:** Is it an exact WGS84 ellipsoid solution? **Answer:** No. It is a spherical approximation; the model uses it consistently and states that limitation.

### 27. What are WGS84 and Web Mercator?
WGS84 is the geographic reference system used for latitude/longitude coordinates. Web Mercator is a projection commonly used to display those coordinates on web maps. It distorts scale and cannot represent the poles, so screen pixel distance is not our routing cost.
**Follow-up:** Why not compute distance from map pixels? **Answer:** Pixel scale depends on zoom and latitude; geographic calculations should operate on coordinates and units.

### 28. How do map tiles work?
The viewport requests image tiles identified by zoom z and tile indices x/y. At zoom z the conventional grid has 2^z tiles per axis. Leaflet arranges visible tiles and the browser follows caching headers; the project does not bulk-download tiles.
**Follow-up:** How does the offline demo get a map? **Answer:** It draws bundled OSM vector road geometry, not an offline archive of OSM's public tiles.

### 29. What is geocoding versus reverse geocoding?
Geocoding finds coordinates from a name/address. Reverse geocoding finds a name/address near coordinates. Our implementation is a limited local name index and nearest named feature, so it explicitly marks reverse lookup approximate.
**Follow-up:** Why not call Nominatim on every keystroke? **Answer:** Its public service policy forbids autocomplete. A local index also supports the offline demonstration.

### 30. How are travel modes represented?
Each directed edge has a bitmask: driving=1, walking=2, cycling=4. Access tags and one-way rules determine which bits are set. Ordinary vehicle one-way tags do not automatically prevent walking in the reverse direction.
**Follow-up:** Does this implement every Indian traffic rule? **Answer:** No. Conditional access, barriers, turn restrictions and the full regional defaults are limitations, not inferred guarantees.

## Deployment

### 31. What does deployment mean?
It means running the app on a server reachable through its actual public URL, with suitable configuration and data. A successful local run, a prepared Dockerfile or a proposed hostname is not deployment evidence. I verify /health and /route against the returned live address.
**Follow-up:** Why must the server bind to 0.0.0.0 in a container? **Answer:** Binding only loopback would prevent the host's routing layer from reaching it on the container network.

### 32. Why use Docker for C++?
It captures the compiler/build stage and runtime dependencies in a reproducible recipe. A multi-stage build keeps the final image smaller and avoids installing compilers or frontend packages at startup. It also gives Render an executable container workflow.
**Follow-up:** Is a container a virtual machine? **Answer:** It isolates processes and user-space resources while sharing the host kernel; a VM normally has its own guest kernel.

### 33. What is a cold start?
A sleeping free service must start its process and load the graph when traffic returns. That creates a delay beyond route-search time. The frontend allows a longer timeout and explains reconnection; the demo begins by checking /health.
**Follow-up:** Why not ping it constantly? **Answer:** That defeats the intended free-service idle behavior and consumes resources. Deliberate pre-demo readiness checks are sufficient.

### 34. How do you fit the graph into limited RAM?
The graph uses native arrays and shared road names, and is read one record at a time from NDJSON. The compressed file is unpacked during setup/image build, not downloaded during startup. Resource measurements are recorded locally and must also be checked on the deployed service.
**Follow-up:** Does gzip alone reduce runtime graph memory? **Answer:** No. Compression reduces stored/transferred bytes; the in-memory representation determines runtime RAM.

### 35. What happens on an ephemeral filesystem restart?
Runtime changes and process-local caches disappear. The image still contains the read-only graph and application assets, so they are available again on startup. No user data is persisted by this prototype.
**Follow-up:** Would saving uploads to that filesystem be reliable? **Answer:** No. Persistent user data would need appropriate durable storage, outside this project's current scope.

### 36. How does Netlify talk to Render?
The frontend build receives the actual API URL through VITE_API_BASE_URL. The C++ service's ALLOWED_ORIGINS includes the exact frontend origin, with scheme and no path/trailing slash. HTTPS prevents mixed-content failures; cross-origin JSON POST is handled through CORS preflight.
**Follow-up:** Does changing a VITE_ variable update an already-built bundle? **Answer:** No. It is embedded at build time, so the frontend must be rebuilt/redeployed.

## Testing

### 37. How do you know both algorithms are correct?
Small seeded random directed graphs are checked against an independent Floyd–Warshall distance oracle. Focused tests cover one-way edges, permission filtering, parallel edges, zero-length results and disconnection. Agreement between Dijkstra and A* alone could hide a shared bug.
**Follow-up:** Do passing tests mathematically prove correctness? **Answer:** No. Tests provide evidence; the reasoning depends on nonnegative weights, valid relaxation, queue ordering and the heuristic invariant.

### 38. What is an integration test here?
Pytest launches the real compiled C++ server and makes actual HTTP requests. It checks responses, headers, schema-related behavior and lifecycle cleanup. This goes beyond testing an isolated function with mocked networking.
**Follow-up:** Why use Python to test a C++ backend? **Answer:** The public boundary is HTTP/JSON; the client language is independent. Python provides concise test orchestration.

### 39. What happens for identical endpoints?
They are snapped to the same usable node and yield zero road distance and time. The result contains an arrival instruction and a two-position GeoJSON line with duplicate coordinates. The original point's access gap is still separate from road distance.
**Follow-up:** Can two different clicked points also produce zero road distance? **Answer:** Yes, if both snap to the same node. The warning and gap distances explain this.

### 40. How do you test unreachable routes?
A synthetic graph with two isolated components is served by a separate test process. Endpoints near each component should produce 404 NO_ROUTE. Another test puts a point too far from usable nodes and expects 422 SNAP_TOO_FAR.
**Follow-up:** Why not use arbitrary real coordinates for this test? **Answer:** Real OSM edits may change connectivity; a controlled fixture makes the intended edge case reproducible.

### 41. How do you measure performance fairly?
Separate startup, snapping, algorithm search, serialization and whole-request time. Compare uncached requests on the same graph/mode/endpoints, and report visited nodes alongside timing. A single local machine's result is not a cloud latency guarantee.
**Follow-up:** Why does a cached request show zero visited nodes? **Answer:** It performed no new search; reporting previous search work as current work would be misleading.

### 42. What did browser testing add?
It verifies controls, selection, drawn geometry, errors and presentation together. API tests cannot show a stale map, swapped inputs or a broken dropdown. Conversely, a visible line does not prove optimality, so both layers are necessary.
**Follow-up:** What if mobile layout was only inspected in a desktop browser? **Answer:** Report it as viewport testing; do not claim physical-device or GPS permission tests that were not performed.

## Security

### 43. How do you validate inputs?
The API checks content type, body size, JSON structure, required fields, numeric types, finite values, coordinate ranges, coverage and mode/algorithm enums. Query numbers must be fully parsed; trailing text and NaN are rejected. Errors have consistent codes and messages.
**Follow-up:** Is valid JSON necessarily valid input? **Answer:** No. For example, a valid JSON string containing latitude is rejected where a number is required.

### 44. What does CORS protect?
It controls whether browser JavaScript from another origin may read a response. The app uses an explicit origin allowlist and supports OPTIONS preflight. CORS does not authenticate a client or prevent direct requests from scripts.
**Follow-up:** Can curl bypass CORS? **Answer:** curl does not enforce browser-origin policy, so server validation and limits remain essential.

### 45. How does rate limiting work?
A token bucket refills at the configured rate and consumes a token for each search/reverse/route request. Exhaustion returns 429 with Retry-After. Identity state is bounded and idle entries are removed so the limiter itself cannot grow without limit.
**Follow-up:** Why not use any supplied X-Forwarded-For value? **Answer:** Clients can forge it. Only verified proxy configuration should be trusted; this prototype uses the socket peer and acknowledges possible shared proxy buckets.

### 46. Where are API keys stored?
The current app needs no paid API keys. Any future backend secret belongs in environment/secret storage and must be excluded from Git. VITE_ values are public in the browser and are only for non-secret configuration such as the API URL.
**Follow-up:** Does adding a key to .gitignore erase an earlier commit? **Answer:** No. A leaked secret must be revoked/rotated; Git history may still contain it.

### 47. Can an OSM place name inject JavaScript?
React renders names as escaped text, and Leaflet tooltips use a created element's textContent. The app does not inject OSM names into innerHTML. The tiny marker HTML is built only from fixed project-controlled values.
**Follow-up:** Why does JSON parsing not prevent XSS by itself? **Answer:** XSS depends on how a string is later inserted into HTML or another executable context.

### 48. What privacy precautions are present?
The service has no user account/history database and logs method, path and status rather than coordinates, request bodies or IP addresses. Routing requests still necessarily send selected coordinates to the API. Browser tile requests expose the viewed area to the tile provider.
**Follow-up:** Does “no database” mean no data leaves the browser? **Answer:** No. Network requests still communicate data; privacy claims must describe those requests honestly.

## Limitations

### 49. Is the route always legally drivable?
No. The importer handles a documented subset of access and one-way tags but not turn-restriction relations, barriers, conditional rules or every regional default. It is an educational routing prototype. The UI and report state this rather than claiming production-grade legality.
**Follow-up:** How would you enforce a no-right-turn relation? **Answer:** Make the search state include the incoming edge, or construct a turn-expanded graph, then reject the prohibited edge transition.

### 50. How accurate is the ETA?
It sums length divided by estimated speed on every selected edge. It excludes live traffic, traffic-signal waiting, acceleration, elevation and access gaps. It demonstrates a useful computation but is not a prediction calibrated from actual trips.
**Follow-up:** Why may a shorter route take longer? **Answer:** It can use slower roads; distance and travel time are distinct objectives.

### 51. What are the consequences of a bounding box?
Routes cannot use roads outside the extracted area. A trip inside the box may be unreachable or longer if the natural route leaves and re-enters. The boundary is visible and outside endpoints are rejected instead of silently expanding the service claim.
**Follow-up:** Does an inside point guarantee connectivity? **Answer:** No. It may be far from a usable road or on a disconnected component.

### 52. Why is nearest-node snapping imperfect?
The nearest road point may lie between stored nodes or across an inaccessible barrier. A polygon center may be inside a private compound. Component-aware candidate selection helps connectivity but does not prove a legal entrance or last-meter access path.
**Follow-up:** What is better than node snapping? **Answer:** Project onto nearby permitted edges, split them with temporary query nodes and consider direction/access/entrance information.

### 53. Why can turn instructions sound awkward?
They are generated from consecutive edge bearings and road-name changes. Curves, roundabouts, unnamed roads and complex junctions may produce extra or incomplete instructions. There is no lane guidance or roundabout-exit numbering model.
**Follow-up:** Is route geometry still useful when text is imperfect? **Answer:** Yes for the academic demonstration, but it must not be sold as reliable turn-by-turn safety guidance.

### 54. Is the local geocoder complete?
No. It covers selected named OSM features in the snapshot and does basic ASCII case-insensitive matching. It is not full Unicode normalization, fuzzy search, house-number interpolation or a national address service. Unknown queries return an empty list and the map remains selectable.
**Follow-up:** Could two places with the same name be different? **Answer:** Yes. Current name deduplication favors concise results but can hide a second same-named place; geographic ranking/grouping is a future improvement.

## Future scope

### 55. How would you support all Delhi NCR?
Measure graph and workload growth, then add spatial indexing, regional partitioning or tiles and a compact binary format. A larger data extract alone is not enough; startup, RAM, route-query cost and hosting capacity must be revalidated. Full-area coverage should only be claimed after tests across that region.
**Follow-up:** Can you merge independently clipped graphs trivially? **Answer:** No. Boundary connectivity and shared node IDs must be preserved and duplicate edges handled.

### 56. How would you make snapping faster?
Use a spatial index such as a k-d tree or R-tree to retrieve nearby candidate nodes or edges, then apply exact geographic distance and mode checks. Candidate retrieval reduces scanning, while the final metric preserves correctness. Connectivity and access still need separate handling.
**Follow-up:** Does a k-d tree on raw degree coordinates automatically give correct geodesic nearest neighbors? **Answer:** No. Coordinates and distance bounds require a suitable projection or careful candidate expansion.

### 57. How would you add fastest routes or live traffic?
Use edge travel time as the optimization weight and replace the heuristic with a compatible lower bound in seconds. A traffic feed would update costs, with versioned caches and freshness reporting. Static ETA estimation is not equivalent to this change.
**Follow-up:** What if travel times depend on departure time? **Answer:** The model becomes time-dependent routing; FIFO assumptions and time-aware cost functions must be considered.

### 58. How would you produce alternative routes?
Implement and test a real k-shortest-path method, such as Yen's algorithm for loopless alternatives, then filter routes for overlap and usefulness. Re-running A* with the same weights simply returns the same optimum. Penalizing edges can provide diversity but changes the optimization problem and needs disclosure.
**Follow-up:** Are the next three shortest paths necessarily good alternatives? **Answer:** No. They may differ only by tiny detours, so overlap and quality criteria matter.

### 59. How would you compare against OSRM?
Use the same endpoints and travel profile where possible, then compare distance, geometry, snapping, runtime and instruction differences. OSRM may use different data, access rules, optimization weights and preprocessing. A discrepancy does not automatically prove either implementation wrong.
**Follow-up:** Why not use OSRM as the only correctness oracle? **Answer:** Its model is not identical and it is an external system. Small graphs with known optimal costs provide a controlled oracle.

### 60. What would you improve first for a real product?
I would first improve legal/access correctness through turn restrictions, barriers and entrance/edge snapping, then introduce spatial indexing and realistic performance/load testing. Reliable geocoding, observability, calibrated travel times and clear privacy controls follow. Production safety requires more than a polished map.
**Follow-up:** If you had only one more day for the minor project? **Answer:** Rehearse the exact demo, verify the live URL and offline fallback, and strengthen tests/documentation for the current scope rather than adding untested features.
