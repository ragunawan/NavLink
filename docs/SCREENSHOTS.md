# Screenshot capture

The [README](../README.md#screenshots) gallery was captured on **November 5, 2026** from the running application with the bundled `bundled-concept-v1` encoder, public visitor identity, and no API keys. It uses the **500-project, 256-person, 214-datasource sample catalog**, not the smaller regression fixtures. Screenshots show real API results; the capture does not mock responses or alter page styles.

| Asset | View |
| --- | --- |
| [dashboard.png](dashboard.png) | Full desktop homepage, live sample counts, and recent projects. |
| [catalog.png](catalog.png) | Hybrid search for `predictive maintenance`, filtered to Maintenance. |
| [project.png](project.png) | Sample project `NL-0001`, BSO Code and Funding Activity Crosswalk. |
| [phase2-proposal.png](phase2-proposal.png) | Prebuild form with the Predictive maintenance example loaded. |
| [advisor.png](advisor.png) | Completed assessment, recommended path, and evidence links. |
| [assistant.png](assistant.png) | Librarian local matching results, project links, and transcript export controls. The filename is retained for existing documentation links. |
| [registry.png](registry.png) | Personnel registry with the public sample records. |
| [mobile.png](mobile.png) | Full homepage at a 390 × 844 mobile viewport. |

Desktop captures use a **1440 × 1000** viewport and device scale factor 1. Homepage images include the full page; other captures show a viewport. Capture uses Chromium, US English, the America/New_York timezone, and reduced motion. Timing values can vary between runs.

## Reproduce safely

Install project dependencies first with `make setup`. Install Chromium during online preparation if needed:

```sh
cd frontend && npx playwright install chromium
```

From the repository root, open a dedicated terminal and prepare a temporary database. These environment overrides keep the real catalog and configured providers separate:

```sh
NAVYLINK_SCREENSHOT_DIR="$(mktemp -d)"
export NAVYLINK_DB="$NAVYLINK_SCREENSHOT_DIR/navylink.db"
export NAVYLINK_FRONTEND=frontend/dist
export NAVYLINK_MODEL_PATH= NAVYLINK_DEMO_USERS=
export OPENAI_API_KEY= NAVYLINK_LLM_API_KEY= NAVYLINK_LLM_PROVIDER=none
export NAVYLINK_SEMANTIC_WEIGHT=0.55
export PYTHONPATH=backend
make build
.venv/bin/python -m navylink.import_sample --replace
.venv/bin/python -m uvicorn navylink.main:app --host 127.0.0.1 --port 8014
```

Leave that server running. In a second terminal, from the repository root:

```sh
NAVYLINK_TEST_URL=http://127.0.0.1:8014 node docs/capture-screenshots.mjs
```

The script requires an explicit loopback URL, verifies the 500-project sample count, and writes only the eight images listed above. It runs one proposal assessment, which saves history in the isolated database, and asks Librarian one question. It requires Librarian's response to be local, checks completed UI states and mobile overflow, and rejects external browser requests or page errors. The server environment must disable provider keys as shown; browser request blocking does not block server-side HTTP calls.

Review the generated images before committing. Stop the isolated server with Ctrl+C afterward. The temporary database and its backup can then be discarded; do not run this replacement sequence against a catalog containing work you want to retain.

The existing regression browser tests also write `dashboard.png`, `mobile.png`, `advisor.png`, `assistant.png`, and `phase2-proposal.png`. Run this capture **after** those tests to keep the README screenshots aligned with the sample catalog.
