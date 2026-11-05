# Configuration and troubleshooting

Run native commands from the repository root. `make setup` copies `.env.example` to `.env` only when `.env` is absent. The API and database commands load `.env`; variables already present in the process environment take precedence. Restart the API after changing configuration. Keep real credentials in the ignored `.env` or deployment environment.

## Local catalog and retrieval

| Variable | Default | Purpose |
| --- | --- | --- |
| `NAVYLINK_DB` | `data/navylink.db` | SQLite path; parent directories are created as needed. |
| `NAVYLINK_FRONTEND` | `frontend/dist` | Built frontend directory, checked when the app starts. |
| `NAVYLINK_SEMANTIC_WEIGHT` | `0.55` | Hybrid semantic weight, from 0 to 1; keyword weight is its complement. |
| `NAVYLINK_MODEL_PATH` | Unset | Prepared local Sentence Transformers model; unset uses `bundled-concept-v1`. |
| `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` | `1` in `.env.example` | Offline flags for optional model dependencies. Model loading also explicitly uses local files only. |
| `NAVYLINK_DEMO_USERS` | Unset | JSON file adding or overriding demonstration identities. |

Use `make model` during online preparation to install optional semantic dependencies and save MiniLM under `data/models/all-MiniLM-L6-v2`. Set that path, run `make reindex`, and restart. Remove the setting and repeat reindex/restart to return to the bundled encoder. The base Docker image contains neither neural dependencies nor model weights.

