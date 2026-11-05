# NavyLINK design system

Updated November 2026 at the user's request: navy-themed colors with an Apple-inspired interface. This replaces the previous Vantage direction. Existing routes, content, data, and workflows remain the foundation.

## Direction

Use a calm, readable interface: a pale blue-gray canvas, white surfaces, deep navy text and actions, and soft rounded corners. Keep the NavyLINK name and compass. The homepage adds cobalt blue and ocean teal accents, colored catalog totals, and a navy call to action. Keep supporting screens restrained. Avoid ornamental corner ticks, lime accents, and dark instrument-style surfaces.

Typography uses the platform system stack: `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, sans-serif. On Apple platforms this follows the native system face. Use weight 400 for body text, 500 for labels and controls, and 600 for headings and emphasis. Body is 17px, labels 14px, section headings about 24px, page headings 36px, and the desktop homepage wordmark 56px. Headings have restrained negative tracking.

## Tokens

`frontend/src/tokens.css` is the source of truth. Navy is `#0a2342`, with `#17365d` for hover and a muted `#3c6088` for supporting links. The canvas is `#f5f7fa`, panels white, and secondary surfaces `#eaf0f6`. Text uses navy, slate `#31455d`, and muted `#596b80`. Rules are quiet; editable fields use a stronger `#7d8a9b` edge so their boundaries remain visible. Error, warning, and success colors communicate actual states.

The spacing scale is 2, 4, 8, 12, 16, 24, 40, 64, 96, and 144px. The centered shell caps at 1360px with 40px desktop and 24/16px tablet/phone gutters. Columns use a 24px gap. Panel corners are 24px, input corners 12px, and action buttons pills. Shadows are subtle navy-tinted depth cues.

## Screen composition

Keep the existing top navigation and all twelve route patterns. The deep navy header has white navigation text, pale blue and teal accents, and a cobalt active tab. It remains visible while scrolling and collapses at 1190px, keeping demo identity selection available.

The homepage centers its introduction and working search, follows with three compact live catalog totals, and shows recent projects in three white panels with colored top edges on wide screens. Home cards use 16px padding, 20px corners, smaller metadata, and tighter gaps; project names and mission descriptions still wrap in full. Recent projects stack at 900px, and catalog totals stack at 600px. All three projects remain available at every viewport. Cobalt (`#205fc6`) and ocean teal (`#075b75`) have pale blue and sea-tinted supporting surfaces; their values live in `tokens.css`.

Catalog search and filters use rounded white surfaces. Results remain readable records with separate evidence and comparison actions. Detail screens pair capability information with contacts and access information. Registries use two columns of white records, stacking on phones; their tabs use a segmented treatment. Forms group related inputs within quiet white panels. Comparison tables scroll inside their own container.

## Controls and accessibility

Primary actions use navy pills with white text, 48px minimum height, and a darker navy hover. Secondary actions use transparent pills with a visible outline. Inputs use white wells and rounded corners. Focus rings appear instantly in blue, or pale blue within the navy header; checkbox and radio accents use navy. Homepage and catalog search inputs use a single continuous blue border on the combined search control when focused, without an additional outline around the inner input. Their buttons retain individual keyboard focus indicators.

Keep native disabled semantics, reduced opacity, a not-allowed cursor, loading states, explicit error text, and approved execution-state labels. Preserve visible labels, all accessible names, decorative icon semantics, the skip link, and mobile navigation Escape behavior. The homepage alone has a faded blue and teal dot background with two slow CSS transform animations. It is hidden from assistive technology, ignores pointer events, and stays outside the content flow. Reduced-motion settings stop the dots and loading spinner, leaving a still background. Other pages have no ambient animation.

## Preservation and maintenance

Preserve all catalog fields, URL search state, handler wiring, citations, permission boundaries, and demonstration/access disclaimers. Counts come from the authorized API view. No new imagery, claims, or metrics are needed. This update changes styling and typography; it introduces no external font request or new package dependency.

Implementation lives in `tokens.css`, `base.css`, `styles.css`, `homepage.css`, and `data-fields.css`. Current documentation screenshots reflect this design. `.hallmark/` records the earlier redesign and its historical Vantage audit; those audit counts do not describe this later style update.
