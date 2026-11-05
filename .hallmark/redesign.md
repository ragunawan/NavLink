# NavyLINK redesign record

Direction: full application redesign, Vantage by explicit user request. Review ran in-thread under the Codex harness. All twelve route patterns, catalog data, API calls and permissions remain.

## Material and system

The authorized catalog supplies all records and figures. No assets or claims were invented. Vantage contributes its steel colourway, blue-black surfaces, local Geologica variable font, light sharpened display type, lime actions and corner-tick figure frames. The original compass/wordmark keep their gold. The application uses its working catalog as the material; no picture slots are outstanding. The most useful future material would be owner-approved real project descriptions replacing demonstration text.

## Copy changes

- “Discover. Connect. Innovate.” → “Find what the fleet is building.” Gate 19: replace the generic triad using the existing catalog purpose.
- “EXPLORE THE SHARED CATALOG” → “Catalog” in the homepage section heading. Gate 54: promote the meaningful label.
- “CONNECTING NAVY INNOVATION” → “Connecting Navy innovation.” Gate 67: sentence-case supporting brand copy.
- “WHY IT MATCHES · RANK {rank}” → “Match evidence, rank {rank}.” Gates 63/67: readable evidence label.
- Middle-dot separators become commas in optional-field helper text, personnel choices/team metadata, timeline timing/status, retrieval provenance, collaboration metadata, and the LLM execution badge. Gate 63. The deterministic execution-state badge and the team group’s original accessible name remain intact.
- The five original assistant example questions remain visible verbatim. Each now has a concise “Use question” button retaining the original question as its accessible name and the original click handler. Gate 49a: avoid wrapped action labels on phones.
- Project type moves from the ornamental title opener into the detail metadata row. The updated date is now a semantic time element.
- All legal, demonstration and access disclaimers remain unchanged.

Redundant openers removed under gate 54; their meaningful headings remain:

- FOLLOW THE CONNECTIONS
- ASK THE SHARED CATALOG
- SOURCE-BOUND DISCOVERY
- ASSESS THE DIFFERENCES
- BUILD ON WHAT EXISTS
- 01 / MISSION NEED
- VISIBLE, BOUNDED, GROUNDED
- EVIDENCE, THEN ACTION
- {run.recommendation.decision.replaceAll('_',' ')}
- EXPLORE THE SHARED CATALOG
- PEOPLE & DATA
- CONTRIBUTE A CAPABILITY
- A CONNECTED FLEET STARTS HERE
- KNOWLEDGE WORTH SHARING
- CREATE ONCE. IMPROVE TOGETHER.

- THE SHARED CATALOG

- EVALUATE THE OVERLAP

- PROJECT REGISTRY

## Review

First word: fix. Resolved field-edge contrast, narrow-screen controls, metadata alignment, heading order, uneven example-link wrapping, and the inherited Tailwind outline on secondary buttons. Final judgment: the Vantage system carries across search, records, forms and workflows. No point cloud is appropriate to this catalog material.

The old homepage showed three small recent cards beside one another. The new full-width rows use more vertical space to keep mission text readable and distinguish comparison actions. All three recent projects remain available at every tested viewport.

Protected while fixing: full record names, all fields and actions, native form semantics, explicit execution states, citations, data and access boundaries.

## Evidence

The final lint summaries and preservation counts are recorded in log.json. Local screenshots and the before/after viewer are generated in .hallmark/compare.html. Raw images and lint reports are ignored by git. The browser suite’s documentation screenshots are updated with Vantage.

Final result: make test passed (94 backend tests and production build); browser regression 20 passed, sample browser checks 2 passed separately. Core and additional route audits both report 0 Floor failures, 0 open Reflex findings and 0 warnings. One Reflex exception (49b) covers wrapped full record titles. The 55 captures cover eleven screens. Preservation: links 73/73, fields 14/14, handlers 82/82, figures 60/60; one homepage heading reworded on record.
