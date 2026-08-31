---
name: figma-shopify-composer
description: Compose a pixel-accurate recreation of a Figma design from a theme's EXISTING sections, blocks, and settings — assemble and configure what the theme already ships, writing template JSON only: no new code, no new files, no new settings, no schema edits. Use when the user wants a Figma frame recreated by reusing existing sections or blocks, or asks to compose/assemble a design from existing settings only. Building a NEW section or block file from Figma is figma-shopify-builder's job — this skill only configures what already exists. The composition reads from a design spec extracted from the Figma frames, reports computed styles against it and against the plan's fidelity forecast, and saves the rendered result for review.
---

# Figma → Shopify Composer

Recreate two Figma frames by composing the theme's existing sections, blocks, and settings — configuration, not code — working from a design spec extracted from those frames. The palette is fixed to what the theme already ships, so fidelity is forecast before anything is built and the style report reads every mismatch back against that forecast. Four phases — research (read-only on the theme), plan (stop for approval), implement (template JSON only), render and report — then cleanup that leaves the machine as found. Nothing is created or modified before plan approval except knowledge docs under `.agent/` (§Knowledge docs) and the revert of a hardcode a previous session stranded (§Phase 1); the deliberate leftovers are the visual-check folder and the knowledge docs.

## Inputs

Collect all five before starting; ask for any that are missing.

1. **Figma desktop link** — with node-id.
2. **Figma mobile link** — with node-id.
3. **Composition type** — `section` or `block`. Section: compose one or more instances of existing section types in the template. Block: add instance(s) of existing block types into an existing section instance — ask which section instance if ambiguous.
4. **Target template** — e.g. `templates/index.json`, `templates/product.json`.
5. **Placement** — after X / before X / first in `order`, by customizer label or section type. For a block: which section instance and its position in `block_order`.

There is deliberately no data-source input: content is entered as values of the existing sections' and blocks' own settings, matching the Figma copy — never prompt for one.

## The build surface

The composition is configuration, not code:

- NO new theme files, NO new settings, NO schema edits. Existing section/block Liquid, CSS, and JS files are READ-ONLY.
- The only writable surfaces: the target template JSON; an approved `config/settings_data.json` value change (if any); the `.git/info/exclude` line for `.agent/`; `.claude/launch.json` if planned; and the `.agent/` tree itself — knowledge docs plus `.agent/figma-shopify-composer/visual-check/`.
- The one exception is transient: the render's `vh-tmp-` assets, which live in the theme's `assets/` only between the hardcode and its revert (§Hardcode-then-revert). The build surface is what SURVIVES the run.
- Prefer settings that inherit from global theme settings (colors, typography, radius, borders, buttons) over per-instance raw values — the result stays wired into the theme's design system.

## The design spec is the authority

`figma-spec.md` — the **design spec** — is the single document the composition reads from. Every value configured into the template traces to it: the exact-values table, the desktop/mobile differences, the layout intent, the stacking and overlap, the group rhythm, the requirements list, and the asset inventory. It is extracted once, in Phase 1, approved inline at the plan stop, and never re-derived mid-run; a value that is not in it is an OPEN QUESTION, not a judgement call.

The palette is fixed to existing capabilities, so the plan states upfront what will match EXACTLY, what APPROXIMATES, and what is UNACHIEVABLE without new code; the user approves that **fidelity forecast** before anything is written.

Pixel accuracy is still the goal. It is no longer a claim the skill makes on its own behalf: the run ends with a **style report** — computed styles against the design spec's values, each mismatch reconciled against the forecast — plus the rendered result saved to the visual-check folder next to the Figma references, and the user judges the result by eye.

## Browser tiers

**Primary: the Claude Code Desktop Browser pane** (desktop app with Browser enabled). Claude drives it directly — screenshots, DOM/computed-style inspection, interaction — and manages the dev server via `.claude/launch.json` (local dev servers need no site approval; preview/live store URLs are external sites and trigger a one-time permission card — Allow once / Always allow). When available, it does the whole capture job.

**Fallbacks, in order:** connected browser MCP (Chrome DevTools MCP / Playwright MCP) → installed Chrome → temporary Playwright via npx.

## Delegation

Bounded research and measurement go to subagents — isolated workers with their own context windows that return only a final report. Delegation earns its keep most in the capability inventory: scanning every section's schema would otherwise flood the main conversation. Delegation multiplies tokens: skip it for trivially small reads.