`make seed` initializes an empty project catalog. `make sample` backs up SQLite and replaces projects, personnel, datasources, lookup rows, indexes, and saved workflow history with the sample CSVs. `make reset` replaces the catalog and history with the 56-project regression fixtures. Stop the API before either replacement; see [import and backup details](data/README.md#sample-catalog).

## SI Powered search and Librarian

These paths use the fixed server endpoint `https://api.openai.com/v1/responses` implemented in `openai_search.py` and `catalog_chat.py`. They do not use `NAVYLINK_LLM_BASE_URL` or `NAVYLINK_LLM_PROVIDER`.

| Variable | Behavior |
| --- | --- |
| `OPENAI_API_KEY` | Primary key for SI Powered reranking and Librarian. |
| `NAVYLINK_LLM_API_KEY` | Fallback when `OPENAI_API_KEY` is empty; this can enable OpenAI calls independently of the provider setting below. |
| `OPENAI_CHAT_MODEL` | Primary model setting; `.env.example` currently sets `gpt-6.1-terra`. |
| `OPENAI_MODEL` | Legacy fallback if `OPENAI_CHAT_MODEL` is empty; the code default is `gpt-6.1-terra`. |

Choose a model accessible to your account that supports the requests implemented by the project. The repository's configured name does not establish account access or model availability.

SI Powered (`GET /api/v1/search?mode=openai&q=…`) starts with up to 50 authorized, filtered hybrid matches. The request sends the query and bounded candidate IDs, names, missions, descriptions, domains, types, statuses, dataset names, and technologies. The response must rank every candidate ID exactly once. Only those candidates may appear in the final results. Requests set `store: false`; reranking uses JSON output, a 25-second timeout, and a 64 KB response-size check.

Librarian (`POST /api/v1/chat/catalog`) uses the same reranking when a key is available, then sends the top five project contexts, the current question, and bounded recent chat history for answer generation. Returned cards link to those projects. Ranking errors propagate to the interface. If answer generation fails, a local template answers from the already ranked projects. With both keys empty, no OpenAI request is made and Librarian uses local matching and answer templates.

The floating chat and full-page Librarian share in-memory conversation state. Changing identity or reloading the application clears that state. TXT, DOC, and PDF exports download the conversation text in the browser; they are separate from catalog export, which has no endpoint. Displayed reliability/usefulness values are local ranking or metadata heuristics and do not measure operational reliability.

## Optional constrained question API

`POST /api/v1/agent/discover` also accepts question input and supports a separate provider configuration. The current Librarian UI calls `/chat/catalog`, so these settings configure the question API rather than its chat transport. Proposal input always runs the local deterministic advisor.

| Variable | Default | Purpose |
| --- | --- | --- |
| `NAVYLINK_LLM_PROVIDER` | `none` | `none`, `openai` for an OpenAI-compatible endpoint, or `ollama`. |
| `NAVYLINK_LLM_BASE_URL` | Unset; Ollama defaults to `http://127.0.0.1:11434` if absent | OpenAI-compatible URL ending in `/v1`, or Ollama server root. Explicitly set it when enabling a provider. |
| `NAVYLINK_LLM_MODEL` | Unset | Model identifier at that endpoint. |
| `NAVYLINK_LLM_API_KEY` | Unset | Optional bearer credential; also a fallback key for SI Powered/Librarian as described above. |
| `NAVYLINK_LLM_TIMEOUT` | `5` | Generation timeout in seconds, clamped to 0.1–30. Does not control Librarian or SI Powered timeouts. |

The OpenAI-compatible adapter uses `/chat/completions`; Ollama uses `/api/chat`. Local validation accepts only retrieved project IDs, exact field quotes, and allowed next-step codes. Invalid output or an unavailable provider produces a deterministic fallback. A question request can set `generation: "deterministic"` to skip this generation path. See [provider examples and validation details](PHASE2.md).

For guaranteed local-only operation, leave **both** `OPENAI_API_KEY` and `NAVYLINK_LLM_API_KEY` empty and set `NAVYLINK_LLM_PROVIDER=none`. Offline model flags do not disable HTTP provider requests.

## Demo identities

Add or override identities with a file such as `data/demo-users.json`:

```json
[
  {
    "id": "reviewer",
    "label": "Demo reviewer",
    "internal": true,
    "groups": ["maintenance-demo"],
    "editor": false
  }
]
```

Set `NAVYLINK_DEMO_USERS=data/demo-users.json` and restart. The interface loads identity choices and edit permissions from the API. The `editor` role permits mutations only for records visible to that identity. These selectable identities are not authentication. All 500 sample projects are public; use regression fixtures for restricted-project demonstrations.

## Docker configuration

The image excludes `.env`. Compose reads the host `.env` for interpolation but forwards only variables declared in `compose.yaml`. The current file forwards the semantic weight and `NAVYLINK_LLM_*` provider settings; it does not forward `OPENAI_API_KEY` or `OPENAI_CHAT_MODEL`.

To configure SI Powered/Librarian explicitly, create `compose.override.yaml`:

```yaml
services:
  navylink:
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      OPENAI_CHAT_MODEL: ${OPENAI_CHAT_MODEL:-}
```

Keep real values in `.env`, then apply with `docker compose up -d`. Do not place literal credentials in a committed override. `NAVYLINK_LLM_API_KEY` remains a fallback for these features. A local provider's URL must be reachable from the container; container loopback refers to the container itself.

The image imports the sample database during build. A new `navylink-data` volume is initialized from the image's `/app/data`; an existing volume takes precedence and is preserved. Rebuilding the image does not replace its existing database. Use the explicit sample-import command in the [README](../README.md#docker-and-offline-packaging) when replacement is intended. Dev Containers use a separate volume and database path.

## Troubleshooting

| Symptom | Check / action |
| --- | --- |
| Homepage returns 404 but `/api/health` works | Run `make build`, then restart the API so it mounts `frontend/dist`. |
| Vite loads but API calls fail | Run `make dev-api` on port 8000. Vite's configured proxy targets that port. |
| Counts show 42 public projects rather than 500 | The regression catalog is loaded. Stop the API and run `make sample` if you intend to replace it. |
| Model load fails | Confirm optional dependencies and the prepared `NAVYLINK_MODEL_PATH`, or unset it and reindex for the bundled encoder. Runtime does not download missing weights. |
| SI Powered reports missing credentials | Set a server key, restart, and verify Compose forwarding when applicable. Local search modes require no key. |
| OpenAI returns 401/403/404/429 | Check key validity, model permissions/name, and account quota. The interface shows sanitized status diagnostics. |
| Librarian reports a ranking error | Its initial SI Powered rerank failed. Correct the provider issue or empty both key variables and restart for local matching. |
| Browser tests cannot launch Chromium | Run `cd frontend && npx playwright install chromium`. Devcontainer setup installs browser system dependencies as well. |
| A saved assessment expires | Records, contacts, permissions, or the response contract changed. Run the proposal again to regenerate current evidence. |
| A record is unavailable or cannot be edited | Check the demo identity. Hidden and nonexistent records both return 404; mutations require a visible record and curator permissions. |
