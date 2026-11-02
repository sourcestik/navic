# Live demo script and failure recovery

## Before the viva (10 minutes)
Keep the actual deployed frontend, API /docs and /health tabs ready. If public deployment is not yet completed, describe the local demonstration as local and finish deployment before submitting. Check the exact commit/data version. Start the local fallback and test it before the room loses connectivity.

```sh
cd /Users/swastikbarik/Documents/Navic
python3 scripts/unpack_data.py
./build/navic-api
```

The compiled binary and `frontend/dist` should already exist. If rebuilding is needed, follow README while internet is available. Open `http://127.0.0.1:8080`. No Python web server replaces the C++ API.

## Five-minute demonstration
| Time | Click or command | What to say |
|---|---|---|
| 0:00 | Open the map; point to the dotted coverage boundary | “This is a Delhi NCR pilot, from Dwarka to parts of central Delhi.” |
| 0:25 | Choose “From campus to a coffee” | “These endpoints come from the bundled OSM place index, including the NSUT relation and mall polygon.” |
| 0:45 | Select Drive and A*, then Find my route | “The C++ API validates, snaps to usable nodes, searches and returns geometry plus metrics.” |
| 1:15 | Point to distance, time and snapping gaps | “The route minimizes road distance; ETA is static. Access gaps are shown separately.” |
| 1:40 | Expand Under the hood | “These are visited nodes and search-only time. If cached, the UI says no new search was performed.” |
| 2:00 | Change algorithm to Dijkstra and calculate again | “The optimal distance stays the same, while search effort can change.” |
| 2:30 | Switch to Walk and calculate | “The travel-mode mask changes eligible edges and ETA; it is not just a different icon.” |
| 3:00 | Open /docs; show POST /route schema and execute | “The backend is independently usable by another client; it is not coupled to React.” |
| 3:40 | Show one invalid/outside-coverage request | “The API returns a structured validation error rather than a misleading route.” |
| 4:10 | Switch the local app to Offline roads | “The road graph and backdrop are bundled. Routing does not require tiles or a live geocoder.” |
| 4:40 | Open test evidence and state limitations | “The algorithm was checked against Floyd–Warshall. Turn restrictions and live traffic remain out of scope.” |

## If something fails
- **API is sleeping:** show /health and allow about a minute. Explain the free-host cold start, then retry once. Do not keep clicking and create a request flood.
- **Internet unavailable:** use the local C++ app and select Offline roads. Bundled assets and road vectors work without external tiles. The Swagger UI uses a pinned CDN and may not load offline; show `docs/openapi.json` instead.
- **API deployed but frontend fails:** inspect the actual VITE_API_BASE_URL and exact ALLOWED_ORIGINS. Demonstrate the API with curl or Swagger while explaining the CORS/configuration issue honestly.
- **Place missing:** search an alternative known landmark or click within the coverage boundary. Do not claim a worldwide address service.
- **No route:** explain modes, access, isolated components and the boundary. Use the tested NSUT–Vegas demo pair rather than pretending every pair is reachable.
- **Machine fails:** use the report screenshots and saved benchmark/test artifacts to explain the result, but label this as recorded evidence, not a live run.

## A direct API demonstration
```sh
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/route \
  -H 'Content-Type: application/json' \
  -d '{"source":{"lat":28.6109714,"lon":77.037946},"destination":{"lat":28.6010845,"lon":77.0296006},"mode":"driving","algorithm":"astar"}'
```

Expected road distance for the bundled snapshot is approximately 2,893.48 m and estimated time 419.57 seconds; source/destination access gaps are approximately 181.76 m and 85.06 m. New OSM data or routing-profile changes can alter these values. Do not hard-code these numbers into the UI.
