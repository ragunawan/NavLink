# Three-minute offline demonstration

Open with NavyLINK's motto: **Create once, discover everywhere, improve together.** Introduce the walkthrough as a way to find existing work, assess reuse and identify opportunities to contribute.

Start in the repository root. Before the event, run `make setup` on Python 3.12+ with Node 22+. Run `make reset` to replace demo records and run history, then `make run`. Open http://127.0.0.1:8000. Do not reset a catalog containing work you want to retain.

| Time | Action | Evidence to show |
| --- | --- | --- |
| 0:00–0:25 | Open Overview as Public visitor. | 42 public synthetic records across seven domains; counts come from SQLite. Curator can discover all 56. |
| 0:25–0:55 | Search “forecast equipment failures using maintenance work orders and supply inventory”. Switch among Hybrid, Keyword and Semantic. | Ranked real records, mode, timing and mission evidence. No probability claim. |
| 0:55–1:20 | Open Keel Prognostics. Scroll to related capabilities. | Fictional owner, approved POC, shared datasets, related initiatives and unknown reuse conditions. Reserved `.example` links are intentionally fictional. |
| 1:20–2:15 | Open Check before you build. Load Predictive maintenance and click Analyze Proposal. | Watch running/completed steps, inspect the Recommended path and source citations, then expand the five initial leads to see complementary work. Review Collaboration opportunities, approved POCs and access questions. The user decides. |
| 2:15–2:35 | Use Compare assessed projects in the assessment. Change one selection. | Side-by-side mission, datasets, technologies, access instructions and unresolved compatibility. Reload the run URL to reopen locally saved evidence. |
| 2:35–3:00 | Disable Wi-Fi / upstream networking while retaining loopback. Reload the app and repeat search. | Browser assets, API, database and vectors are all local. A local server must remain running. |

The predictive maintenance example fills the required Phase 2 scenario: “We plan to build an AI-powered predictive maintenance system that analyzes historical equipment failures and supply data to forecast maintenance needs.” The proposed name, audience and technology are optional. A mission problem or description is sufficient.

Second scenario: Check before you build → Financial management example → Analyze Proposal. Budget Compass and Fiscal Lantern are potential duplicates; Obligation Data Cooperative is a relevant dataset. Licensing, current access and integration remain owner-confirmed questions.

Optional follow-up: open Discovery assistant, choose “Are there any financial management dashboards?” and ask the catalog. Show exact catalog fields, local project citations, next steps, uncertainty and the “Deterministic · no LLM used” label. Ask for differences between Keel Prognostics and BearingWatch to show its comparison. The default does not require an LLM; unavailable configured providers also fall back.

Optional metadata demonstration: paste a fictional description into proposal or registry, click Suggest metadata, edit a suggestion, check “I reviewed these editable suggestions,” then apply it. No record is written by Suggest metadata. Editing the description makes the prior suggestions stale.

Permission demonstration: `/projects/maint-07` returns the same not-found response as an unknown record for Public visitor. Switch to Maintenance group to see the fictional Acoustic Health Kit. Switch back to remove it. An internal analyst cannot see group-only projects. Catalog curator is needed to create, edit or delete records.

The bundled baseline works without a model download. To demonstrate a neural encoder, prepare it online beforehand using `make model`, set `NAVYLINK_MODEL_PATH` in `.env`, run `make reindex`, and restart. Runtime loading uses local files only. Do not confuse disconnected operation with browser-only operation: this prototype requires the laptop's local server.
