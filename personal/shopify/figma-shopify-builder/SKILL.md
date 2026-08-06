---
name: figma-shopify-builder
description: Build pixel-accurate Shopify sections or blocks from Figma designs. Use when the user shares Figma links (desktop + mobile node-ids) to implement in a theme, asks for a section or block added to a template, wants content editable via theme-editor settings, or wants it driven by metafields/metaobjects. Fidelity is measured — computed styles plus pixel diff against the Figma frames — never eyeballed.
---

# Figma → Shopify Builder

Build a theme section or block from two Figma frames and prove it pixel-accurate by measurement. Four phases — research (read-only on the theme), plan (stop for approval), implement, verify (numeric gate) — then cleanup that leaves the machine as found. Nothing is created or modified before plan approval except knowledge docs under `.agent/` (§Knowledge docs) and the revert of a hardcode a previous session stranded (§Phase 1); the deliberate leftovers are the visual-check folder and the knowledge docs.

## Inputs

Collect all six before starting; ask for any that are missing.

1. **Figma desktop link** — with node-id.
2. **Figma mobile link** — with node-id.
3. **Build type** — `section` or `block`. For a block, detect the theme's architecture — theme blocks (`blocks/` dir) vs blocks defined inside a host section's schema — and if section-scoped, ask which host section.
4. **Target template** — e.g. `templates/index.json`.
5. **Placement** — before/after which existing section (by customizer label or type). For a block: which section instance in the template and its position in `block_order`.
6. **Data source** — one of:
   - **Theme settings** — all content editable via the section's or block's schema settings in the theme editor, defaults matching the Figma copy; repeated items become editor blocks.
   - **Metafields** — namespace.key(s), owner type (product/collection/page/shop), and how the owner resolves in this template's context (ask if unclear); connect via dynamic sources where the theme editor supports them. When the design contains repeated items (cards, slides, testimonials, FAQ entries), the user picks ONE multiple-data type — it governs all repeated data in the build; if unspecified, ask before planning:
     - **json** — a single metafield of type `json` on the owner holding an array of item objects. The plan proposes the exact item schema (each key ↔ the Figma element it fills); the Liquid iterates `metafield.value`.
     - **metaobject** — a metaobject definition whose fields map to the Figma item elements (text → single/multi-line text, image → file_reference, link → url, …); entries reached via a `list.metaobject_reference` metafield on the owner, or iterated from `shop.metaobjects.<type>.values` when not owner-bound — the plan proposes which, plus the definition type, field keys, and how entry ORDER is controlled (list order vs an explicit sort field).

   Metafield/metaobject definitions and values live in Shopify admin, not theme code: the plan writes out the exact spec + sample values (matching the Figma copy) for the user to create; theme code only reads them, and absent data takes the split.

## The split — placeholder in the editor, nothing on live

Missing content renders two ways, branched on `request.design_mode` (true in the theme editor, false in preview links and on the live site):

- **Theme editor** — a placeholder holds the spot, naming the empty settings by their schema labels so the merchant sees what to fill. A block placeholder carries `{{ block.shopify_attributes }}`, staying clickable into that block's settings.
- **Preview and live** — the branch emits no markup. Shopify still wraps a section in `<div id="shopify-section-…">`; where theme CSS gives that wrapper margin or padding, the leftover gap is closed in the plan.

**Required settings decide** — schema settings for a theme-settings build, metafield/metaobject fields for a metafields build. Which ones count is the user's call per build, never inferred from "this field is blank". A hero carrying an image and a heading may make only the heading required: heading blank → the section takes the split; image blank → the image markup is skipped and the rest renders as designed. The plan proposes them once the schema exists — the minimum that leaves the section meaningless when blank, typically the primary copy or the item's data source, decorative fields left skip-only — named for the section and for each block type; the user confirms or corrects at approval.

Repeated items cascade: an item whose required settings are blank takes the split on its own; when no item survives, so does the host section.

Placeholders reuse the theme's own treatment: grep `placeholder_svg_tag`, a `placeholder` class, and `snippets/placeholder*`, plus `.agent/COMPONENTS.md` by reuse keyword `placeholder`. No match → the plan proposes one, and a reusable snippet earns a Functions row there. Copy is a fixed template rather than composed per build — `<display name> — add <required setting labels, joined> to show this <section|block>` — and a theme convention carrying its own copy wins.

## Pixel-accurate is a measured result

The build passes when, per breakpoint:

1. Every checked computed style matches its Figma value.
2. The image diff ratio against the Figma screenshot is ≤ 1% with anti-aliasing ignored.
3. Residual diff pixels are confirmed FROM THE DIFF IMAGE to be text-rasterization noise — Figma and Chromium rasterize fonts differently, so a literal 0% is unreachable. Layout, color, or spacing differences are never "noise".

Side-by-side eyeballing is for diagnosis only; passing is numeric.

## Browser tiers

