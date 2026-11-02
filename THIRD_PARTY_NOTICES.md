# Third-party code and data

| Component | Pinned version | License / source |
|---|---|---|
| cpp-httplib | 0.56.0 | MIT, backend/vendor/LICENSE.httplib; https://github.com/yhirose/cpp-httplib |
| nlohmann/json | 3.12.0 | MIT, backend/vendor/LICENSE.json; https://github.com/nlohmann/json |
| React / React DOM | 19.3.1 | MIT; https://github.com/facebook/react |
| Leaflet | 1.9.4 | BSD-2-Clause; https://github.com/Leaflet/Leaflet |
| Vite | 8.3.5 | MIT; https://github.com/vitejs/vite |
| Swagger UI | 5.34.1 | Apache-2.0; https://github.com/swagger-api/swagger-ui |
| pytest | 8.4.2 | MIT; https://github.com/pytest-dev/pytest |
| OpenStreetMap | Snapshot 2026-11-01T19:03:08Z | ODbL 1.0; https://www.openstreetmap.org/copyright |

The graph and road geometry are derived from OpenStreetMap and are distributed under ODbL 1.0, not under the project's code license. Their database source is the bounded Overpass extract described by scripts/prepare_data.py. Attribution is displayed in the UI and metadata. The raw extraction can be reproduced from the query and bbox, though a fresh query retrieves a newer snapshot. The compressed delivered database plus checksum preserves the exact demonstrated snapshot.

DM Sans and Manrope are requested from Google Fonts for presentation, with local system-font fallbacks. Their upstream font distributions use the SIL Open Font License. No font or tile bulk-download feature is included. Pnpm's lockfile records transitive JavaScript packages; their own license files remain in installed dependencies.

Open tools do not imply unlimited free hosted capacity. Provider usage limits and map-service policies are documented in docs/06-deployment.md and docs/references.md.
