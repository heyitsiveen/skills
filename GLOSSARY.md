# Skills

A Claude Code marketplace of agent skills, organised as bucket → domain → skill. The language below covers the skills in `personal/shopify/`, where most of the shared vocabulary lives — the theme-build suite first, then the sheet-to-metafields work, which shares none of its vocabulary and needed its own.

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

### Pushing sheet data into metafields

**Run**:
One execution of `sheet-to-shopify-metafields`: one Source sheet, one store, one Mapping. A Run is the unit a Backup covers and the unit an Undo restores.

**Source sheet**:
The Google Sheet a Run reads its new values from. Read-only to the skill — never written to, not even to add a tab.
_Avoid_: the spreadsheet, the doc, the source of truth

**Mapping**:
The column → metafield correspondence a Run is given. Supplied per Run, never inferred: a column header and a metafield display name may differ (`Details (HTML)` → `Revamp Details`), and a metafield key may not follow its own naming convention (`Revamp Product Benefits` → `custom.product_benefits`).
_Avoid_: the schema, the config, the column map

**Pre-flight**:
The audit a Run performs before it writes anything: real headers, true row count, empty mapped cells, duplicate handles, every HTML tag present in the source columns, and the contents of any notes column — including one the Mapping was told to ignore. Ignoring a column means not mapping it, not that its contents are irrelevant to whether the Run is safe.
_Avoid_: validation, the dry run, the check

**Converted value**:
What the converter produces for one cell: a rich-text HTML fragment and its plain-text twin, or the ordered values of a list metafield. Produced before the browser is touched, and inspectable on screen before any write.
_Avoid_: the payload, the output, the transformed cell

**Welding**:
The failure this design exists to prevent. Pasting a definition list into Shopify's rich-text metafield editor discards `<dl>`, `<dt>` and `<dd>` **and the whitespace around them**, concatenating every term to its value with no separator — `Best forEspressoOrigins…`. It saves without error and reads correctly in the admin's collapsed preview. Only the storefront shows it, and the pairing cannot be recovered.

**Backup**:
The prior values of every metafield a Run will write, captured before the first write, in a form that can restore them. A record that can only be read is not a Backup.
_Avoid_: the snapshot, the export, the safety copy

**Undo**:
Restoring a Run's prior values from its Backup. Because clearing a metafield in the admin deletes the record rather than storing an empty one, an Undo can restore *absent* as absent.
_Avoid_: revert (taken by Hardcode-then-revert), rollback, restore

**Matrixify mode**:
The path a Run takes when the store has Matrixify. One export is the Backup; one import is the write. No editor, no clipboard, none of Browser mode's hazards.

**Browser mode**:
The path a Run takes without Matrixify. The Backup and the write both go through the admin's bulk editor, fifty products at a time, saving every twenty.
