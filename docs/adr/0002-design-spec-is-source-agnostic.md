# The design spec is source-agnostic

The design spec was defined as the document "extracted from the Figma frames" that a build reads from, and four skills read that definition. `shopify-page-replicate` builds from a rendered Source page instead of a design file, so the term now covers either source: a pair of Figma frames, or a Source page. Nothing else about the design spec changes — it is still the single authority a build reads from, still holds every measured value and the asset inventory, and is still the thing the style report asserts against.

## Why the existing skill was deleted rather than extended

`shopify-migrate-page-to-new-theme` already captured a live page. But it produced a document and a copy-paste handoff prompt rather than a build, and its central rule was to recreate the page in the *new* theme's design system — new colors, new fonts, old content. That is the opposite of what a Stand-in needs. Keeping it would have left two skills with overlapping triggers and opposing intent, so it was removed and its live-capture procedure was moved into the new skill.
