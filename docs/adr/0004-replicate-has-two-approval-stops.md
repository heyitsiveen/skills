# Replicate has two approval stops

`figma-shopify-builder`, `figma-shopify-composer` and `shopify-app-restyle` each state that their plan phase is "the run's ONLY stop". `shopify-page-replicate` has two, and the deviation is deliberate.

Stop 1, in Phase 2, approves the design spec, the section-by-section routing, the fidelity forecast, and the list of sections the run will remove from the target template. Stop 2, at the head of Phase 3, approves the design of the replica sections — and fires only when stop 1 chose to build at least one, which is the uncommon case.

One stop would mean a single plan covering a whole page's composition *and* the full design of new section code. The composer's plan for one section already runs to a dozen dense bullets; the page-scale version is long enough that nobody reads it, and an unread approval is not an approval. The two stops also ask genuinely different questions: is this the right plan, then is this the right code.
