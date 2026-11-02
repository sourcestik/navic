# Phase 6 — deploy the C++ API publicly

## Current state
On 2 November 2026, Render served version 2.0.0 at https://navic-delhi.onrender.com (release 883c946). The public API returned a Paris–Brussels driving route of 311.9 km in an estimated 3 h 37 min and rejected New York–London with 404 NO_ROUTE. The app and API share one free Docker service in Singapore. Leave Docker Command empty. See [worldwide configuration](worldwide.md).

## Connect accounts so the assistant can deploy
1. Open the **Plugins** directory in Codex (or the shared [ChatGPT plugins directory](https://chatgpt.com/plugins)). Search **GitHub**, open it and install it. Complete the GitHub sign-in/authorization flow and include the intended Navic repository in its access scope. If the repository does not exist yet, it can be created after account access is confirmed; repository visibility must be chosen deliberately.
2. Find **Render** in the same directory, install it and complete its connection flow. Use your own Render account/workspace. If it asks for a Render API key rather than OAuth, follow the account's API-key settings and paste the key only into the secure connection form, never into chat, source code or the frontend environment.
3. In the [Render dashboard](https://dashboard.render.com/), open Account Settings → Account Security → Git Deployment Credentials → Add credential → GitHub. Authorize the Render GitHub app for the Navic repository. This is distinct from connecting GitHub to Codex. [Official Render instructions](https://render.com/docs/git-provider).
4. Return to this chat and say **“GitHub and Render are connected.”** If a repository already exists, provide its URL. The assistant must confirm the actual connection state, push the source, create a free Docker web service, wait for deployment and test the returned public URL.

Button names can vary with the app version. Installation alone does not confirm authentication. The shared directory and install flow are described in [OpenAI's plugin documentation](https://developers.openai.com/plugins/quickstart).

## Verified free-service limits (checked 2 November 2026)
| Service | Current relevant limit | Project response |
|---|---|---|
| Render free web service | 512 MB RAM, 0.1 CPU | Streaming graph loader, bounded workers/cache; measure deployed memory |
| Render inactivity | Sleeps after 15 minutes; wake-up can take about a minute | UI timeout/retry guidance; visit /health before the viva |
| Render allowance | 750 free instance hours per workspace/month; bandwidth/build limits also apply | Use one small service and inspect workspace usage |
| Render disk | Ephemeral; no free persistent disk | Bake immutable graph into the image; no runtime OSM downloads |
| Netlify Free | 300 monthly credits, hard free-plan limits; sites can pause at exhaustion | Few production builds; monitor credits; keep the frontend lightweight |

Sources: [Render free services](https://render.com/docs/free), [Render compute plans](https://render.com/docs/compute-plans), [Netlify pricing](https://www.netlify.com/pricing/). Render's bandwidth rules can create charges on accounts that have billing enabled; use the free plan, inspect the current account's limits and do not enable a paid upgrade or paid overage. Provider policy can change. This guide does not guarantee indefinite free availability.

## First deployment: Render can serve both API and frontend
Serving both from the supplied Docker image is the simplest initial public demonstration. Netlify can be added after the API passes its smoke test.

1. Push this repository to GitHub, including `data/graph.ndjson.gz`, `data/network.geojson`, `data/metadata.json` and the vendored headers. Exclude `.env`, `.venv`, raw downloads and build/node_modules directories.
2. In Render select New → Web Service and choose the repository. Select the **Docker** runtime, the root `Dockerfile`, the main branch and the **Free** instance type. Do not choose a paid database, disk or service plan.
3. Use `/health` as the health-check path. The Docker image compiles the C++ program, tests the routing core and builds the frontend. It unpacks the graph before runtime. Render supplies `PORT`; the service binds to `0.0.0.0`.
4. Create the service and read the actual assigned HTTPS URL. Set `ALLOWED_ORIGINS` to that exact origin, with no trailing slash, and redeploy/restart if required. A same-origin POST still sends an Origin header, so include the Render app origin too.
5. Alternatively use New → Blueprint with the supplied `render.yaml`; enter the actual allowed origins when prompted. The blueprint explicitly selects `plan: free`.
6. Wait for a successful deployment, read logs for graph counts and check for memory errors. Open the real URL's `/health`, `/docs`, and `/` in a browser.

## Local Docker verification on a machine with Docker
```sh
docker build -t navic:2.0 .
docker run --rm -p 8080:8080 --env-file .env navic:2.0
```

Create `.env` from `.env.example` first. The Procfile is included for compatible hosts, but **Render uses Dockerfile**, not Procfile or requirements.txt, to run this C++ service. `requirements.txt` is for Python tests only.

## Deploy the frontend to Netlify
1. Sign in to Netlify, choose Add new project/site → Import an existing project and authorize the same GitHub repository. Choose the Free plan.
2. The root `netlify.toml` specifies base `frontend`, build `pnpm run build`, publish `dist`, Node 24 and pnpm 11.25.0. The checked-in pnpm lockfile is authoritative.
3. Add the build environment variable `VITE_API_BASE_URL` with the **actual Render HTTPS URL**, without a trailing slash. This is public configuration, not a secret.
4. Deploy and read the actual Netlify site URL. In Render, append its origin to `ALLOWED_ORIGINS`, comma-separated with the Render origin and with no spaces/trailing slashes. Restart the backend as required by Render.
5. Open the Netlify site and compute a route. If a build-time API URL changes later, rebuild the frontend. If CORS fails, inspect scheme, host and port exactly; do not solve the problem with a wildcard allowlist.

## Environment reference
| Variable | Default / meaning |
|---|---|
| PORT | 8080 locally; provided by Render |
| HOST | 0.0.0.0; use 127.0.0.1 for local-only binding |
| GRAPH_PATH | data/graph.ndjson |
| NETWORK_PATH | data/network.geojson |
| OPENAPI_PATH | docs/openapi.json |
| SWAGGER_PATH | docs/swagger.html |
| STATIC_DIR | frontend/dist |
| ALLOWED_ORIGINS | Explicit comma-separated browser origins; local defaults are in .env.example |
| RATE_LIMIT_PER_MINUTE | 180 per socket peer by default |
| VITE_API_BASE_URL | Empty for same-origin; real HTTPS API URL for Netlify |
| VITE_TILE_URL | Standard OSM tile URL by default; replace with a permitted provider when needed |

No map/routing API key is required. Do not paste hosting account secrets into VITE_ variables.

## Live smoke test: exact commands without an invented hostname
From the repository root in a POSIX shell:
```sh
printf 'Paste the actual deployed API URL: '
read -r NAVIC_API_URL
python3 scripts/smoke_test.py "$NAVIC_API_URL" --output artifacts/public-smoke-test.json
```

The script checks graph readiness, searches the actual campus/mall and computes driving/walking/cycling routes. Confirm that the saved URL is genuinely public HTTPS. For a full frontend check, use a second device or mobile data; a local-only URL will not satisfy that test.

## Final live checklist
- [x] GitHub contains the intended commit and data bundle; no credentials are tracked.
- [x] Render deployment is successful on the Free plan.
- [x] The actual public HTTPS /health returns status=ok and the expected graph version/counts.
- [ ] /docs displays the contract and can execute POST /route.
- [x] The public smoke-test artifact records successful routes in all three modes.
- Not applicable: the live web app and API share a Render origin; Netlify is optional.
- [ ] Invalid or disconnected inputs show useful errors in the UI and API.
- [ ] Cold start is tested after idle and documented; no artificial keepalive loop is added.
- [ ] Deployed RAM and logs have been inspected; local memory numbers are not substituted.
- [ ] A second-device request succeeds without the development Mac serving it.
- [x] Actual URLs, deployed commit and timestamp are added to README/report.

## Three-line revision
Build the container, include the graph, bind the platform's port and verify the real HTTPS URL.
Netlify embeds the API address at build time; Render must allow the exact frontend origin.
Free hosting sleeps and has limits, so rehearse both a warm public demo and a local offline fallback.
