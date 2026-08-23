# Skills

A Claude Code marketplace of agent skills, organised as bucket → domain → skill. The language below covers the Figma-to-Shopify skill suite in `personal/shopify/`, where most of the shared vocabulary lives.

## Language

### Building from Figma

**Design spec**:
The single document, extracted from the Figma frames, that a build reads from. Holds every measured value, the desktop/mobile differences, and the asset inventory. Lives at `figma-spec.md`.
_Avoid_: extraction, figma spec, exact-values table, visual specification

**Style report**:
The list of computed-style mismatches produced after a build, comparing the rendered page against the design spec. It is output, not judgment — it cannot fail a build.
_Avoid_: verification, gate, assertion pass, fidelity check

**Style reporter**:
The subagent that captures the rendered result, produces the style report, and writes the screenshots to disk. Returns text only, never images.
_Avoid_: visual-verifier

**Fidelity forecast**:
The composer's up-front sorting of each design element into EXACT, APPROXIMATES, or UNACHIEVABLE, given that it may only reuse what the theme already ships. The style report is what proves it.

**Visual-check folder**:
`.agent/<skill-name>/visual-check/<name>/`. Holds the Figma reference screenshots, the design spec, the rendered result screenshots, and the exported assets. Retained after a run for the user's own review.

**Hardcode-then-revert**:
Temporarily substituting real values for empty editor settings so the rendered result is representative, then removing them and proving the removal. Justified by the result screenshot being worth looking at.

**The split**:
A section or block renders a placeholder in the theme editor and nothing at all on the live storefront when its required settings are empty.
