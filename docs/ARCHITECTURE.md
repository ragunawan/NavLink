# NavyLINK implementation plan

Local browser → React / Vite → FastAPI `/api/v1` → SQLAlchemy / SQLite.

1. Build the authorized catalog, synthetic seed command, CRUD, FTS5 index and persisted local vectors.
2. Connect dashboard, search, detail, related projects and registry forms to the real API.
3. Add explicit overlap rules, comparison and a persisted deterministic discovery workflow.
4. Exercise permission boundaries, retrieval evaluation, browser flows and offline packaging.

Project metadata is a validated document with normalized organization and domain tables. All retrieval starts with the authorized subset; vocabulary, vector scoring, counts and explanations use only that subset. POC visibility is a separate policy. Demo identity headers are intentionally not authentication; the server binds to loopback by default.

FTS5 provides lexical ranking. A bundled deterministic concept encoder maps mission synonyms to sparse concepts and hashes remaining terms into normalized vectors. This lightweight baseline needs no model download. An optional locally cached Sentence Transformers encoder can replace it; it never silently downloads at runtime. Reciprocal Rank Fusion combines lexical and semantic ranks. Similarity is relative ordering, never a probability or proof of duplication.

SQLite stores embeddings and agent run results. Metadata and vector updates commit together. Search has no cloud dependency or external action tool. Deployment to a real environment needs approved identity, authorization, handling and security controls. All bundled data is synthetic.

The Check Before You Build state machine streams NDJSON progress before and after actual operations. It merges hybrid and related-project findings, inspects a bounded set of records, evaluates constraints, compares candidates and synthesizes cited next steps. A shared iterator drives the streaming and complete-JSON endpoints. Typed citations preserve exact authorized record values; persisted assessments carry private scope/record fingerprints, which are revalidated before replay. See `AGENT.md` for the bounds and decision contract.
