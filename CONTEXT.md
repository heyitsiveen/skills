# Skills

A Claude Code marketplace of agent skills, organised as bucket → domain → skill. The language below covers the Shopify theme-build skill suite in `personal/shopify/`, where most of the shared vocabulary lives.

## Language

### Building from a design

**Design spec**:
The single document, extracted from the design source, that a build reads from. Holds every measured value, the desktop/mobile differences, and the asset inventory. The design source is a pair of Figma frames, or a Source page.
_Avoid_: extraction, figma spec, exact-values table, visual specification

**Style report**:
The list of computed-style mismatches produced after a build, comparing the rendered page against the design spec. It is output, not judgment — it cannot fail a build.
_Avoid_: verification, gate, assertion pass, fidelity check

**Style reporter**:
The subagent that captures the rendered result, produces the style report, and writes the screenshots to disk. Returns text only, never images.
_Avoid_: visual-verifier

**Fidelity forecast**:
The up-front sorting of each design element into EXACT, APPROXIMATES, or UNACHIEVABLE, given only the sections the theme already ships. The style report is what proves it.

**Visual-check folder**:
`.agent/<skill-name>/visual-check/<name>/`. Holds the reference screenshots, the design spec, the rendered result screenshots, and the exported assets. Retained after a run for the user's own review.

**Hardcode-then-revert**:
Temporarily substituting real values for empty editor settings so the rendered result is representative, then removing them and proving the removal. Justified by the result screenshot being worth looking at.

**The split**:
A section or block renders a placeholder in the theme editor and nothing at all on the live storefront when its required settings are empty.

### Getting assets from a design

**Original source**:
The designer's uploaded picture, returned by `download_assets` as `rawImages` and never re-rendered. It keeps its alpha, sets the scale ceiling, and where the node shows the whole of it, it is itself the shipping file.
_Avoid_: raw image, source asset, uncropped export

**Crop**:
What the node shows when it shows less than the whole original source. A crop exists only where the fill renders above 100% in either axis, or the aspects differ by more than 2% — otherwise there is nothing to crop and the original source ships.
_Avoid_: cut, trim

**Scale ceiling**:
The largest export scale the original source's real resolution supports. Past it Figma interpolates, so a bigger number buys pixels and no detail.

**Transport format**:
A format a file passes through and is never delivered in. `export` is requested as PDF because its PNG and SVG carry the design's page fill behind the node; the PDF is rasterized and deleted. See `docs/adr/0005-export-ships-through-pdf.md`.

### Replicating a page

**Stand-in**:
A replicated page holding a template's place on the Target theme until a real design exists for it. Temporary by intent — a later build replaces it.

**Source page**:
The rendered page being copied, reached at a URL on the Source theme.
_Avoid_: live page, reference page, original

**Source theme**:
The theme the Source page is served from — the client's current theme.
_Avoid_: live theme, old theme

**Target theme**:
The theme the replication is built into — the client's revamped theme, on the same store.
_Avoid_: new theme, revamped theme

**Replicate**:
To rebuild a Source page on the Target theme so that it renders the same, using the Target theme's existing sections wherever they reach.
_Avoid_: copy, clone, port, migrate
