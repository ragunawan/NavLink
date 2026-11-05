# Three-minute sample-catalog demonstration

Open with NavyLINK's motto: **Create once, discover everywhere, improve together.** Show how to discover existing work, assess reuse, and identify people and data that can help.

## Prepare

From the repository root, run `make setup` with Python 3.12+ and Node 22+. To match the README screenshots, stop the API and run `make sample`, then `make run`. The sample import backs up SQLite and replaces the catalog and workflow history; do not replace a catalog containing work you want to retain. See [sample import and restoration](data/README.md#sample-catalog).

For this local-only walkthrough, leave both `OPENAI_API_KEY` and `NAVYLINK_LLM_API_KEY` empty and set `NAVYLINK_LLM_PROVIDER=none` in `.env`, then restart. The bundled encoder needs no download. Open http://127.0.0.1:8000 as **Public visitor**.

## Walkthrough

| Time | Action | Evidence to show |
| --- | --- | --- |
| 0:00–0:25 | Open Home. | 500 fictional projects across eight mission domains and 16 organizations. Counts come from the authorized SQLite catalog. |
| 0:25–0:50 | Search `predictive maintenance`; filter to Maintenance in Catalog. Switch between Hybrid, Keyword, and Semantic. | Actual ranked records, mission evidence, filters, and relative ranking. SI Powered is optional and requires a configured OpenAI key. |
| 0:50–1:15 | Open Machinery Vibration Anomaly Detection or another matching project. | Mission, description, stated datasets, registered personnel, and related capabilities. Missing license, deployment, and integration details remain unknown. Use Compare on two project cards for a side-by-side view. |
| 1:15–2:10 | Open Prebuild, load Predictive maintenance, and click Analyze Proposal. Scroll to Discovery assessment. | Actual running/completed operations, Recommended path, source links, collaboration leads, and reuse checks. Expand beyond the first five leads or change the assessed comparison. Reload the saved run URL to reopen evidence. |
| 2:10–2:40 | Open Librarian and ask `List projects for predictive maintenance.` | Local catalog answer with project links. Scroll inside the answer panel to the cards. Open the floating Librarian to show the shared chat; export TXT, DOC, or PDF. |
| 2:40–3:00 | Open Registry, then switch from Personnel to Datasources. | 256 people and 214 datasources. Search a name, organization, expertise, or datasource; project detail metadata links to referenced registry entries. |

The Predictive maintenance example asks: “We plan to build an AI-powered predictive maintenance system that analyzes historical equipment failures and supply data to forecast maintenance needs.” Only a mission problem or description is required; the project name, intended users, technology, and other fields are optional. Recommendations are advisory leads, and the user decides whether to investigate reuse.

The sample catalog differs from the regression fixtures: it does not contain Keel Prognostics, Budget Compass, or Acoustic Health Kit. Do not use fixture-specific names in the sample walkthrough. Reserved `.example` resources and personnel contacts are fictional.

## Optional demonstrations

**Metadata suggestions:** paste a fictional description into Prebuild or project registration, click Suggest metadata, edit a suggestion, check “I reviewed these editable suggestions,” and apply. Suggestion generation does not save a record. Changing the description makes prior suggestions stale. Use Catalog curator to register or edit projects at `/projects/new`.

**Disconnected use:** with both API keys empty and no external generation provider selected, disable upstream networking while retaining loopback. Reload Home and repeat local search, Prebuild, and Librarian. The app still needs its local server; it is not a browser-only application.

**SI Powered and Librarian generation:** configure the server key/model in `.env` and restart before the demo. SI Powered reranks up to 50 authorized local matches. Librarian uses the same ranking and answers from the top five. This path needs provider connectivity; ranking failures appear as errors, while answer-generation failures retain ranked links with a local template. Review [configuration](CONFIGURATION.md) before enabling it.

**Neural retrieval:** prepare `make model` online, set `NAVYLINK_MODEL_PATH=data/models/all-MiniLM-L6-v2`, run `make reindex`, and restart. Runtime uses only local model files. This is separate from optional answer generation.

## Restricted-record demonstration

All sample projects are public. To demonstrate permission boundaries without replacing the sample database, start an isolated regression server in another terminal:

```sh
NAVYLINK_DB="$(mktemp -d)/navylink.db" NAVYLINK_MODEL_PATH= \
  OPENAI_API_KEY= NAVYLINK_LLM_API_KEY= NAVYLINK_LLM_PROVIDER=none \
  PYTHONPATH=backend .venv/bin/python -m uvicorn navylink.main:app \
  --host 127.0.0.1 --port 8013
```

Open http://127.0.0.1:8013. Public visitor sees 42 of 56 fixture projects. `/projects/maint-07` returns the same not-found view as an unknown ID. Select **Maintenance group** to see Acoustic Health Kit, then return to Public visitor to remove its evidence. Internal analyst cannot see group-only projects; Catalog curator can see all fixture projects and edit visible records. These selectable demo identities are not production authentication.

The fixture catalog also supports the original maintenance tour with Keel Prognostics and BearingWatch, and the financial proposal example with Budget Compass, Fiscal Lantern, and Obligation Data Cooperative. Stop the isolated server with Ctrl+C afterward.
