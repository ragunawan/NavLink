# Phase 2 implementation

The existing React, FastAPI, SQLAlchemy and SQLite architecture is preserved. The registry, FTS5, local encoders, RRF retrieval, streamed advisor, related projects, comparison and authorization already existed. This phase extends those components and adds a separate retrieval/generation path for questions.

**Current interface:** the navigation labels this proposal workflow **Prebuild** and the catalog chat **Librarian**. Librarian at `/librarian` (also `/assistant`) now calls `/api/v1/chat/catalog`, using local templates or optional SI Powered reranking and OpenAI generation. The constrained RAG behavior and `NAVYLINK_LLM_*` provider setup below describe question input to `/api/v1/agent/discover`, which remains available as an API. See [current configuration](CONFIGURATION.md) for the distinction and shared-key fallback.

## Completed

- Full proposal contract: proposed name, mission problem or description, domain, intended users, datasets, technology and desired capabilities. Mission/description validation is server-side. Description-only and mission-only requests work.
- Ranked actual candidates with source citations, matched terms/concepts, shared datasets/technologies/users, domain/status components and explicit differences. Relative scores are evidence indicators, not probabilities. Four advisory relationship labels supplement dataset/collaboration/history lead roles.
- Related-project ranking uses mission retrieval, datasets, domains, technologies and stated use cases. Comparison includes descriptions, audiences, highlighted identical attributes, differences, access constraints and explicit collaborator-seeking status.
- Collaboration section prioritizes Seeking Collaborators and shows owning organizations, approved contact methods, mission opportunities and open questions. It sends no messages or access requests.
- RAG assistant with authorized hybrid retrieval, stable-ID context, separate generation, locally validated source/field/quote references, structured fallback, source cards, optional two-project comparison and an execution summary.
- Editable Suggest metadata in registry and proposal forms with review confirmation. Dataset names come from explicitly mentioned authorized names or explicitly quoted names in the user's text; unknown owners, status and contacts are never generated. Changed input invalidates the prior suggestion review.
- Offline operation with the bundled encoder or cached MiniLM, outbound-socket/browser-network tests, synthetic evaluation, and updated demo instructions.

## RAG behavior

`POST /api/v1/agent/discover` accepts either a proposal or `{"question":"…"}`. A question can also include `generation: "deterministic"`, structured domain/type/status/organization filters, or up to two explicit project IDs. The default `auto` generation uses the configured provider when available. Explicitly named/selected authorized projects can supply a two-project comparison.

The response includes `answer`, catalog `facts`, field-level `citations`, `referenced_project_ids`, up to five `retrieved_projects`, advisory `recommendations`, `uncertainty`, `execution_steps`, `generation_mode`, and optional comparison. Question answers are returned per request; proposal assessments retain their persisted run workflow. Librarian has its own response contract and browser session state.

The `/api/discovery/check-duplicate`, `/api/projects/{id}/related`, `/api/projects/compare` and `/api/agent/discover` aliases use the same policies as their canonical `/api/v1` routes. OpenAPI documents the canonical versions.

Retrieval applies authorization before lexical indexing and semantic ranking. The context contains only allowlisted authorized fields and contact-redacted values. Descriptions and questions are untrusted JSON data inside a single user message, with system instructions rejecting embedded instructions. No metadata can choose a provider URL, credentials or external action.

To avoid unverifiable factual prose, generation is intentionally **extractive and constrained**. The model returns exact field quotes and selected next-step codes. Local validation checks every project ID against the retrieved set, every field against the context, every quote for exact equality, and every action against a bounded enum. Invented POCs, permission claims, changed quotes, unknown IDs, extra prose, unsupported action codes and contact actions without an approved POC are rejected. A failed validation or provider call produces a deterministic answer. Accepted facts remain labeled catalog fields; next steps remain advisory.

## Optional provider configuration

No model or provider is required. The default is `NAVYLINK_LLM_PROVIDER=none`; this makes no generation network call. Configure these server-side in `.env`, then restart:

```dotenv
# Approved OpenAI-compatible endpoint:
NAVYLINK_LLM_PROVIDER=openai
NAVYLINK_LLM_BASE_URL=https://approved-endpoint.example/v1
NAVYLINK_LLM_MODEL=your-approved-model-name
NAVYLINK_LLM_API_KEY=your-key-if-required
NAVYLINK_LLM_TIMEOUT=5
```

The compatibility path uses `/chat/completions`, JSON mode and local schema validation. JSON mode alone does not guarantee schema conformance; see the [official OpenAI structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat).

For an already prepared local Ollama server:

```dotenv
NAVYLINK_LLM_PROVIDER=ollama
NAVYLINK_LLM_BASE_URL=http://127.0.0.1:11434
NAVYLINK_LLM_MODEL=your-locally-installed-model
NAVYLINK_LLM_TIMEOUT=5
```

Ollama uses `/api/chat`, nonstreaming generation and a JSON schema in `format`, following the [official Ollama chat API](https://docs.ollama.com/api/chat). NavyLINK does not install or download an Ollama model. Prepare it before disconnecting. Both providers have bounded response sizes, no redirect following, no retries and a configurable timeout capped at 30 seconds. Credentials stay on the server and are not returned in error messages. Configure a base URL reachable from the deployment environment; container loopback is the container, not the host's model server.

These provider settings apply to question input on `/api/v1/agent/discover`. Proposal retrieval, classification, ranking, comparison and recommendations stay deterministic. If a configured provider becomes unreachable offline, this question API automatically falls back. Set `generation: "deterministic"` in a question request to skip generation even when a provider is configured. Librarian uses the separate key/model configuration documented in [CONFIGURATION.md](CONFIGURATION.md#si-powered-search-and-librarian).

## Verification and remaining limits

Provider integration is tested through actual HTTP client request/response handling with in-process transport fixtures for OpenAI-compatible and Ollama protocols. These tests use retrieved database evidence, exercise error cases and validate all accepted claims. Fixture results do not establish live provider quality or latency. The November 5 documentation capture used local matching with provider keys disabled.

The default encoder and ontology remain small. Dataset and audience overlaps use exact names; intent, negation and complex compatibility require human review. Scope/record fingerprints expire old saved proposal evidence, and all API responses are noncacheable across identities. Demo roles remain non-production authentication.

The constrained question API intentionally limits generation to validated evidence selection; the separate Librarian path supports catalog-grounded prose. A relationship graph, synchronization, and production identity integration are deferred. Docker/Compose files are maintained; container deployment was not exercised during this documentation refresh. See `EVALUATION.md` for observed native results and limitations.
