# Phase 8 — repository and version control

The published repository is [sourcestik/navic-MiniProject](https://github.com/sourcestik/navic-MiniProject). Use the setup steps below only for a new clone or a new project.

## What belongs in Git
Track project code, tests, direct dependency versions/lockfile, vendor notices, compressed graph, offline geometry, metadata and documentation. Do not track secrets, raw Overpass downloads, node_modules, compiled binaries, virtual environments or transient process logs. The compressed graph is about 20 MiB and below GitHub's per-file limit; its uncompressed counterpart is ignored.

## Create a local repository (if not already initialized)
```sh
git init -b main
git add backend frontend scripts tests data docs README.md LICENSE THIRD_PARTY_NOTICES.md CMakeLists.txt Dockerfile Procfile render.yaml netlify.toml requirements.txt requirements-report.txt pytest.ini .gitignore .dockerignore .env.example .github artifacts output
git diff --cached --stat
git commit -m "Build Navic C++ routing API and React map navigator"
```
If Git asks for identity, set your own real name/email using repository-local `git config user.name` and `git config user.email`. Do not invent another person's authorship. Review staged files before committing.

## Push to a new GitHub repository
Create an empty repository named `navic` in your own GitHub account, choosing visibility deliberately. Do not prepopulate it with a separate README/license if pushing this existing history. Copy its actual HTTPS clone URL, then run:
```sh
printf 'Paste the GitHub repository HTTPS URL: '
read -r NAVIC_REPO_URL
git remote add origin "$NAVIC_REPO_URL"
git push -u origin main
```
If origin already exists, inspect `git remote -v` and use the intended remote rather than adding a duplicate. Use GitHub's supported browser/credential-manager authentication flow; never put a token into a remote URL or a committed file. The connected GitHub integration can perform the equivalent publishing step once account access is confirmed.

## Meaningful future commits
| Change | Example commit message |
|---|---|
| Initial implementation | Build Navic C++ routing API and React map navigator |
| Snapping correction | Prefer shared road components when snapping place centroids |
| Algorithm verification | Compare Dijkstra and A* with an independent shortest-path oracle |
| Data refresh | Refresh bounded Delhi OSM snapshot and update provenance |
| Deployment configuration | Configure the verified public API origin for the frontend |
| Documentation | Record live deployment evidence and final viva results |

Do not create artificial historical commits claiming tests happened before they were actually written. A single complete initial commit is acceptable.

## Test the hosted workflow
After pushing, inspect the actual GitHub Actions run. It compiles on Ubuntu, unpacks data, runs C++/pytest checks and builds the frontend. A checked-in workflow is not evidence that CI has passed. Resolve any platform-specific failure before the final submission.

## Three-line revision
Git records local history; GitHub hosts the repository and CI.
Commit source, exact dependency/data versions and evidence, while ignoring secrets and generated bulk files.
Push the verified commit, inspect CI, then deploy that same source revision.