Prefer the named custom agents `figma-extractor`, `theme-scanner`, and `style-reporter` when installed in `~/.claude/agents/` or `.claude/agents/` — their definitions add tool-enforced restrictions (e.g. `disallowedTools: Write, Edit` on the style reporter). Otherwise run the built-in general-purpose subagent with the embedded prompts below; in that fallback the no-theme-edits rule is instruction-enforced, so each prompt states it explicitly.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the Figma MCP / browser tools reach subagents (subagents inherit internal + MCP tools by default; the Browser pane's preview tools may be main-session-only). Any role whose tools don't reach a subagent runs in the main conversation instead.

**Handoff protocol:** subagents can't see the conversation and can't ask the user questions — every delegation prompt carries its exact inputs (node-ids, file paths, the design spec's path, the approved fidelity forecast, capture specs); every worker writes FULL findings to a report file in the temp working directory (the capability scanner writes its knowledge doc instead, and the two reuse scanners write the shards the main agent merges into theirs — §Knowledge docs) and returns a short summary; ambiguities come back as OPEN QUESTIONS for the main agent to put to the user. The temp working directory is created per run (use the session scratchpad when available) and is deleted at cleanup.

**Never delegated:** the requirements-to-capabilities matching (1c — the synthesis that feeds the fidelity forecast), planning and every user approval (the design spec, the forecast, global-value changes), all implementation edits, and the correction round that follows the style report.

| Role | Phase | Report |
|---|---|---|
| figma-extractor | 1a, parallel | `figma-spec.md` — the design spec |
| theme-scanner — capability catalog | 1b, parallel | `.agent/THEME-CAPABILITIES.md` (canonical; shards `{temp-dir}/THEME-CAPABILITIES-<n>.md`, merged into it by the main agent) |
| theme-scanner — reuse inventory, JavaScript side | 1b, parallel | `{temp-dir}/COMPONENTS-<n>.md` |
| theme-scanner — reuse inventory, Liquid/CSS side | 1b, parallel | `{temp-dir}/COMPONENTS-<n>.md` (every side's report merged into `.agent/COMPONENTS.md` by the main agent) |
| style-reporter (never edits theme files) | 4, once per breakpoint, plus the correction round's re-check | `style-report-<breakpoint>.md` |

All three scanners are read-only on the theme, and each dispatches only when its doc is absent or stale (§Knowledge docs). The two reuse scanners share one doc, so they stand or dispatch together — except in INCREMENTAL, where a side whose tree holds no changed entry stands down and its half of the doc is kept byte-for-byte, its rows and its share of the header's counts carried into the merge so the gate still measures the whole theme.

### figma-extractor prompt

```
You are extracting a Figma design spec for a Shopify composition task — the
design will be recreated from the theme's EXISTING sections and settings, so
every value must be exact. Work only from the Figma MCP; do not read or modify
the theme repo.

Frames:
- Desktop: {figma-desktop-link} (node-id {desktop-node-id})
- Mobile: {figma-mobile-link} (node-id {mobile-node-id})

This document is the DESIGN SPEC: the single authority the composition reads
from. Nothing is re-derived from Figma later, so anything the composition needs
must be in it — and anything you are unsure of is an OPEN QUESTION, never a
guess.

For each node-id call get_design_context and get_screenshot, then compile:
1. Exact-values table per breakpoint: typography (family, size, weight,
   line-height, letter-spacing), colors, spacing (padding/margin/gap), sizes,
   border-radii, borders, image dimensions, frame width. These are the
   settings-configuration targets AND the expected values for computed-style
   assertions — record exactly.
2. Layout structure per breakpoint and every desktop vs mobile difference
   (column counts, stacking, order, visibility, alignment — e.g. 2 columns on
   desktop → 1 column on mobile).
3. Layout intent, per breakpoint: which elements form a row, a grid or a stack,
   the group each belongs to, and how that grouping changes between desktop and
   mobile (a desktop 3-up row becoming a mobile stack, and in what order).
4. Stacking and overlap: z-order wherever elements sit over one another, which
   element is on top, and the offset and overlap amount of each overlapping pair.
5. Group rhythm: the spacing BETWEEN sibling groups, per breakpoint — not only
   per-element margins. Give the gap between each pair of adjacent groups and
   name the repeating interval where one exists.
6. Asset inventory — one row per exportable asset: layer name | node-id |
   kind (raster fill / vector / composition) | the node's w×h | for a raster
   fill, the fill's rendered percentage of its node (the `w-`/`h-` values
   get_design_context emits) and the largest `rawImages` entry's own w×h |
   needs-transparency | whether the subtree holds text. Phase 3 exports from
   the node-id, so every asset carries its own; text in the subtree is an
   OPEN QUESTION, since exporting flattens it. The source's w×h is what
   separates a cropped row from an uncropped one and what caps the scale, so
   a raster-fill row without it cannot be exported. Needs-transparency is
   measured, not judged: a raster fill needs it when its largest `rawImages`
   entry carries sub-opaque pixels, a vector always does, and a composition's
   is read from the design. It is what the export phase's Alpha check
   asserts against.
7. The REQUIREMENTS LIST — the distilled design: layout structure per
   breakpoint; each content element (headings, text, CTAs/buttons, images,
   badges); each style requirement (colors, typography, radius, borders,
   spacing, alignment).

Sections 3, 4 and 5 are WRITTEN FROM THE SCREENSHOT — read the image, describe
what the composition actually does — and EVERY claim in them is backed by a
value from get_design_context, cited inline (the layout mode, the item spacing,
the absolute position, the bounds). A claim you cannot back with a value is an
OPEN QUESTION, not an assertion. The screenshot is the source of the structure;
the design context is the source of the numbers.

Open the document with this header line, verbatim, before section 1:

    producer: figma-shopify-composer — write surface: template JSON only —
    no new code, no new files, no new settings, no schema edits

Write the FULL findings to {temp-dir}/figma-spec.md with an OPEN QUESTIONS
section at the end for anything ambiguous. Return only a 3–5 line summary plus
the open questions.
```

### theme-scanner prompts — one per doc

Each opens with the absolute path of its format spec and the same instruction: **read that spec in full before writing a byte of the doc, and reproduce the block it gives.** The doc's shape, its row schemas, and the sources to sweep are the spec's; the prompt carries the run.

**Capability catalog:**

```
You are cataloging what a Shopify theme's existing sections, blocks, and
settings can already do. A Figma design will be recreated from those
capabilities alone — no new code — so what you catalog decides what is
achievable. READ-ONLY on the theme: your only write is the doc named below.

Format spec: {skill-dir}/references/theme-capabilities-format.md
Read it in full before writing a byte of the doc, and reproduce the block it
gives. Every fact a row carries is the spec's §Row schemas.

Theme repo: {repo-path}
Header `skill:` field: figma-shopify-composer (theme-scanner — capability
catalog)
Read: config/settings_schema.json · every `.liquid` file in sections/ and
blocks/ · section-group JSON for §Conventions · templates/**/*.json ·
layout/theme.liquid, the CSS-variable snippet and the theme's stylesheets ·
every section that reads a metafield or metaobject
Write to: .agent/THEME-CAPABILITIES.md
Mode: {FULL | INCREMENTAL — refresh only these entries: {list}}
Scope: {whole theme | shard {n} of {total} — {file range}, written to
{temp-dir}/THEME-CAPABILITIES-{n}.md instead, holding your sections only —
the main agent assembles the merged header from every shard's counts}

PER-RUN — return in your summary, never in the doc:
1. The placement anchor for "{placement}" in {template-path}'s `order` — or,
   for a block composition, the host section instance and its `block_order`
   position. OPEN QUESTION if ambiguous.
2. Whether .git/info/exclude carries a `.agent/` line.

Return only a 3–5 line summary, each section's row count, the per-run
findings, and the open questions.
```

**Reuse inventory, JavaScript side:**

```
You are inventorying what a Shopify theme already ships, JavaScript side, so a
composition task can tell which existing sections carry a design's behaviour
and motion. READ-ONLY on the theme: your only write is the report named below.

Format spec: {skill-dir}/references/components-format.md
Read it in full before writing a byte of the report, and reproduce the block it
gives, holding the categories your tree produced. Which category a row belongs
to, and the sources to sweep, are the spec's.

Theme repo: {repo-path}
Header `skill:` field, for the merged doc: figma-shopify-composer
(theme-scanner — reuse inventory)
Read: the JavaScript source tree
Write to: {temp-dir}/COMPONENTS-{n}.md, holding the categories your tree
produced — the main agent merges every side's report into
.agent/COMPONENTS.md and assembles the header from their counts
Mode: {FULL | INCREMENTAL — refresh only these entries: {list}}
Scope: {the whole tree | shard {n} of {total} — {file range}}

Return only a 3–5 line summary, each category's row count, the header counts
your tree yields, and the open questions.
```

**Reuse inventory, Liquid/CSS side:** the same prompt with every Liquid file — `sections/`, `blocks/`, `snippets/`, `layout/`, `templates/` — and every stylesheet as the tree it reads, and its own report number. Between them the two sides read every file the theme ships, which is what the gate measures against.

### style-reporter prompt

```
You are producing the style report for one breakpoint of a Shopify composition
(existing sections/blocks configured via template JSON) built from a design
spec. You NEVER edit theme files — no Write, no Edit, no shell command that
changes a theme file. Your ONLY writes are the result screenshot and the report
file named below. Capture, assert, reconcile, report.

Breakpoint: {desktop|mobile}, width {w}px
Render at: {dev-server-url | preview-url}
Clip to the composed region: {selector for the added section instance(s) or
the host section}
Design spec (the expected values): {temp-dir}/figma-spec.md
Fidelity forecast, from the approved plan: {element → EXACT | APPROXIMATES
(with the forecast delta) | UNACHIEVABLE}
Capability map for tagging: .agent/THEME-CAPABILITIES.md + the approved
settings map
Key elements to assert: {the forecast's EXACT and APPROXIMATES elements, from
the approved plan} — elements forecast UNACHIEVABLE are NOT asserted; list
them by name instead

1. Capture hygiene, then capture: viewport at the Figma frame width above;
   animations/transitions disabled; wait for document.fonts.ready + network
   idle; clip to the composed region, not the full page.
2. Computed styles: getComputedStyle on each key element vs the design spec's
   values (font-family/size/weight, line-height, letter-spacing, color,
   background, padding, margin, gap, border, border-radius). Record every
   mismatch: element, property, expected, actual.
3. Reconcile each mismatch against the forecast for that element:
   - forecast EXACT → BROKEN FORECAST. The plan promised this value was fully
     achievable from existing settings, and it did not land. Tag it either
     "settings-fixable per the capability map" (name the setting) or
     "undeclared gap". This is a forecasting failure, not a build defect —
     say so.
   - forecast APPROXIMATES → APPROXIMATION, QUANTIFIED. Not a failure. Give
     the measured delta (expected vs actual, and the numeric difference) and
     whether it is within the delta the forecast described.
4. Write the capture to .agent/figma-shopify-composer/visual-check/
   {composition-name}/result-{breakpoint}.png, overwriting what is there.
   Generate no diff image and no other render variant.

Write the FULL table to {temp-dir}/style-report-{breakpoint}.md: one row per
mismatch — element | property | expected | actual | forecast (EXACT /
APPROXIMATES) | reconciliation (BROKEN FORECAST + tag, or the quantified
delta) — followed by the UNACHIEVABLE elements named and excluded. Return that
table as TEXT only, plus the mismatch count split by forecast class. Return no
images.
```

## Knowledge docs — scan once, reuse

`.agent/` at the theme repo root holds every durable artifact this skill suite produces: shared knowledge docs at its root, per-skill outputs under `.agent/<skill-name>/`. Knowledge docs are written for an AI reader — tables, exact identifiers (section filenames, setting ids, types, defaults), composition rules and constraints, zero filler prose — and are the one exception to "nothing before approval": each lands before the run continues — the capability catalog as its scanner writes it, the reuse inventory as soon as the main agent merges both sides — so the knowledge survives even an abandoned run.

This skill produces both shared docs and reads both:

| doc | what it answers here | shape |
|---|---|---|
| `.agent/THEME-CAPABILITIES.md` | what the theme's existing sections, blocks and settings can already do — the capability inventory 1c matches every requirement against | [`references/theme-capabilities-format.md`](references/theme-capabilities-format.md) |
| `.agent/COMPONENTS.md` | what the theme already ships and where — its Flows, Patterns and Animations rows map a design requirement to candidate sections, motion included: reveals · hover treatments · loading states | [`references/components-format.md`](references/components-format.md) |

**Their shape comes from their format specs, not from this file.** Read the spec in full before writing a byte of either doc, and reproduce the block it gives. Each spec carries that block, the header fields, a row schema per section, the `format:` ladder deciding regenerate / refresh / read-as-is, the completeness gate, and the sharding threshold.

Producing the reuse inventory rather than only consulting it is what keeps a run on a theme without one from silently losing a signal this skill says it uses.

**Read before any scan (main agent, at 1b):**

1. Read each doc where it exists and run its spec's §Format version against it. That ladder decides FULL, INCREMENTAL, read-as-fresh, or read-as-newer — per doc, independently.
2. Dispatch only the scanners the ladder leaves standing: a doc read as fresh or read as newer stands its scanner(s) down, and a doc read as newer is named in the final output as read-as-is. A stood-down capability catalog still leaves the placement anchor and the `.git/info/exclude` check to two small inline reads.
3. The scanners write BEFORE 1c matching continues — the capability scanner into its doc, the two reuse scanners into shards the main agent merges into theirs.
4. Run each written or merged doc's completeness gate (its spec's §Completeness gate) before 1c reads it. A shortfall re-dispatches only the section or category that fell short; one still short after that second dispatch carries its expected count, actual count, and missing names into the final output.
5. An explicit user refresh always wins, per that doc's own refresh phrase: FULL rescan, doc rewritten.

**Root pointer:** the repo's root `AGENTS.md`/`CLAUDE.md` names this convention so future sessions find the docs before rescanning. Missing → append it (or create a minimal `CLAUDE.md` holding just this block, excluded like everything else) as a planned edit:

```
## 📚 Knowledge docs (check before any theme scan)
Skill outputs + knowledge docs live under `.agent/` — shared docs at its root,
per-skill outputs in `.agent/<skill-name>/`. Read `.agent/THEME-CAPABILITIES.md`
before any theme scan and search `.agent/COMPONENTS.md` before writing new
code; freshness checks + refresh instructions in their headers.
```

## The visual-check folder

`.agent/figma-shopify-composer/visual-check/<composition-name>/` in the theme repo, `<composition-name>` kebab-cased from the Figma frame name (e.g. `.agent/figma-shopify-composer/visual-check/hero/`). Its root holds the design spec and two image classes:

- **The design spec**, at the folder root — `figma-spec.md`, copied in from the temp directory at render start and retained, so the values this composition was given survive the run.
- **Figma references**, at the folder root — `figma-desktop.png` / `figma-mobile.png`, written once at render start.
- **Clean renders**, at the folder root — `result-desktop.png` / `result-mobile.png`, written by the style reporter, one per breakpoint.
- No diff images, and no `clean-`, `section-`, or other render variants are generated. These whole-frame files are what the user compares by eye.
- **Per-asset exports**, in `assets/`, flat — the shipping file for each Figma node, each raster's `original-source-*` beside it, and `UPLOAD.md` (§Asset export).
- `HARDCODE-ACTIVE.md` — present only while a hardcode is live (§Hardcode-then-revert).

The folder is not theme code: `.agent/` stays out of git via a `.git/info/exclude` line (confirm the `.agent/` line exists; append it as a planned edit if not — a local, never-committed file, and the Shopify CLI ignores non-theme root directories, so it is never pushed). At cleanup, the root retains only the design spec and the four image files above; `assets/` remains for the user to review and upload, while `HARDCODE-ACTIVE.md` is deleted after every revert.

## Asset export — one file per node, and never the page behind it

A `download_assets` call per asset node-id from the inventory. **`export` renders the node with its whole ancestor chain**, clipped to the node's bounds, so its PNG and SVG paint the design's page fill behind the artwork — usually white, whatever the page frame holds. Its PDF does not. Every `export` is therefore requested as PDF and rasterized locally; `rawImages` and `svgAssets` are unaffected and preserve alpha as they always did. See `docs/adr/0005-export-ships-through-pdf.md`.

A crop exists only when the node shows less than the whole source picture. That is what picks the field, with the row's **kind**:

| Kind | Ships | Kept beside it |
|---|---|---|
| **Raster fill, uncropped** — fill renders at 100% or less in both axes, and the source aspect is within 2% of the node's | the largest `rawImages` — the picture whole, with its alpha | the same bytes again, as `original-source-<name>` |
| **Raster fill, cropped** — the fill renders above 100% in either axis, or the aspects differ by more than 2% | `export` as PDF, rasterized | the largest `rawImages`, as `original-source-<name>` |
| **Vector** | `svgAssets` — scale-free, and a multi-layer group comes back composed into one file | — |
| **Composition** — shapes plus text, which exists no other way | `export` as PDF, rasterized | — |

An uncropped fill has nothing for `export` to contribute: it would upscale the same pixels and flatten the page behind them. Residual framing within 2% is the section's own `object-fit` to reproduce, not an export's. The 2% is a chosen line rather than a derived one — move it deliberately and record the move here.

The archive copy is **unconditional**: an uncropped row's `original-source-<name>` duplicates its own shipping file, and that duplication is the point. The prefix is the run's standing guarantee that the untouched source is on disk, and a guarantee that holds only for some rows is not one.

**PDF is a transport format, never a deliverable.** Pass `defaultFormat: "pdf"`, rasterize at the chosen scale, delete the PDF. Nothing uploads one, nothing keeps one:

```sh
sips -s format png --resampleWidth <target-px> export.pdf --out <name>.png      # macOS, ships with the OS
pdftoppm -png -scale-to-x <target-px> -scale-to-y -1 export.pdf <name>          # elsewhere; magick also works
```

`<target-px>` is the node's `w` times the scale chosen below — the same number the **Bounds** check divides back out. Both commands take it, so neither platform needs a second conversion.

**Delivered format follows the artwork, not the route:** PNG where any pixel is transparent, JPEG where the picture is a fully opaque photograph, SVG for vectors. A `rawImages` file ships as the bytes arrived, in the format its `format` field names — re-encoding it only adds a generation of loss.

`rawImages` holds the designer's upload at its original framing: 832×1248 portrait where the design shows a 616×464 landscape. That makes it the **original source** — it sets the export's scale ceiling and stays in `assets/` for a later re-crop; where a crop exists, the crop is what ships. Several entries at one aspect (within 1%) are one picture at several resolutions, so the largest is it; aspects that differ, or `rawImagesTruncated`, mean the row claims one fill over a subtree holding more — OPEN QUESTION.

**`export` flattens**, so a node whose subtree holds text reaches the user as an OPEN QUESTION naming each string, and that export waits on the answer — the inventory flags it, `get_metadata` confirms it at export time. Flattening trades live copy for pixels: right for a badge, wrong for a card whose heading and CTA belong in markup.

**Scale** applies to `export` alone — `rawImages` and `svgAssets` are scale-free. Pass `defaultScale` explicitly every time, so a node's own export settings never decide it, and take the largest value satisfying all three — or the first two alone on a composition, which carries no original source to cap it:

- `≤ 4`, `w × h ≤ 20 MP`, `max(w,h) ≤ 5760` — Files rejects above 20 MP and `image_url` caps at 5760 px, so a blanket 4x fails on square assets.
- **`max(w,h) ≤ 4096`** — `download_assets` caps a render there when the node carries no export settings of its own.
- **The original source's real resolution**, `source_w ÷ (node_w × w%)` from the fill's rendered percentage — 1.35 for an 832-wide original filling a 616-wide node. Past it Figma interpolates, and upscaling invents no detail.

Filenames kebab-case from the Figma layer name, extension by delivered format. One node, one file.

**Four checks close the phase:**

- **Alpha** — every asset the inventory marks as needing transparency carries pixels below full opacity. A file that is 100% opaque failed, however plausible it looks; report the node and the measured figure rather than the eye.
- **Bounds** — each `export`-sourced file's pixels ÷ its scale equals the node's `w`×`h` within 1 px. Short means the parent frame **clipped** it: report the node and both numbers.
- **Identity** — each asset node-id is its own, distinct from the desktop and mobile frame node-ids the run was given.
- **Count** — shipping files in `assets/` equals inventory rows, and `original-source-*` equals the raster-fill rows; name any miss.

**Source-quality flag:** when an original source is narrower than 2× its slot's rendered CSS width, record it in the plan and the final output with the layer name and both numbers. The remedy is new source art in Figma, not a bigger export.

`assets/UPLOAD.md` closes the phase and keeps the folder self-describing once the run's temp directory is gone. The archive block carries every raster-fill row:

```
UPLOAD THESE
<file>                  <w>×<h>  → <destination>

DO NOT UPLOAD — archive only
original-source-<file>  <w>×<h>  the untouched source; the same bytes as the
                                 shipping file where the row was uncropped
```

## Asset delivery — uploaded and client-changeable

Assets ship as Files uploads the client assigns to the existing sections' `image_picker` settings in the theme editor, so they stay swappable:

| Asset | Export as | Rendered by |
|---|---|---|
| Icon, flat illustration, logo, line art | **SVG** | the section's `image_picker` |
| Photo, hero, product shot | **PNG** where any pixel is transparent, **JPEG** where fully opaque | the section's `image_picker` |

Upload what ships: Shopify's CDN re-encodes to WebP or AVIF per browser and per derivative on its own, so pre-converting only adds a generation of loss and no image encoder ever reaches the ledger. Where the host section pipes an SVG through an unpinned `image_tag`, it emits ~19 srcset candidates that all resolve to the same file, and where its code carries `format: 'pjpg'` it forfeits WebP and AVIF entirely — both are existing section code, so both are reported as gaps rather than edited.

**Inline branch:** unreachable here. When the user designates an asset as carrying motion or a hover/scheme colour change, that needs committed theme code — report it as a gap and defer it to the figma-shopify-builder skill.

## Hardcode-then-revert

`image_picker` takes no `default`, so an assigned-by-hand image region renders empty and the result screenshot would show a hole — the one thing the user is going to judge the composition by. The render puts the exported assets in directly, then puts the settings back.

**Before hardcoding**, write `HARDCODE-ACTIVE.md` into the visual-check folder: every file path about to be touched, the original template JSON verbatim, and every temp asset copied into the theme's `assets/`. It is the snapshot the revert restores from.

**Inject once**, after the render is up and before the first capture, at the first tier that reaches the region:

1. **The section's or block's own `liquid` setting** in the template JSON — renders in the right DOM position and stays inside the template-only build surface. The capability inventory flags which sections expose one.
2. **A temporary Custom Liquid section** in `order`, emitting a `{% style %}` block alone that background-images the real element in place — for host sections with no `liquid` setting, and only where the empty picker still renders a targetable element.
3. **Neither tier reaches it** — this skill writes template JSON only, and a region needing committed section code is out of its reach. It is not injected and not worked around: the plan names it, the result render shows the empty picker, and the final output says so with the tier that would be needed.

Injected regions sit between sentinels and temp assets carry the `vh-tmp-` prefix, which is what makes both greppable:

```liquid
{%- comment -%} VERIFY-HARDCODE-START <name> {%- endcomment -%}
<img src="{{ 'vh-tmp-hero.png' | asset_url }}" width="…" height="…" alt="">
{%- comment -%} VERIFY-HARDCODE-END <name> {%- endcomment -%}
```

Correction-round fixes go outside the marked region — tier 2's temporary section is removed wholesale at revert, so a settings fix parked inside it would go with it.

Tiers 1 and 2 copy temp assets into the theme's `assets/`, the one point where this skill writes a theme file. They are transient by construction: the revert deletes them, and the final output reports that no theme file remains rather than that none was created.

**Revert** on every exit — completion and abort alike: restore from the breadcrumb, delete `assets/vh-tmp-*`, remove the temp Custom Liquid section from `order`, delete the breadcrumb.

**Prove it** in the final output: `grep -r VERIFY-HARDCODE` over the theme returns nothing, no `vh-tmp-*` remains, and the template JSON matches the breadcrumb's original. A revert that fails reports **REVERT FAILED** with the breadcrumb path.

A session that dies mid-render leaves the breadcrumb and the sentinels in place. Finding either at the start of a run means reverting from it first.

## Phase 1 — Research (read-only on the theme)

**Stranded-hardcode check first** (main agent, before anything else): a `HARDCODE-ACTIVE.md` in any `.agent/figma-shopify-composer/visual-check/*/`, or a `grep -r VERIFY-HARDCODE` hit in the theme, is a hardcode a previous session left live. Revert it per §Hardcode-then-revert and report it before the run continues — a stranded hardcode is the one theme edit this phase makes, and leaving it live in a client's theme is the risk the mechanism exists to close.

Run 1a and every standing scanner of 1b in parallel, then match in main. Beyond that revert, no theme file is created or modified; the only writes are the knowledge docs (§Knowledge docs).

- **1a. Figma requirements** → figma-extractor: both frames via the Figma MCP; the producer/write-surface header; exact-values table (the settings-configuration targets AND the style report's expected values); per-breakpoint layout structure and desktop/mobile differences; layout intent; stacking and overlap; group rhythm; asset inventory; the distilled REQUIREMENTS LIST. Report: `figma-spec.md`, the design spec. This is the run's only extraction — the composition reads from it and never returns to Figma for a value.
- **1b. Theme knowledge** — the knowledge-doc check first (§Knowledge docs), then the scanners it leaves standing: the capability scanner into `.agent/THEME-CAPABILITIES.md`, the two reuse scanners into the shards the main agent merges into `.agent/COMPONENTS.md`, each doc gated on arrival. What each scanner reads, and every fact its rows carry, is its format spec's. Per-run and never in a doc: the target-template placement anchor (OPEN QUESTION if ambiguous) and the `.git/info/exclude` check — inline reads where the catalog stood its scanner down. Above a spec's sharding threshold each standing scanner splits further into the shards the spec defines, each carrying its file range, and the main agent merges. Current global values are read live from `config/settings_data.json` in main — the catalog carries the schema's declared defaults, which are a different fact.
- **1c. Match requirements to capabilities** (main agent, from `figma-spec.md` + `.agent/THEME-CAPABILITIES.md`): for every requirement, the existing capability that achieves it — which section type (or stack of section instances), which block types, which settings and values, per breakpoint. Where a style value should come from a global, check whether the CURRENT global value already equals the Figma value — if it doesn't, that is a decision point, never a silent change. Anything with no existing capability is a GAP: record the closest achievable approximation and its visible cost, and whether an existing per-instance custom CSS/Liquid setting (an existing setting, so within the constraint) could close it.
- **1d. Tooling detection** (main agent, non-mutating checks only): Browser pane availability first, then fallbacks per Browser tiers; the Agent tool and which tools reach subagents (fix the delegation map). Render path: Shopify CLI + `shopify.theme.toml` → `shopify theme dev` (desktop app: defined in `.claude/launch.json` so the pane manages the server); otherwise a preview/live store URL. There is NO static-render fallback — composed existing sections depend on the full theme runtime (snippets, global settings, theme CSS/JS), which a local Liquid engine cannot reproduce. Record the tiers and any temporary installs required.
- **1e. Ask**: put anything still ambiguous — including OPEN QUESTIONS from the reports — to the user as concise questions before planning.

**Done when:** the design spec `figma-spec.md` exists, carrying its producer/write-surface header and all seven sections; both knowledge docs are current and past their gates — produced this run, refreshed incrementally, or read as fresh or newer with that decision recorded; every requirement is matched to a capability or recorded as a gap; every OPEN QUESTION is answered; and the tooling record names browser tier, capture source, render path, delegation map, temp dir, and the exclude status.

## Phase 2 — Plan (stop for approval)

Present the complete plan and stop. This is the run's ONLY stop. Create or modify nothing until the user approves. Approval covers the design spec, the fidelity forecast, the temporary installs, and any global-value change or custom-CSS usage the plan explicitly lists.

- **The design spec, quoted inline**: the exact-values table reproduced in the plan itself, per breakpoint, plus the layout intent, the stacking and overlap, and the group rhythm — quoted, never referenced by file path. The user approves the numbers themselves, because after this stop nothing re-reads Figma and a misread design is not caught again. Every OPEN QUESTION is resolved above it.
- **Composition**: which existing section type(s) — one instance or a stack — and/or which existing block types, in what order.
- **Settings map**: for every chosen section instance and block, every setting id → value, per breakpoint where responsive settings exist, with the Figma value it satisfies. Text/link settings carry the Figma copy. Image settings stay unassigned — the user uploads the exported assets via the theme editor and assigns them (§Asset delivery); the render shows those regions through the hardcode, and a region no injection tier reaches is declared as an empty picker in the result render.
- **Global-inheritance table**: requirement → global-connected setting used → whether the current global value already matches Figma. Where it doesn't, the user picks one: a per-instance override setting (if one exists) / changing the global VALUE — flagged loudly, it restyles the whole storefront / accepting the current global as an approved gap.
- **Fidelity forecast**: every element sorted into EXACT (fully met by existing capabilities), APPROXIMATES (closest achievable, its visible cost and expected delta described), or UNACHIEVABLE without new code — accept as a gap or defer to the figma-shopify-builder skill. A per-instance custom CSS/Liquid setting proposed as a gap-closer is its own flagged line item. The forecast is per element, because the style report reads every mismatch back against it: an EXACT element that misses is a broken forecast, an APPROXIMATES element that misses is the approximation quantified, and the UNACHIEVABLE elements are the ones the report names rather than asserts.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append adding it.
- **Asset-export list** (§Asset export, §Asset delivery): every inventoried asset → node-id, kind, source field, format, computed scale, and filename in `.agent/figma-shopify-composer/visual-check/<composition-name>/assets/`, plus the section setting the user will assign it to and, for a raster fill, its `original-source-*` twin; `assets/UPLOAD.md` is written from this list.
- **Hardcode plan** (§Hardcode-then-revert): per image region, the injection tier that reaches it and its temp `vh-tmp-` asset; a region no tier reaches is named as one the result render will show empty, with the tier it would need.
- **Template diff**: the exact JSON — new entries in `sections` (type = existing section file, with the settings map and `blocks` + `block_order`) inserted into `order` at the input placement; or, for a block composition, the block entries and `block_order` position inside the host section instance.
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced so far.
- **Render-and-report approach**: browser tier, render path, whether `.claude/launch.json` will be created/updated (a planned file if so), the capture width per breakpoint, the composed-region selector, the key elements the style report asserts — the forecast's EXACT and APPROXIMATES elements, with the UNACHIEVABLE ones listed separately as excluded — and the exact temporary-install list with method (on-demand runner / project-local / venv) and removal confirmation.

**Done when:** the user has approved.

## Phase 3 — Implement (main agent only)

Touch only planned files; no delegated edits.

- Edit the target template JSON exactly as approved — section entries with their settings maps and block configurations at the approved position — configuring from the approved design spec alone: its exact values, its layout intent, its stacking and overlap, its group rhythm. Figma is not re-read; a value the spec does not carry goes back to the user. Show the diff again before writing.
- Apply any approved global-value change in `config/settings_data.json` exactly as listed in the plan, and nothing beyond it.
- Append the `.agent/` line to `.git/info/exclude` if planned.
- Export the Figma assets per the approved list (§Asset export) into `.agent/figma-shopify-composer/visual-check/<composition-name>/assets/`; run the bounds, identity and count checks.

**Done when:** every planned edit is in place as approved and nothing else changed — no new theme files, no new settings, no edited section/block/snippet/CSS/JS file — and all three export checks pass — bounds, identity, and both counts — with `assets/UPLOAD.md` written.

## Phase 4 — Render and report

**Static, first:** the target template (and `config/settings_data.json`, if edited) still parses as valid JSON; `shopify theme check` on changed files if available; fix errors.

Then **seven steps, in this order** — render → data check → capture hygiene → `style-reporter` → correction round → style report → cleanup. The three Figma-driven skills share this shape; the one step this skill varies is step 6, the style report, which reconciles every mismatch against the approved fidelity forecast. There is no loop, no iteration cap and no pass/fail verdict: the run passes through the seven once and ends by handing the user the evidence.

At the start, write `figma-desktop.png` / `figma-mobile.png` into the visual-check folder and copy the approved design spec in beside them as `figma-spec.md`.

**1. Render.** `shopify theme dev` when available (Browser pane manages it via `.claude/launch.json` in the desktop app); otherwise the preview/live store URL in the browser. There is no static fallback — composed existing sections require the full theme runtime.

**2. Data check** (main agent) — the shape's data check in its plain form. Each skill's render pulls its own kind of data, so each fills this step with the check that data needs; the builder's metafield/metaobject stop-and-hand-over is that skill's, and this is this skill's. Filling the slot is not varying the shape — step 6 is the one step this skill varies. Existing sections render the store's REAL data, so a composed instance can come up empty or wrong-shape for reasons the settings map cannot see: a product/collection/blog reference that resolves to nothing, a section whose content comes from a resource the template's context doesn't supply. Confirm each configured instance renders the content the approved settings map points at; where it doesn't, hand the user exactly what is missing and resume once it exists — nothing is captured against a render that isn't showing the composition.

**3. Capture hygiene** (before every capture): the Figma frame width per breakpoint; clip to the composed region (the added section instance(s) or host section), not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle. No scale-matching and no pixel-dimension requirement — nothing compares the capture to the reference mechanically. Capture source: the Browser pane, else connected browser MCP or installed Chrome, else `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the cleanup ledger). **Hardcode last** (main agent, before the first capture): breadcrumb, then inject at the planned tier per §Hardcode-then-revert, so the result screenshot shows the design rather than an empty `image_picker`.

**4. `style-reporter`, once per breakpoint.** One call each for desktop and mobile: it captures, asserts the key elements' computed styles against the design spec's values, reconciles each mismatch against the fidelity forecast, writes `result-{breakpoint}.png` into the visual-check folder, and returns a text mismatch table. It never edits theme files and returns no images. Without delegation the same work runs in the main conversation, once per breakpoint.

**5. Correction round** (main agent, once). Read the returned tables and fix what they name by ADJUSTING SETTINGS VALUES in the template JSON per the capability map — never by editing section/block code. If no setting can move the value, it is an undeclared gap: surface it, don't hack it. Then re-render and re-run `style-reporter` once per affected breakpoint. One pass, one re-check, then stop; whatever remains goes into the report as-is.

**Revert** closes this step, the last capture now taken: restore from the breadcrumb and prove it per §Hardcode-then-revert.

**6. Style report — this skill's permitted variation.** Emit the surviving mismatches per breakpoint, each one read back against the approved forecast for its element:

- **Forecast EXACT, mismatched → BROKEN FORECAST.** The plan promised existing settings would hit the value and they did not. It is a forecasting failure, reported as such and distinct from a build defect, tagged either settings-fixable per the capability map (naming the setting) or an undeclared gap.
- **Forecast APPROXIMATES, mismatched → the approximation, quantified.** Not a failure: the row carries the measured delta — expected, actual, the numeric difference — and whether it sits inside the delta the forecast described.
- **Forecast UNACHIEVABLE → excluded from the assertion list and named.** These are never asserted, so they never appear as mismatches; the report lists them by name as out of reach without new code, deferred to the figma-shopify-builder skill.

One row per mismatch — element, property, expected, actual, forecast class, reconciliation — and "no mismatches" where there are none. It is output, not judgment: it never blocks completion and carries no threshold, ratio, iteration count, plateau state or verdict. Nothing is excluded except the UNACHIEVABLE elements the forecast already named. It sits beside `result-desktop.png` / `result-mobile.png` and `figma-desktop.png` / `figma-mobile.png`, which the user compares by eye. Note the report scope: computed styles were checked at the two captured widths, on the key elements the plan named.

If no render or capture path exists even with temporary installs: revert any live hardcode, then stop and report exactly what's missing.

**7. Cleanup.** The ledger lists every temporary install (name, method, location). First refresh both shared knowledge docs against the current branch using their format ladders — reconcile the changed template scan and `git:` line, append the run to `updates:`, and rerun both completeness gates before the final report; a higher-format doc is read-as-newer and left byte-for-byte unchanged. Then uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall; `.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/` in full — the knowledge docs for the next run, plus `.agent/figma-shopify-composer/visual-check/<composition-name>/` (the design spec, the references, the result renders, exported assets) — untracked via `.git/info/exclude`. The user reviews the renders before committing, uploads the files `assets/UPLOAD.md` lists through the theme editor and assigns them to the image settings, and manages the folder themselves. Nothing lands in git except the planned template/config edits.

**Final output (no explanatory prose):** files changed (expected: the template JSON; possibly `settings_data.json`, the `.git/info/exclude` append, `.claude/launch.json`) with confirmation that NO theme file REMAINS beyond those and NO schemas were edited; the revert proof (`grep -r VERIFY-HARDCODE` clean, no `vh-tmp-*` remaining, template JSON matching the breadcrumb original) or **REVERT FAILED** with the breadcrumb path; the style report per breakpoint — element, expected, actual, forecast class and reconciliation per surviving mismatch, or "no mismatches" — with the broken forecasts called out, the approximations' deltas given, and the UNACHIEVABLE elements named as excluded; any image region no hardcode tier reached, named as showing empty in the result render; any source-quality flags; any assets deferred to figma-shopify-builder for the inline branch; the delegation map; the tooling ledger with removal confirmation (or "nothing installed"); knowledge-doc status, one line each for `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` — created / refreshed incrementally / read as fresh / read as newer and left unchanged, with the gate's reconciled counts or its declared shortfall; the path `.agent/figma-shopify-composer/visual-check/<composition-name>/` with a one-line inventory (the design spec, the references, the result renders, shipping files and `original-source-*` counts per format, `UPLOAD.md`) and exclusion confirmation.

## Rules

- Read every file before editing; show a diff before overwriting anything existing.
- Ask instead of assuming.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- The design spec is the authority: the composition reads from it alone, no value is re-read from Figma after Phase 1, and a value it does not carry goes back to the user.
- The style report reports; it never blocks completion. One check against the design spec, one correction round, then it is emitted with whatever remains — no threshold, no ratio, no iteration count, no verdict.
- Every mismatch is read back against the approved forecast: EXACT that missed is a BROKEN FORECAST, not a build defect; APPROXIMATES that missed is the approximation quantified, not a failure; UNACHIEVABLE is never asserted, only named. Nothing else is excluded from the report.
- The template JSON (plus approved `settings_data.json` values) is the only build surface; `.git/info/exclude`, `.claude/launch.json`, and the `.agent/` tree are the only other writable paths, per the plan. Section/block/snippet/CSS/JS files stay read-only — no new theme files, no new settings, no schema edits. The render's `vh-tmp-` assets are the one transient exception and the revert removes them.
- `assets/` holds the shipping file for each Figma node — its crop where one exists, its original source where none does — each raster's `original-source-*` beside it; reference captures at the folder root hold the frame. The bounds, identity and alpha checks keep a clipped, whole-frame or page-backed render out.
- Upload the crops and let the CDN pick the format — no image encoder reaches the ledger.
- A hardcode is breadcrumbed before it exists and reverted on every exit — completion and abort alike — with the grep proof in the final output.
- Knowledge docs first: read `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` before any theme scan and run each spec's `format:` ladder on it; a scanner that runs writes its doc back, past its completeness gate, before the task continues. An explicit user refresh always wins.
- This skill produces both shared docs, so a theme missing one is scanned rather than worked around, and a doc at a higher `format:` is read as it stands and named in the output.
- Never change a global setting VALUE silently — globals restyle the entire storefront; every global change is an explicit, individually-approved plan line.
- A per-instance custom CSS/Liquid setting is used only when the theme already has it AND the plan flagged it.
- Prefer global-connected settings over raw per-instance values when both can hit the Figma value.
- Verify template/schema JSON structure via the Shopify dev MCP instead of guessing.
- The Browser pane leads when available; fallbacks apply only when it's absent.
- Only `result-desktop.png` and `result-mobile.png` are generated at the visual-check root, alongside the design spec and the two Figma references; no diff images, and no `clean-`, `section-`, or other render variant.
- `.agent/` lives at the repo root, is always excluded via `.git/info/exclude`, and is never committed.
- CLI tools: check installed first (on PATH, project dep, or npm script) — installed → invoke directly (`shopify theme dev`, `npm run …`), no runner. Not installed → on-demand runner (`npx` / `pnpm dlx` / `bunx` / `pipx run`), never a global install. Runner impossible (persistent binary/venv needed) → project-local or venv, on the ledger.
- Leave the machine as it was found — the retained `.agent/` tree (knowledge docs + visual-check) is the one deliberate leftover, kept for the next run, review, and asset uploads.

## Usage

```
Use the figma-shopify-composer skill.
- Desktop: <figma link with node-id>
- Mobile: <figma link with node-id>
- Type: section
- Template: templates/index.json
- Place: after "Autoplay Slider"
```

No data-source line — content comes from the existing sections' and blocks' own settings.