**Primary: the Claude Code Desktop Browser pane** (desktop app with Browser enabled). Claude drives it directly — screenshots, DOM/computed-style inspection, interaction — manages the dev server via `.claude/launch.json` (local dev servers need no site approval), and opens static HTML files from the project directly in the pane.

**Capture-exactness check:** the measured diff needs captures at the exact Figma frame widths and scale, with identical pixel dimensions, clipped to the section/block container. Confirm the pane's screenshots can honor that; if not, the pane still does inspection and diagnosis while the MEASURED captures fall to the first fallback that can.

**Fallbacks, in order:** connected browser MCP (Chrome DevTools MCP / Playwright MCP) → installed Chrome → temporary Playwright via npx.

## Delegation

Bounded research and measurement go to subagents — isolated workers with their own context windows that return only a final report — so bulk Figma payloads, theme reads, and per-iteration screenshots stay out of the main conversation, and independent research runs in parallel. Delegation multiplies tokens: skip it for trivially small reads.

Prefer the named custom agents `figma-extractor`, `theme-scanner`, and `visual-verifier` when installed in `~/.claude/agents/` or `.claude/agents/` — their definitions add tool-enforced restrictions (e.g. `disallowedTools: Write, Edit` on the verifier). Otherwise run the built-in general-purpose subagent with the embedded prompts below; in that fallback the no-theme-edits rule is instruction-enforced, so each prompt states it explicitly.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the Figma MCP / browser tools reach subagents (subagents inherit internal + MCP tools by default; the Browser pane's preview tools may be main-session-only). Any role whose tools don't reach a subagent runs in the main conversation instead.

**Handoff protocol:** subagents can't see the conversation and can't ask the user questions — every delegation prompt carries its exact inputs (node-ids, file paths, capture specs, the expected-values file path); every worker writes FULL findings to a report file in the temp working directory (the capability scanner writes its knowledge doc instead, and the two reuse scanners write the shards the main agent merges into theirs — §Knowledge docs) and returns a short summary; ambiguities come back as OPEN QUESTIONS for the main agent to put to the user. The repeated-items inventory is figma-extractor output, but the json-vs-metaobject ask always happens in the main conversation. The temp working directory is created per run (use the session scratchpad when available) and is deleted at cleanup.

**Never delegated:** planning, user approvals, all implementation edits, the json-vs-metaobject ask, the required-settings confirmation, the metafield-data stop-and-hand-over, and the diagnosis/fix half of the verification loop.

| Role | Phase | Report |
|---|---|---|
| figma-extractor | 1, parallel | `figma-spec.md` |
| theme-scanner — capability catalog | 1, parallel | `.agent/THEME-CAPABILITIES.md` (canonical; shards `{temp-dir}/THEME-CAPABILITIES-<n>.md`, merged into it by the main agent) |
| theme-scanner — reuse inventory, JavaScript side | 1, parallel | `{temp-dir}/COMPONENTS-<n>.md` |
| theme-scanner — reuse inventory, Liquid/CSS side | 1, parallel | `{temp-dir}/COMPONENTS-<n>.md` (every side's report merged into `.agent/COMPONENTS.md` by the main agent) |
| visual-verifier (never edits theme files) | 4, one call per iteration | `verify-report-<n>.md` |

All three scanners are read-only on the theme, and each dispatches only when its doc is absent or stale (§Knowledge docs). The two reuse scanners share one doc, so they stand or dispatch together — except in INCREMENTAL, where a side whose tree holds no changed entry stands down and its half of the doc is kept byte-for-byte, its rows and its share of the header's counts carried into the merge so the gate still measures the whole theme. Splitting them this way is what keeps a components scan from losing its last table to a capabilities scan competing for the same attention.

### figma-extractor prompt

```
You are extracting a Figma design spec for a Shopify theme build. Work only from
the Figma MCP; do not read or modify the theme repo.

Frames:
- Desktop: {figma-desktop-link} (node-id {desktop-node-id})
- Mobile: {figma-mobile-link} (node-id {mobile-node-id})

For each node-id call get_design_context and get_screenshot, then compile:
1. Exact-values table per breakpoint: typography (family, size, weight,
   line-height, letter-spacing), colors, spacing (padding/margin/gap), sizes,
   border-radii, image dimensions, frame width. These are the implementation
   targets AND the expected values for computed-style assertions — record exactly.
2. Desktop vs mobile layout differences (stacking, order, visibility, alignment).
3. Each screenshot's scale (1x/2x) and pixel dimensions — captures must match
   them exactly for the pixel diff.
4. Repeated-items inventory: any card/slide/testimonial/FAQ-style repetition —
   item count, the elements each item contains, per-item content.
5. Asset inventory — one row per exportable asset: layer name | node-id |
   kind (raster fill / vector / composition) | the node's w×h | for a raster
   fill, the fill's rendered percentage of its node (the `w-`/`h-` values
   get_design_context emits) and whether the subtree holds text. Phase 3
   exports from the node-id, so every asset carries its own; text in the
   subtree is an OPEN QUESTION, since exporting flattens it.

Write the FULL findings to {temp-dir}/figma-spec.md with an OPEN QUESTIONS
section at the end for anything ambiguous. Return only a 3–5 line summary plus
the open questions.
```

### theme-scanner prompts — one per doc

Each opens with the absolute path of its format spec and the same instruction: **read that spec in full before writing a byte of the doc, and reproduce the block it gives.** The doc's shape, its row schemas, and the sources to sweep are the spec's; the prompt carries the run.

**Capability catalog:**

```
You are cataloging what a Shopify theme's existing sections, blocks, and
settings can already do, to ground a new {section|block} build against what the
theme already has. READ-ONLY on the theme: your only write is the doc named
below.

Format spec: {skill-dir}/references/theme-capabilities-format.md
Read it in full before writing a byte of the doc, and reproduce the block it
gives. Every fact a row carries is the spec's §Row schemas.

Theme repo: {repo-path}
Header `skill:` field: figma-shopify-builder (theme-scanner — capability
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
   for a block build, the host section instance and its `block_order`
   position. OPEN QUESTION if ambiguous.
2. Whether .git/info/exclude carries a `.agent/` line.

Return only a 3–5 line summary, each section's row count, the per-run
findings, and the open questions.
```

**Reuse inventory, JavaScript side:**

```
You are inventorying what a Shopify theme already ships, JavaScript side, so a
new {section|block} build reuses or extends it instead of rebuilding it.
READ-ONLY on the theme: your only write is the report named below.

Format spec: {skill-dir}/references/components-format.md
Read it in full before writing a byte of the report, and reproduce the block it
gives, holding the categories your tree produced. Which category a row belongs
to, and the sources to sweep, are the spec's.

Theme repo: {repo-path}
Header `skill:` field, for the merged doc: figma-shopify-builder
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

### visual-verifier prompt

```
You are measuring one verification iteration of a Shopify {section|block}
against its Figma reference. You NEVER edit theme files — measure, record,
report only.

Iteration: {n} — breakpoint {desktop|mobile}, width {w}px, scale {s}, expected
capture dimensions {W}x{H}px
Render at: {dev-server-url | static-html-path}
Clip to container: {selector}
Figma reference: .agent/figma-shopify-builder/visual-check/{name}/
figma-{breakpoint}.png
Expected values: {temp-dir}/figma-spec.md
Key elements to assert: {list from the approved plan}
Diff tool: {pixelmatch … | odiff-bin …} (installed direct, else via npx; anti-aliasing ignored)

1. Capture hygiene, then capture: viewport at the exact width and scale above;
   animations/transitions disabled; wait for document.fonts.ready + network
   idle; stub or hide dynamic content not part of the comparison; clip to the
   container. The capture's pixel dimensions must equal the reference's exactly.
2. Computed styles: getComputedStyle on each key element vs the expected values
   (font-family/size/weight, line-height, letter-spacing, color, background,
   padding, margin, gap, border-radius). Record every mismatch: element,
   property, expected, actual.
3. Pixel diff: run the diff tool vs the reference; record the diff ratio; save
   the diff image.
4. Overwrite .agent/figma-shopify-builder/visual-check/{name}/
   result-{breakpoint}.png and diff-{breakpoint}.png with THIS iteration's
   capture and diff.

Write the FULL report to {temp-dir}/verify-report-{n}.md: mismatch table, diff
ratio, largest diff regions and where they sit. Return only the diff ratio,
mismatch count, and one line on the biggest offender.
```

## Knowledge docs — scan once, reuse

`.agent/` at the theme repo root holds every durable artifact this skill suite produces: shared knowledge docs at its root, per-skill outputs under `.agent/<skill-name>/`. Knowledge docs are written for an AI reader — tables, exact identifiers (filenames, setting ids, types, defaults), rules and constraints, zero filler prose — and are the one exception to "nothing before approval": each lands before the run continues — the capability catalog as its scanner writes it, the reuse inventory as soon as the main agent merges both sides — so the knowledge survives even an abandoned run.

This skill produces both shared docs and reads both:

| doc | what it answers here | shape |
|---|---|---|
| `.agent/THEME-CAPABILITIES.md` | what the theme already does, so a new build follows it — §Globals and §Conventions always, §Metafield patterns for a metafields source, §Block architecture for a block build | [`references/theme-capabilities-format.md`](references/theme-capabilities-format.md) |
| `.agent/COMPONENTS.md` | what already exists and where, searched by reuse keyword before a byte of new code is written — match → reuse or extend it | [`references/components-format.md`](references/components-format.md) |

**Their shape comes from their format specs, not from this file.** Read the spec in full before writing a byte of either doc, and reproduce the block it gives. Each spec carries that block, the header fields, a row schema per section, the `format:` ladder deciding regenerate / refresh / read-as-is, the completeness gate, and the sharding threshold.

**Read before the theme scan (main agent, Phase 1):**

1. Read each doc where it exists and run its spec's §Format version against it. That ladder decides FULL, INCREMENTAL, read-as-fresh, or read-as-newer — per doc, independently.
2. Dispatch only the scanners the ladder leaves standing: a doc read as fresh or read as newer stands its scanner(s) down, and a doc read as newer is named in the final output as read-as-is. A stood-down capability catalog still leaves the placement anchor and the `.git/info/exclude` check to two small inline reads.
3. The scanners write BEFORE planning continues — the capability scanner into its doc, the two reuse scanners into shards the main agent merges into theirs.
4. Run each written or merged doc's completeness gate (its spec's §Completeness gate) before the plan reads it. A shortfall re-dispatches only the section or category that fell short; one still short after that second dispatch carries its expected count, actual count, and missing names into the final output.
5. An explicit user refresh always wins, per that doc's own refresh phrase: FULL rescan, doc rewritten.

**After verification passes, each doc gains what this build added** — the section's or block's entry in §Section catalog or §Theme blocks plus its §Inheritance rows; a `## Custom web components` row per element registered, an `## Animations` row per reusable or recurring motion treatment built, and a row for the build itself. Each append lands in the table that owns it, `generated:` / `git:` / `scanned:` are refreshed, one dated `updates:` line records the run, and the doc faces its completeness gate again. A doc read at a higher `format:` keeps every byte: the build's entries are named in the final output instead.

**Root pointer:** the repo's root `AGENTS.md`/`CLAUDE.md` names this convention so future sessions find the docs before rescanning. Missing → append it (or create a minimal `CLAUDE.md` holding just this block, excluded like everything else) as a planned edit:

```
## 📚 Knowledge docs (check before any theme scan)
Skill outputs + knowledge docs live under `.agent/` — shared docs at its root,
per-skill outputs in `.agent/<skill-name>/`. Read `.agent/THEME-CAPABILITIES.md`
before any theme scan and search `.agent/COMPONENTS.md` before writing new
code; freshness checks + refresh instructions in their headers.
```

## The visual-check folder

`.agent/figma-shopify-builder/visual-check/<section-or-block-name>/` in the theme repo, kebab-cased from the section/block name (e.g. `.agent/figma-shopify-builder/visual-check/hero/`). The root has exactly three image classes:

- **Figma references**, at the folder root — `figma-desktop.png` / `figma-mobile.png`, written once at verification start.
- **Clean renders**, at the folder root — `result-desktop.png` / `result-mobile.png`, overwritten after EVERY verification iteration.
- **Image diffs**, at the folder root — `diff-desktop.png` / `diff-mobile.png`, overwritten after EVERY verification iteration.
- No `clean-`, `section-`, or other render variants are generated. These whole-frame files are the only measured comparison set; the pixel diff measures the frame.
- **Per-asset exports**, in `assets/`, flat — the shipping crop for each Figma node, each raster's `original-source-*` beside it, and `UPLOAD.md` (§Asset export).
- `HARDCODE-ACTIVE.md` — present only while a verification hardcode is live (§Hardcode-then-revert).

The folder is not theme code: `.agent/` stays out of git via a `.git/info/exclude` line (confirm the `.agent/` line exists; append it as a planned edit if not — a local, never-committed file, and the Shopify CLI ignores non-theme root directories, so it is never pushed). At cleanup, the root retains only the six image files above; `assets/` remains for the user to review and upload, while `HARDCODE-ACTIVE.md` is deleted after every revert.

## Asset export — the design's crop, one file per node

A `download_assets` call per asset node-id from the inventory, where the row's **kind** picks the field:

| Kind | Ships | Kept beside it |
|---|---|---|
| **Raster fill** | `export` — the node's own bounds, which is the designer's **crop** | the largest `rawImages`, as `original-source-<name>` |
| **Vector** | `svgAssets` — scale-free, and a multi-layer group comes back composed into one file | — |
| **Composition** — shapes plus text, which exists no other way | `export` | — |

`rawImages` holds the designer's upload at its original framing: 832×1248 portrait where the design shows a 616×464 landscape. That makes it the **original source** — it sets the export's scale ceiling and stays in `assets/` for a later re-crop, while the crop is what ships. Several entries at one aspect (within 1%) are one picture at several resolutions, so the largest is it; aspects that differ, or `rawImagesTruncated`, mean the row claims one fill over a subtree holding more — OPEN QUESTION.

**`export` flattens**, so a node whose subtree holds text reaches the user as an OPEN QUESTION naming each string, and that export waits on the answer — the inventory flags it, `get_metadata` confirms it at export time. Flattening trades live copy for pixels: right for a badge, wrong for a card whose heading and CTA belong in markup.

**Scale** applies to `export` alone — `rawImages` and `svgAssets` are scale-free. Pass `defaultScale` explicitly every time, so a node's own export settings never decide it, and take the largest value satisfying both — or the first alone on a composition, which carries no original source to cap it:

- `≤ 4`, `w × h ≤ 20 MP`, `max(w,h) ≤ 5760` — Files rejects above 20 MP and `image_url` caps at 5760 px, so a blanket 4x fails on square assets.
- **The original source's real resolution**, `source_w ÷ (node_w × w%)` from the fill's rendered percentage — 1.35 for an 832-wide original filling a 616-wide node. Past it Figma interpolates, and upscaling invents no detail.

Filenames kebab-case from the Figma layer name, extension by format. One node, one file.

**Three checks close the phase:**

- **Bounds** — each `export`-sourced file's pixels ÷ its scale equals the node's `w`×`h` within 1 px. Short means the parent frame **clipped** it: report the node and both numbers.
- **Identity** — each asset node-id is its own, distinct from the desktop and mobile frame node-ids the run was given.
- **Count** — shipping files in `assets/` equals inventory rows, and `original-source-*` equals the raster-fill rows; name any miss.

**Source-quality flag:** when an original source is narrower than 2× its slot's rendered CSS width, record it in the plan and the final output with the layer name and both numbers. The remedy is new source art in Figma, not a bigger export.

`assets/UPLOAD.md` closes the phase and keeps the folder self-describing once the run's temp directory is gone:

```
UPLOAD THESE
<file>                  <w>×<h>  → <destination>

DO NOT UPLOAD — archive only
original-source-<file>  <w>×<h>  uncropped
```

## Asset delivery — uploaded and client-changeable

Assets ship as Files uploads the client assigns in the theme editor, so they stay swappable:

| Asset | Export as | Rendered by |
|---|---|---|
| Icon, flat illustration, logo, line art | **SVG** | `image_picker` → `image_tag: widths: '400'` |
| Photo, hero, product shot | **PNG** crop | `image_picker` → `image_tag` |

`widths` is pinned on SVG because width is a CDN no-op on a vector — unpinned, `image_tag` emits ~19 srcset candidates that all resolve to the same file.

Upload the crop and pass no `format:` argument: Shopify's CDN re-encodes to WebP or AVIF per browser and per derivative on its own, so pre-converting only adds a generation of loss and no image encoder ever reaches the ledger. `format: 'pjpg'` is the one value that defeats that negotiation — where existing theme code carries it on a region under measurement, report it.

**Inline branch — on the user's instruction only.** When the user states that an asset carries motion or a hover/scheme colour change, that asset is committed to the theme's `assets/` as `.svg` and rendered by `inline_asset_content`, which is what gives CSS reach into it: `currentColor`, `:hover`, custom properties. Inlined assets are theme code, so the client cannot swap them in the editor — the plan and the final output name each one. A reusable icon wrapper snippet earns a `.agent/COMPONENTS.md` Functions row like any other.

## Hardcode-then-revert

`image_picker` takes no `default`, so a fresh build renders an empty slot and the diff would measure a hole. Verification renders the exported assets directly, then puts the settings back.

**Before hardcoding**, write `HARDCODE-ACTIVE.md` into the visual-check folder: every file path about to be touched, the original markup verbatim, and every temp asset copied into the theme's `assets/`. It is the snapshot the revert restores from.

**Hardcode once**, before the loop rather than per iteration. Injected regions sit between sentinels and temp assets carry the `vh-tmp-` prefix, which is what makes both greppable:

```liquid
{%- comment -%} VERIFY-HARDCODE-START <name> {%- endcomment -%}
<img src="{{ 'vh-tmp-hero.png' | asset_url }}" width="…" height="…" alt="">
{%- comment -%} VERIFY-HARDCODE-END <name> {%- endcomment -%}
```

Iteration fixes go outside the marked region.

**Revert** on every exit — pass, cap, and abort — and before the split check, which exercises the real settings path: restore from the breadcrumb, delete `assets/vh-tmp-*`, delete the breadcrumb.

**Prove it** in the final output: `grep -r VERIFY-HARDCODE` over the theme returns nothing, and no `vh-tmp-*` remains. A revert that fails reports **REVERT FAILED** with the breadcrumb path.

A session that dies mid-verification leaves the breadcrumb and the sentinels in place. Finding either at the start of a run means reverting from it first.

## Phase 1 — Research (read-only on the theme)

**Stranded-hardcode check first** (main agent, before anything else): a `HARDCODE-ACTIVE.md` in any `.agent/figma-shopify-builder/visual-check/*/`, or a `grep -r VERIFY-HARDCODE` hit in the theme, is a hardcode a previous session left live. Revert it per §Hardcode-then-revert and report it before the run continues — a stranded hardcode is the one theme edit this phase makes, and leaving it would corrupt every measurement that follows.

Run the figma-extractor and every standing scanner in parallel, plus tooling detection. Beyond that revert, no theme file is created or modified; the only writes are the missing knowledge docs (§Knowledge docs).

- **Figma extraction** → figma-extractor: both frames via the Figma MCP; exact-values table (implementation targets AND expected values for verification); screenshot scale + pixel dimensions; desktop/mobile differences; repeated-items inventory; asset inventory. Report: `figma-spec.md`.
- **Theme reads** — the knowledge-doc check first (§Knowledge docs), then the scanners it leaves standing: the capability scanner into `.agent/THEME-CAPABILITIES.md`, the two reuse scanners into the shards the main agent merges into `.agent/COMPONENTS.md`, each doc gated on arrival. What each scanner reads, and every fact its rows carry, is its format spec's. Per-run and never in a doc: the template placement anchor (OPEN QUESTION if ambiguous) and the `.git/info/exclude` check — inline reads where the catalog stood its scanner down. Above a spec's sharding threshold each standing scanner splits further into the shards the spec defines, each carrying its file range, and the main agent merges. Either branch, the main agent greps the theme's placeholder treatment inline (§The split). Where globals exist the plan maps each Figma value to them; where they don't, Figma values apply directly — unmapped values get listed, never silently decided.
- **Tooling detection** (main agent, non-mutating checks only): Browser pane availability first, then fallbacks per Browser tiers; run the capture-exactness check; the Agent tool and which tools reach subagents (fix the delegation map); Shopify CLI + `shopify.theme.toml` (desktop app: `shopify theme dev` defined in `.claude/launch.json` so the pane manages the server); Python for the static-approximation fallback; pixel-diff tool: installed `pixelmatch`/`odiff` (PATH or project `node_modules/.bin`) invoked directly, else `npx pixelmatch` / `npx odiff-bin`. Record the render tier, capture source, and any temporary installs required.

**Done when:** `figma-spec.md` exists; both knowledge docs are current and past their gates — produced this run, refreshed incrementally, or read as fresh or newer with that decision recorded; every OPEN QUESTION has been put to the user and answered — including the json-vs-metaobject ask when the source is metafields and the design repeats — and the tooling record names render tier, capture source, diff tool, delegation map, and required temp installs.

## Phase 2 — Plan (stop for approval)

Present the complete plan and stop. Create or modify nothing until the user approves. Approving the plan also approves the listed temporary installs.

The plan states:

- **File**: filename + display name.
- **Schema**, per data source — theme settings: every text/link/image editable with defaults matching the Figma copy; images via `image_picker` per §Asset delivery (Figma images are sizing reference only — the exported assets are what the user uploads and assigns in the theme editor); repeated items as editor blocks. Metafields: which content is metafield-driven (repeated items render from the data, not editor blocks) and which residual settings remain in the schema.
- **Data-source mapping** (metafields only): each Figma content element → the metafield that fills it, with owner type and resolution. For repeated items, the chosen type in FULL — json: namespace.key, owner type, exact item schema (every key: type + the Figma element it fills), malformed-item handling; metaobject: definition type, every field key (type + the Figma element it fills), access path (`list.metaobject_reference` vs `shop.metaobjects`), entry-ordering mechanism. Plus sample values matching the Figma copy, written ready to create in admin, and which fields connect via dynamic sources.
- **The split**: the proposed required settings for the section and for each block type, called out as a decision to confirm, every remaining setting listed as skip-only; the placeholder's markup per breakpoint (theme treatment reused, else the new snippet proposed) with its rendered copy shown; the section-wrapper gap fix where theme CSS leaves one.
- **Typography/color mapping**: table to theme globals, or hardcode note; unmapped values flagged.
- **Breakpoints**: responsive strategy.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append adding it.
- **Asset-export list** (§Asset export, §Asset delivery): every inventoried asset → node-id, kind, source field, format, computed scale, and filename in `.agent/figma-shopify-builder/visual-check/<name>/assets/`, plus the setting that will render it and, for a raster fill, its `original-source-*` twin; `assets/UPLOAD.md` is written from this list. Separately: every asset the user has designated for the inline branch, named as not client-changeable.
- **Template diff**: the exact JSON diff (new key in `sections` + `order` position, or block entry + `block_order` position).
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced so far.
- **Verification approach**: browser tier (with the capture-exactness result), render tier, whether `.claude/launch.json` will be created/updated (a planned file if so), capture widths and scale, key elements for computed-style assertions, pixel-diff tool + pass threshold (default: diff ratio ≤ 1%, anti-aliasing ignored), iteration cap (default: 8 per breakpoint, plateau exit after 2 iterations without improvement), and the exact temporary-install list with method (on-demand runner / project-local / venv) and removal confirmation.
- **Hardcode plan** (§Hardcode-then-revert): every `image_picker` region to be hardcoded, its temp `vh-tmp-` asset, and the file each injection lands in. Approving the plan approves these temporary edits.

**Done when:** the user has approved — required settings confirmed, never assumed into approval.

## Phase 3 — Implement (main agent only)

Touch only planned files; no delegated edits.

- Create the section/block file per the plan: mapped globals where they exist, exact Figma values otherwise; both breakpoints exact.
- Wire the split per the plan: the required-settings check, the `request.design_mode` placeholder branch, no markup on the other side — at item level first, then the whole section when no item survives.
- Metafields source: the Liquid reads the approved metafields — iterating `metafield.value` for json (validating and skipping malformed items), or the metaobject entries' fields per the approved access path and ordering — with exact access syntax verified via the Shopify dev MCP, dynamic sources connected where the editor supports them, and absent or blank required fields taking the split.
- Edit the template JSON exactly as approved, showing the diff again before writing.
- Append the `.agent/` line to `.git/info/exclude` if planned.
- Export the Figma assets per the approved list (§Asset export) into `.agent/figma-shopify-builder/visual-check/<name>/assets/`; run the bounds, identity and count checks; inline-branch assets also go into the theme's `assets/`.

**Done when:** every planned file exists as approved, nothing else changed, and all three export checks pass — bounds, identity, and both counts — with `assets/UPLOAD.md` written.

## Phase 4 — Verify

**Static:** the template JSON still parses; `shopify theme check` on changed files if available; fix errors.

**Visual** — the gate is numeric; never assumed, never skipped silently. At verification start, write `figma-desktop.png` / `figma-mobile.png` into the visual-check folder.

- **Render:** `shopify theme dev` when the CLI + `shopify.theme.toml` exist (desktop app: the Browser pane manages it via `.claude/launch.json`). Otherwise a static approximation via a temporary Liquid engine (e.g. `python-liquid` in a throwaway venv) with schema defaults stubbed and relevant theme CSS inlined — flagged as an approximation; the computed-style and pixel-diff layers still run against it in a real browser (the pane opens the static HTML directly). Blocks render within their host section.
- **Metafield data check** (metafields source, before the loop, main agent): `theme dev` renders the dev store's REAL metafield/metaobject data. Confirm the approved definitions and values exist and match the plan's spec; if they don't, STOP and hand the user the exact definition spec + sample values from the approved plan to create in admin, then resume once populated — verification never runs against an empty or wrong-shape render. The static approximation instead stubs the values with the Figma copy per the plan's mapping.
- **Capture:** Browser pane screenshots if the capture-exactness check passed; otherwise connected browser MCP or installed Chrome; otherwise `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the cleanup ledger). The pane remains the inspection/diagnosis surface regardless.
- **Capture hygiene, before every capture:** exact Figma frame widths at the Figma screenshot's scale — identical pixel dimensions (diff tools require same-size inputs); clip to the section/block container, not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle; stub or hide dynamic content not part of the comparison.

**Hardcode** (main agent, before the loop): breadcrumb, then inject per §Hardcode-then-revert, so the loop measures the design rather than an empty `image_picker`.

**Loop, per breakpoint** — with delegation, steps 1–3 run as ONE visual-verifier call per iteration; the main agent reads `verify-report-<n>.md`, performs step 4, and launches the next round. Without delegation, the loop runs in main as written.

1. **Computed styles first**: getComputedStyle on the key elements vs the Figma values (font-family/size/weight, line-height, letter-spacing, color, background, padding, margin, gap, border-radius). Fix every mismatch before looking at pixels.
2. **Pixel-diff gate**: the planned diff tool (installed direct, else npx) vs the Figma screenshot; record the diff ratio and save the diff image — every iteration.
3. **Live tracking**: immediately overwrite `result-{breakpoint}.png` and `diff-{breakpoint}.png` in the visual-check folder with this iteration's capture and diff. Generate no `clean-`, `section-`, or other render variant.
4. **Diagnosis** (main agent): on failure, read the DIFF IMAGE / mismatch report to localize the mismatch and map it to a cause — metafields source: distinguish a code/style cause from a DATA cause; wrong or missing values get reported to the user with corrected sample values, not patched around in code. Fix, re-render, re-capture, repeat from step 1.

**Revert** (main agent, the moment the loop exits — pass or cap): restore from the breadcrumb and prove it per §Hardcode-then-revert. The split check runs after, on the real settings path.

**Split check** (main agent, once the loop passes): the measured captures are the populated design — then blank the required settings and confirm both halves, block level first, then the whole section: theme editor → the placeholder, dev-server/preview URL → no markup. Restore the content afterward. On the static approximation, stub `request.design_mode` both ways instead.

**Exit:** PASS when the pixel-accurate definition holds at both breakpoints. CAP after 8 iterations per breakpoint, or 2 consecutive iterations without diff-ratio improvement (the main agent tracks count and plateau across verifier reports) — then stop and report the final diff ratio, the diff image, and the suspected remaining cause. The threshold never drops silently. Note the report scope: fidelity is proven at the two captured widths only.

If no render or capture path exists even with temporary installs: revert any live hardcode, then stop and report exactly what's missing.

**Cleanup:** the ledger lists every temporary install (name, method, location). Once verification passes or caps: update the knowledge docs with what this build added, per §Knowledge docs — each append in the table that owns it, both headers refreshed with a dated `updates:` line, and each doc past its completeness gate again; uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall; `.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/` in full — the knowledge docs for the next run, plus `.agent/figma-shopify-builder/visual-check/<name>/` (references, live-updated result/diff images, exported assets) — untracked via `.git/info/exclude`. The user reviews the comparisons before committing, uploads the files `assets/UPLOAD.md` lists per the data source (theme-editor `image_picker` assignment, or Files upload referenced from metafield/metaobject values), and manages the folder themselves. Nothing lands in git except the planned theme files.

**Final output (no explanatory prose):** files created/changed; the revert proof (`grep -r VERIFY-HARDCODE` clean, no `vh-tmp-*` remaining) or **REVERT FAILED** with the breadcrumb path; the split check result (editor placeholder, no markup on live) with the required settings it was run against; [metafields] the final definition spec + sample values as created/confirmed; final diff ratio per breakpoint with pass/cap status; the delegation map; the tooling ledger with removal confirmation (or "nothing installed"); knowledge-doc status, one line each for `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` — created / refreshed incrementally / read as fresh / read as newer and left unchanged, with the gate's reconciled counts or its declared shortfall — plus the post-build appends: the new build's catalog entry and its inventory row(s), the new custom elements, the new Animations rows, and each doc's `updates:` line; the path `.agent/figma-shopify-builder/visual-check/<name>/` with a one-line inventory (references, result/diff images, shipping crops and `original-source-*` counts per format, `UPLOAD.md`) and exclusion confirmation; any source-quality flags; any inline-branch assets, named as not client-changeable.

## Rules

- Read every file before editing; show a diff before overwriting anything existing.
- Ask instead of assuming — including the json-vs-metaobject choice when the source is metafields, the data repeats, and the user hasn't specified it.
- Required settings are the user's call — proposed in the plan per section and per block type, confirmed at approval; every other blank field is just skipped markup.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- Metafield data must exist and match the spec before verification — otherwise stop and hand over the spec.
- The Browser pane leads when available; fallbacks apply only when it's absent or fails the capture-exactness check.
- The pixel-diff gate is mandatory: passing is numeric, and the threshold never drops silently.
- Only `result-desktop.png`, `result-mobile.png`, `diff-desktop.png`, and `diff-mobile.png` are generated at the visual-check root; overwrite them every iteration and generate no `clean-`, `section-`, or other render variant.
- `assets/` holds the design's crop for each Figma node, each raster's `original-source-*` beside it; reference captures at the folder root hold the frame. The bounds and identity checks keep a clipped or whole-frame render out.
- Assets ship as Files uploads the client assigns, so they stay swappable; the inline branch runs only where the user asked for it, and every inlined asset is named as not client-changeable.
- Upload the crops and let the CDN pick the format — no image encoder reaches the ledger.
- A hardcode is breadcrumbed before it exists and reverted on every exit — pass, cap, and abort — with the grep proof in the final output.
- `.agent/` lives at the repo root, is always excluded via `.git/info/exclude`, and is never committed.
- Knowledge docs first: read `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` before any theme scan and run each spec's `format:` ladder on it; a scanner that runs writes its doc back, past its completeness gate, before the task continues. An explicit user refresh always wins.
- Knowledge docs stay current: a passing build appends its section/block, its custom elements, and its reusable motion into the tables that own them, records the run on each doc's `updates:` line, and re-runs each gate before the final report. A doc at a higher `format:` keeps every byte and the appends are named in the output instead.
- Verify Liquid/schema syntax — including metafield and metaobject access — via the Shopify dev MCP instead of guessing.
- CLI tools: check installed first (on PATH, project dep, or npm script) — installed → invoke directly (`shopify theme dev`, `npm run …`), no runner. Not installed → on-demand runner (`npx` / `pnpm dlx` / `bunx` / `pipx run`), never a global install. Runner impossible (persistent binary/venv needed) → project-local or venv, on the ledger.
- Leave the machine as it was found — the retained `.agent/` tree (knowledge docs + visual-check) is the one deliberate leftover, kept for the next run, review, and asset uploads.

## Usage

```
Use the figma-shopify-builder skill.
- Desktop: <figma link with node-id>
- Mobile: <figma link with node-id>
- Type: section
- Template: templates/index.json
- Place: after "Autoplay Slider"
- Data source: theme settings
  (or: metafields — product, custom.testimonials, multiple: metaobject)
  (or: metafields — page, custom.faq_items, multiple: json)
```
