# Phase 2 observed evaluation

Reports are actual runs of `PYTHONPATH=backend .venv/bin/python -m navylink.evaluate`, each using a separate temporary database with 56 synthetic records. Full labels, returned project IDs, predictions, decisions and pair outcomes are retained in `evaluation.json` and `evaluation-neural.json`.

Host: **MacBookPro18,3**, ARM64, 8 logical cores, **16 GiB RAM**, macOS 27.2, Python 3.14.10, Node 26.13.0. Hardware was read during local setup. The base image targets Python 3.12; native Python 3.14 was tested. Installed Python versions are captured in `python-environment.txt`; frontend packages resolve through `frontend/package-lock.json`.

## Results

| Measurement | Bundled baseline | MiniLM |
| --- | ---: | ---: |
| Labeled search queries | 15 | 15 |
| Near-duplicate proposals | 5 | 5 |
| Complementary/nonduplicate proposals | 5 | 5 |
| Precision@5 | 0.3733 | 0.3867 |
| Recall@5 | 0.9556 | 0.9778 |
| MRR | 0.9667 | 1.0 |
| Duplicate precision | 1.0 | 1.0 |
| Duplicate recall | 1.0 | 1.0 |
| Complementary lead recall | 1.0 | 1.0 |
| Workflow success rate | 1.0 | 1.0 |
| Citation instances checked | 902 | 916 |
| Valid citation instances | 902 | 916 |
| Candidates with eight reuse checks | 45 | 46 |
| Average search latency (ms) | 2.21 | 8.23 |
| Median search latency (ms) | 2.08 | 8.14 |
| Maximum search latency (ms) | 4.64 | 9.82 |
| Median workflow latency (ms) | 24.59 | 49.99 |
| Maximum workflow latency (ms) | 27.21 | 54.47 |
| App creation, model load if applicable, seed (ms) | 74.22 | 5020.19 |
| Peak Python RSS (MiB) | 102.12 | 554.09 |

Both encoders found all **12 labeled duplicate relationships** (12 true positives, zero false positives, zero false negatives) in five near-duplicate proposals. Five additional proposals cover complementary datasets and unrelated missions. All labeled complementary leads were retrieved. All 10 known similar pairs appeared in related top 6; none of the 10 unrelated pairs did. Six benchmark permission checks passed for each encoder.

Citation counts are instances, including repeated references. Each is checked against the actual authorized project's API field value, name, ID and local URL. Every candidate included licensing, access, deployment, integration, datasets, support, technology and contact checks. Missing metadata is explicitly unknown; no permission or compatibility is assumed.

## Verification

- **58 backend tests passed** in bundled mode in **5.69 seconds**.
- The same **58 tests passed with cached MiniLM and offline flags** in **55.07 seconds**.
- TypeScript checking and the Vite production build passed.
- Provider tests validate actual HTTP client protocol handling with in-process OpenAI-compatible and Ollama transport fixtures. They use retrieved database records and reject unsupported IDs, fields, quotes, prose, action codes, hidden contacts and invalid responses; unreachable generation falls back. No live generative model inference was performed.
- Ten Chromium journeys passed against the final build and a fresh temporary demo database in **10.5 seconds**. They cover the exact Phase 2 maintenance example, description-only input, reviewed/stale Auto-Tag, real citations, collaboration, selected comparisons, saved runs, RAG question answers, RAG comparison, identity changes, registry CRUD, failures and local discovery with external HTTP denied.
- Final real HTTP smoke tests on loopback returned 200 for the required proposal (eight assessed candidates), 200 for financial-dashboard RAG fallback (sources `fin-01`, `fin-02`), and 404 for a comparison containing an unauthorized project. These calls used the requested `/api` aliases, not in-process transport.

Backend tests include socket-denied discovery and question answering, hidden-record independence, current contact/group revocation, typed proposal validation, real progress before operations, cancellation/failure, missing metadata and common API aliases. The evaluation regression runs the full labeled harness twice and checks repeatable rankings, proposal predictions and pair outcomes.

## Interpretation and limits

The evaluation uses manually labeled synthetic fixtures, and those fixtures have informed rule development. Perfect duplicate and citation metrics are **regression evidence, not independent operational accuracy**. The next evaluation should use independently labeled, more varied mission descriptions and missing/contradictory metadata.

Precision@5 divides by five even if a query has fewer than five labeled relevant records. Many queries have one relevant record, explaining the lower precision alongside high recall and MRR. Per-query non-relevant results remain in the reports.

Latency measurements use an **in-process API test client**, not real HTTP or browser time. Search time includes authorized filtering, ephemeral FTS indexing and local vector ranking, but excludes response serialization. Workflow time includes API response creation. Startup includes app/schema/seed creation after core imports; neural startup also imports the transformer stack and loads weights. It is not OS process startup. Peak RSS is a high-water mark rather than idle usage. Cached neural weights occupy approximately 87 MiB, excluding dependencies and download cache.

LLM generation quality, latency and external provider availability are unmeasured. Core workflows and fallback remain offline; an unavailable configured provider uses a bounded timeout before fallback. No container deployment, physical disconnected-device test, power/thermal measurement or edge certification is claimed. Docker is unavailable on this host. Network isolation tests preserve loopback while blocking outbound sockets or external browser HTTP.

## Reproduce

```sh
NAVYLINK_MODEL_PATH= PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
NAVYLINK_MODEL_PATH= PYTHONPATH=backend .venv/bin/python -m navylink.evaluate
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  NAVYLINK_MODEL_PATH=data/models/all-MiniLM-L6-v2 \
  PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  NAVYLINK_MODEL_PATH=data/models/all-MiniLM-L6-v2 \
  PYTHONPATH=backend .venv/bin/python -m navylink.evaluate --output docs/evaluation-neural.json
npm --prefix frontend run build
# With make run active:
npm --prefix frontend test
# Or set NAVYLINK_TEST_URL=http://127.0.0.1:8011 for an isolated server.
```

Screenshots: `dashboard.png`, `advisor.png`, `phase2-proposal.png`, `assistant.png`, and `mobile.png`. Browser evidence and evaluation reports use only synthetic data.
