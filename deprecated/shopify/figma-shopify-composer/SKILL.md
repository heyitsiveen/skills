---
name: figma-shopify-composer
description: Compose a pixel-accurate recreation of a Figma design from a theme's EXISTING sections, blocks, and settings — assemble and configure what the theme already ships, writing template JSON only: no new code, no new files, no new settings, no schema edits. Use when the user wants a Figma frame recreated by reusing existing sections or blocks, or asks to compose/assemble a design from existing settings only. Building a NEW section or block file from Figma is figma-shopify-builder's job — this skill only configures what already exists. Fidelity is measured — computed styles plus pixel diff against the Figma frames — never eyeballed.
---

# Figma → Shopify Composer

Recreate two Figma frames by composing the theme's existing sections, blocks, and settings — configuration, not code — and prove it pixel-accurate by measurement. The palette is fixed to what the theme already ships, so fidelity is forecast before anything is built and measured against that forecast after. Four phases — research (read-only on the theme), plan (stop for approval), implement (template JSON only), verify (numeric gate) — then cleanup that leaves the machine as found. Nothing is created or modified before plan approval except knowledge docs under `.agent/` (§Knowledge docs) and the revert of a hardcode a previous session stranded (§Phase 1); the deliberate leftovers are the visual-check folder and the knowledge docs.

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
- The one exception is transient: verification's `vh-tmp-` assets, which live in the theme's `assets/` only between the hardcode and its revert (§Hardcode-then-revert). The build surface is what SURVIVES the run.
- Prefer settings that inherit from global theme settings (colors, typography, radius, borders, buttons) over per-instance raw values — the result stays wired into the theme's design system.

## Pixel-accurate is a measured result

The composition passes when, per breakpoint:

1. Every checked computed style matches its Figma value.
2. The image diff ratio against the Figma screenshot is ≤ 1% with anti-aliasing ignored, measured ON UNMASKED REGIONS — every masked region is individually approved in the plan (accepted gaps, and image regions no hardcode tier reaches — §Hardcode-then-revert).
3. Residual diff pixels are confirmed FROM THE DIFF IMAGE to be text-rasterization noise — Figma and Chromium rasterize fonts differently, so a literal 0% is unreachable. Layout, color, or spacing differences are never "noise".

The palette is fixed to existing capabilities, so the plan states upfront what will match EXACTLY, what APPROXIMATES, and what is UNACHIEVABLE without new code; the user approves that fidelity forecast before anything is written. Side-by-side eyeballing is for diagnosis only; passing is numeric.

## Browser tiers

**Primary: the Claude Code Desktop Browser pane** (desktop app with Browser enabled). Claude drives it directly — screenshots, DOM/computed-style inspection, interaction — and manages the dev server via `.claude/launch.json` (local dev servers need no site approval; preview/live store URLs are external sites and trigger a one-time permission card — Allow once / Always allow).

**Capture-exactness check:** the measured diff needs captures at the exact Figma frame widths and scale, with identical pixel dimensions, clipped to the composed region. Confirm the pane's screenshots can honor that; if not, the pane still does inspection and diagnosis while the MEASURED captures fall to the first fallback that can.

**Fallbacks, in order:** connected browser MCP (Chrome DevTools MCP / Playwright MCP) → installed Chrome → temporary Playwright via npx.

## Delegation

Bounded research and measurement go to subagents — isolated workers with their own context windows that return only a final report. Delegation earns its keep most in the capability inventory: scanning every section's schema would otherwise flood the main conversation. Delegation multiplies tokens: skip it for trivially small reads.

Prefer the named custom agents `figma-extractor`, `theme-scanner`, and `visual-verifier` when installed in `~/.claude/agents/` or `.claude/agents/` — their definitions add tool-enforced restrictions (e.g. `disallowedTools: Write, Edit` on the verifier). Otherwise run the built-in general-purpose subagent with the embedded prompts below; in that fallback the no-theme-edits rule is instruction-enforced, so each prompt states it explicitly.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the Figma MCP / browser tools reach subagents (subagents inherit internal + MCP tools by default; the Browser pane's preview tools may be main-session-only). Any role whose tools don't reach a subagent runs in the main conversation instead.

**Handoff protocol:** subagents can't see the conversation and can't ask the user questions — every delegation prompt carries its exact inputs (node-ids, file paths, the requirements list, the approved mask list, capture specs); every worker writes FULL findings to a report file in the temp working directory (the capability scanner writes its knowledge doc instead, and the two reuse scanners write the shards the main agent merges into theirs — §Knowledge docs) and returns a short summary; ambiguities come back as OPEN QUESTIONS for the main agent to put to the user. The temp working directory is created per run (use the session scratchpad when available) and is deleted at cleanup.

**Never delegated:** the requirements-to-capabilities matching (1c — the synthesis that feeds the fidelity forecast), planning and every user approval (forecast, mask list, global-value changes), all implementation edits, and the diagnosis/fix half of the verification loop.

| Role | Phase | Report |
|---|---|---|
| figma-extractor | 1a, parallel | `figma-spec.md` |
| theme-scanner — capability catalog | 1b, parallel | `.agent/THEME-CAPABILITIES.md` (canonical; shards `{temp-dir}/THEME-CAPABILITIES-<n>.md`, merged into it by the main agent) |
| theme-scanner — reuse inventory, JavaScript side | 1b, parallel | `{temp-dir}/COMPONENTS-<n>.md` |
| theme-scanner — reuse inventory, Liquid/CSS side | 1b, parallel | `{temp-dir}/COMPONENTS-<n>.md` (every side's report merged into `.agent/COMPONENTS.md` by the main agent) |
| visual-verifier (never edits theme files) | 4, one call per iteration | `verify-report-<n>.md` |

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

For each node-id call get_design_context and get_screenshot, then compile:
1. Exact-values table per breakpoint: typography (family, size, weight,
   line-height, letter-spacing), colors, spacing (padding/margin/gap), sizes,
   border-radii, borders, image dimensions, frame width. These are the
   settings-configuration targets AND the expected values for computed-style
   assertions — record exactly.
2. Layout structure per breakpoint and every desktop vs mobile difference
   (column counts, stacking, order, visibility, alignment — e.g. 2 columns on
   desktop → 1 column on mobile).
3. Each screenshot's scale (1x/2x) and pixel dimensions — captures must match
   them exactly for the pixel diff.
4. Asset inventory — one row per exportable asset: layer name | node-id |
   kind (raster fill / vector / composition) | the node's w×h | for a raster
   fill, the fill's rendered percentage of its node (the `w-`/`h-` values
   get_design_context emits) and whether the subtree holds text. Phase 3
   exports from the node-id, so every asset carries its own; text in the
   subtree is an OPEN QUESTION, since exporting flattens it.
5. The REQUIREMENTS LIST — the distilled design: layout structure per
   breakpoint; each content element (headings, text, CTAs/buttons, images,
   badges); each style requirement (colors, typography, radius, borders,
   spacing, alignment).

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

### visual-verifier prompt

```
You are measuring one verification iteration of a Shopify composition
(existing sections/blocks configured via template JSON) against its Figma
reference. You NEVER edit theme files — measure, record, report only.

Iteration: {n} — breakpoint {desktop|mobile}, width {w}px, scale {s}, expected
capture dimensions {W}x{H}px
Render at: {dev-server-url | preview-url}
Clip to the composed region: {selector for the added section instance(s) or
the host section}
Figma reference: .agent/figma-shopify-composer/visual-check/{composition-name}/
figma-{breakpoint}.png
Approved mask list: {region → reason, from the approved plan} — apply exactly;
never add or grow a mask
Expected values: {temp-dir}/figma-spec.md
Capability map for tagging: .agent/THEME-CAPABILITIES.md + the approved
settings map
Key elements to assert: {list from the approved plan}
Diff tool: {pixelmatch … | odiff-bin …} (installed direct, else via npx; anti-aliasing ignored)

1. Capture hygiene, then capture: viewport at the exact width and scale above;
   animations/transitions disabled; wait for document.fonts.ready + network
   idle; clip to the composed region. The capture's pixel dimensions must
   equal the reference's exactly.
2. Computed styles: getComputedStyle on each key element vs the expected
   values (font-family/size/weight, line-height, letter-spacing, color,
   background, padding, margin, gap, border, border-radius). Record every
   mismatch: element, property, expected, actual.
3. Pixel diff: apply the approved masks, run the diff tool vs the reference,
   record the diff ratio, save the diff image.
4. Overwrite .agent/figma-shopify-composer/visual-check/{composition-name}/
   result-{breakpoint}.png and diff-{breakpoint}.png with THIS
   iteration's capture and diff.

Write the FULL report to {temp-dir}/verify-report-{n}.md: diff ratio, mismatch
table with every mismatch TAGGED either "settings-fixable per the capability
map" (name the setting) or "undeclared gap", largest diff regions and where
they sit. Return only the diff ratio, mismatch count by tag, and one line on
the biggest offender.
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

`.agent/figma-shopify-composer/visual-check/<composition-name>/` in the theme repo, `<composition-name>` kebab-cased from the Figma frame name (e.g. `.agent/figma-shopify-composer/visual-check/hero/`). The root has exactly three image classes:

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

Assets ship as Files uploads the client assigns to the existing sections' `image_picker` settings in the theme editor, so they stay swappable:

| Asset | Export as | Rendered by |
|---|---|---|
| Icon, flat illustration, logo, line art | **SVG** | the section's `image_picker` |
| Photo, hero, product shot | **PNG** crop | the section's `image_picker` |

Upload the crop: Shopify's CDN re-encodes to WebP or AVIF per browser and per derivative on its own, so pre-converting only adds a generation of loss and no image encoder ever reaches the ledger. Where the host section pipes an SVG through an unpinned `image_tag`, it emits ~19 srcset candidates that all resolve to the same file, and where its code carries `format: 'pjpg'` it forfeits WebP and AVIF entirely — both are existing section code, so both are reported as gaps rather than edited.

**Inline branch:** unreachable here. When the user designates an asset as carrying motion or a hover/scheme colour change, that needs committed theme code — report it as a gap and defer it to the figma-shopify-builder skill.

## Hardcode-then-revert

`image_picker` takes no `default`, so an assigned-by-hand image region renders empty and the diff would measure a hole. Verification renders the exported assets directly, then puts the settings back.

**Before hardcoding**, write `HARDCODE-ACTIVE.md` into the visual-check folder: every file path about to be touched, the original template JSON verbatim, and every temp asset copied into the theme's `assets/`. It is the snapshot the revert restores from.

**Inject once**, before the loop rather than per iteration, at the first tier that reaches the region:

1. **The section's or block's own `liquid` setting** in the template JSON — renders in the right DOM position and stays inside the template-only build surface. The capability inventory flags which sections expose one.
2. **A temporary Custom Liquid section** in `order`, emitting a `{% style %}` block alone that background-images the real element in place — for host sections with no `liquid` setting, and only where the empty picker still renders a targetable element.
3. **Mask the region** and record the reason on the mask list, when neither tier reaches it.

Injected regions sit between sentinels and temp assets carry the `vh-tmp-` prefix, which is what makes both greppable:

```liquid
{%- comment -%} VERIFY-HARDCODE-START <name> {%- endcomment -%}
<img src="{{ 'vh-tmp-hero.png' | asset_url }}" width="…" height="…" alt="">
{%- comment -%} VERIFY-HARDCODE-END <name> {%- endcomment -%}
```

Iteration fixes go outside the marked region — tier 2's temporary section is removed wholesale at revert, so a settings fix parked inside it would go with it.

Tiers 1 and 2 copy temp assets into the theme's `assets/`, the one point where this skill writes a theme file. They are transient by construction: the revert deletes them, and the final output reports that no theme file remains rather than that none was created.

**Revert** on every exit — pass, cap, and abort: restore from the breadcrumb, delete `assets/vh-tmp-*`, remove the temp Custom Liquid section from `order`, delete the breadcrumb.

**Prove it** in the final output: `grep -r VERIFY-HARDCODE` over the theme returns nothing, no `vh-tmp-*` remains, and the template JSON matches the breadcrumb's original. A revert that fails reports **REVERT FAILED** with the breadcrumb path.

A session that dies mid-verification leaves the breadcrumb and the sentinels in place. Finding either at the start of a run means reverting from it first.

## Phase 1 — Research (read-only on the theme)

**Stranded-hardcode check first** (main agent, before anything else): a `HARDCODE-ACTIVE.md` in any `.agent/figma-shopify-composer/visual-check/*/`, or a `grep -r VERIFY-HARDCODE` hit in the theme, is a hardcode a previous session left live. Revert it per §Hardcode-then-revert and report it before the run continues — a stranded hardcode is the one theme edit this phase makes, and leaving it would corrupt every measurement that follows.

Run 1a and every standing scanner of 1b in parallel, then match in main. Beyond that revert, no theme file is created or modified; the only writes are the knowledge docs (§Knowledge docs).

- **1a. Figma requirements** → figma-extractor: both frames via the Figma MCP; exact-values table (the settings-configuration targets AND the expected values for verification's computed-style assertions); per-breakpoint layout structure and desktop/mobile differences; screenshot scale + pixel dimensions; asset inventory; the distilled REQUIREMENTS LIST. Report: `figma-spec.md`.
- **1b. Theme knowledge** — the knowledge-doc check first (§Knowledge docs), then the scanners it leaves standing: the capability scanner into `.agent/THEME-CAPABILITIES.md`, the two reuse scanners into the shards the main agent merges into `.agent/COMPONENTS.md`, each doc gated on arrival. What each scanner reads, and every fact its rows carry, is its format spec's. Per-run and never in a doc: the target-template placement anchor (OPEN QUESTION if ambiguous) and the `.git/info/exclude` check — inline reads where the catalog stood its scanner down. Above a spec's sharding threshold each standing scanner splits further into the shards the spec defines, each carrying its file range, and the main agent merges. Current global values are read live from `config/settings_data.json` in main — the catalog carries the schema's declared defaults, which are a different fact.
- **1c. Match requirements to capabilities** (main agent, from `figma-spec.md` + `.agent/THEME-CAPABILITIES.md`): for every requirement, the existing capability that achieves it — which section type (or stack of section instances), which block types, which settings and values, per breakpoint. Where a style value should come from a global, check whether the CURRENT global value already equals the Figma value — if it doesn't, that is a decision point, never a silent change. Anything with no existing capability is a GAP: record the closest achievable approximation and its visible cost, and whether an existing per-instance custom CSS/Liquid setting (an existing setting, so within the constraint) could close it.
- **1d. Tooling detection** (main agent, non-mutating checks only): Browser pane availability first, then fallbacks per Browser tiers; run the capture-exactness check; the Agent tool and which tools reach subagents (fix the delegation map). Render path: Shopify CLI + `shopify.theme.toml` → `shopify theme dev` (desktop app: defined in `.claude/launch.json` so the pane manages the server); otherwise a preview/live store URL. There is NO static-render fallback — composed existing sections depend on the full theme runtime (snippets, global settings, theme CSS/JS), which a local Liquid engine cannot reproduce. Diff tool: installed `pixelmatch`/`odiff` (PATH or project `node_modules/.bin`) invoked directly, else `npx pixelmatch` / `npx odiff-bin`. Record the tiers and any temporary installs required.
- **1e. Ask**: put anything still ambiguous — including OPEN QUESTIONS from the reports — to the user as concise questions before planning.

**Done when:** `figma-spec.md` exists; both knowledge docs are current and past their gates — produced this run, refreshed incrementally, or read as fresh or newer with that decision recorded; every requirement is matched to a capability or recorded as a gap; every OPEN QUESTION is answered; and the tooling record names browser tier, capture source (exactness result), render path, diff tool, delegation map, temp dir, and the exclude status.

## Phase 2 — Plan (stop for approval)

Present the complete plan and stop. Create or modify nothing until the user approves. Approval covers the temporary installs, the mask list, and any global-value change or custom-CSS usage the plan explicitly lists.

- **Composition**: which existing section type(s) — one instance or a stack — and/or which existing block types, in what order.
- **Settings map**: for every chosen section instance and block, every setting id → value, per breakpoint where responsive settings exist, with the Figma value it satisfies. Text/link settings carry the Figma copy. Image settings stay unassigned — the user uploads the exported assets via the theme editor and assigns them (§Asset delivery); verification measures those regions through the hardcode, and only a region no injection tier reaches goes on the mask list.
- **Global-inheritance table**: requirement → global-connected setting used → whether the current global value already matches Figma. Where it doesn't, the user picks one: a per-instance override setting (if one exists) / changing the global VALUE — flagged loudly, it restyles the whole storefront / accepting the current global as an approved gap.
- **Fidelity forecast**: EXACT (fully met by existing capabilities), APPROXIMATE (closest achievable, visible cost described), UNACHIEVABLE without new code — accept as a gap or defer to the figma-shopify-builder skill. A per-instance custom CSS/Liquid setting proposed as a gap-closer is its own flagged line item.
- **Mask list**: every approved gap, plus the tier-3 image regions no hardcode reaches, each with its reason. Image regions a hardcode tier does reach are measured, not masked. The gate applies to everything unmasked.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append adding it.
- **Asset-export list** (§Asset export, §Asset delivery): every inventoried asset → node-id, kind, source field, format, computed scale, and filename in `.agent/figma-shopify-composer/visual-check/<composition-name>/assets/`, plus the section setting the user will assign it to and, for a raster fill, its `original-source-*` twin; `assets/UPLOAD.md` is written from this list.
- **Hardcode plan** (§Hardcode-then-revert): per image region, the injection tier that reaches it and its temp `vh-tmp-` asset; tier-3 regions carry their mask reason.
- **Template diff**: the exact JSON — new entries in `sections` (type = existing section file, with the settings map and `blocks` + `block_order`) inserted into `order` at the input placement; or, for a block composition, the block entries and `block_order` position inside the host section instance.
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced so far.
- **Verification approach**: browser tier (with the capture-exactness result), render path, whether `.claude/launch.json` will be created/updated (a planned file if so), capture widths and scale, key elements for computed-style assertions, pixel-diff tool + pass threshold (default: diff ratio ≤ 1% on unmasked regions, anti-aliasing ignored), iteration cap (default: 8 per breakpoint, plateau exit after 2 iterations without improvement), and the exact temporary-install list with method (on-demand runner / project-local / venv) and removal confirmation.

**Done when:** the user has approved.

## Phase 3 — Implement (main agent only)

Touch only planned files; no delegated edits.

- Edit the target template JSON exactly as approved — section entries with their settings maps and block configurations at the approved position — showing the diff again before writing.
- Apply any approved global-value change in `config/settings_data.json` exactly as listed in the plan, and nothing beyond it.
- Append the `.agent/` line to `.git/info/exclude` if planned.
- Export the Figma assets per the approved list (§Asset export) into `.agent/figma-shopify-composer/visual-check/<composition-name>/assets/`; run the bounds, identity and count checks.

**Done when:** every planned edit is in place as approved and nothing else changed — no new theme files, no new settings, no edited section/block/snippet/CSS/JS file — and all three export checks pass — bounds, identity, and both counts — with `assets/UPLOAD.md` written.

## Phase 4 — Verify

**Static:** the target template (and `config/settings_data.json`, if edited) still parses as valid JSON; `shopify theme check` on changed files if available; fix errors.

**Visual** — the gate is numeric; never assumed, never skipped silently. At verification start, write `figma-desktop.png` / `figma-mobile.png` into the visual-check folder.

- **Render:** `shopify theme dev` when available (Browser pane manages it via `.claude/launch.json` in the desktop app); otherwise the preview/live store URL in the browser. There is no static fallback — composed existing sections require the full theme runtime. If neither path is possible, stop and report exactly what's missing.
- **Capture:** Browser pane screenshots if the capture-exactness check passed; otherwise connected browser MCP or installed Chrome; otherwise `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the cleanup ledger). The pane remains the inspection/diagnosis surface regardless.
- **Capture hygiene, before every capture:** exact Figma frame widths at the Figma screenshot's scale — identical pixel dimensions (diff tools require same-size inputs); clip to the composed region (the added section instance(s) or host section), not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle; apply the approved mask list so the diff measures only what is supposed to match.

**Hardcode** (main agent, before the loop): breadcrumb, then inject at the planned tier per §Hardcode-then-revert, so the loop measures the design rather than an empty `image_picker`.

**Loop, per breakpoint** — with delegation, steps 1–3 run as ONE visual-verifier call per iteration; the main agent reads `verify-report-<n>.md`, performs step 4, and launches the next round. Without delegation, the loop runs in main as written.

1. **Computed styles first**: getComputedStyle on the key elements vs the Figma values (font-family/size/weight, line-height, letter-spacing, color, background, padding, margin, gap, border, border-radius). A mismatch is fixed by ADJUSTING SETTINGS VALUES in the template JSON per the capability map — never by editing section/block code. If no setting can move the value, it's an undeclared gap: surface it, don't hack it.
2. **Pixel-diff gate**: the planned diff tool (installed direct, else npx) vs the Figma screenshot with the approved masks applied; record the diff ratio and save the diff image — every iteration.
3. **Live tracking**: immediately overwrite `result-{breakpoint}.png` and `diff-{breakpoint}.png` in the visual-check folder with this iteration's capture and diff. Generate no `clean-`, `section-`, or other render variant.
4. **Diagnosis** (main agent): on failure, read the DIFF IMAGE / mismatch report to localize the mismatch and map it to a settings value (or an undeclared gap), fix, re-render, re-capture, repeat from step 1.

**Revert** (main agent, the moment the loop exits — pass or cap): restore from the breadcrumb and prove it per §Hardcode-then-revert, before anything else.

**Exit:** PASS when the pixel-accurate definition holds at both breakpoints — the gate passes on unmasked regions and every masked region is on the approved list. CAP after 8 iterations per breakpoint, or 2 consecutive iterations without diff-ratio improvement (the main agent tracks count and plateau across verifier reports) — then stop and report the final diff ratio, the diff image, the suspected remaining cause, and whether it is a settings issue or an undeclared capability gap. The threshold never drops and the mask list never grows silently. Note the report scope: fidelity is proven at the two captured widths only.

**Post-write knowledge refresh:** after the approved template or settings JSON write, refresh both shared knowledge docs against the current branch using their format ladders. Reconcile the changed template scan and `git:` line, append the run to `updates:`, and rerun both completeness gates before the final report. A higher-format doc is read-as-newer and left byte-for-byte unchanged.

**Cleanup:** the ledger lists every temporary install (name, method, location). Once verification passes or caps: uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall; `.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/` in full — the knowledge docs for the next run, plus `.agent/figma-shopify-composer/visual-check/<composition-name>/` (references, live-updated result/diff images, exported assets) — untracked via `.git/info/exclude`. The user reviews the comparisons before committing, uploads the files `assets/UPLOAD.md` lists through the theme editor and assigns them to the image settings, and manages the folder themselves. Nothing lands in git except the planned template/config edits.

**Final output (no explanatory prose):** files changed (expected: the template JSON; possibly `settings_data.json`, the `.git/info/exclude` append, `.claude/launch.json`) with confirmation that NO theme file REMAINS beyond those and NO schemas were edited; the revert proof (`grep -r VERIFY-HARDCODE` clean, no `vh-tmp-*` remaining, template JSON matching the breadcrumb original) or **REVERT FAILED** with the breadcrumb path; final diff ratio per breakpoint with pass/cap status; the masked-region list with each mask's approval reason; any source-quality flags; any assets deferred to figma-shopify-builder for the inline branch; the fidelity outcome vs the forecast (EXACT / APPROXIMATE / undeclared gaps discovered); the delegation map; the tooling ledger with removal confirmation (or "nothing installed"); knowledge-doc status, one line each for `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` — created / refreshed incrementally / read as fresh / read as newer and left unchanged, with the gate's reconciled counts or its declared shortfall; the path `.agent/figma-shopify-composer/visual-check/<composition-name>/` with a one-line inventory (references, result/diff images, shipping crops and `original-source-*` counts per format, `UPLOAD.md`) and exclusion confirmation.

## Rules

- Read every file before editing; show a diff before overwriting anything existing.
- Ask instead of assuming.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- The template JSON (plus approved `settings_data.json` values) is the only build surface; `.git/info/exclude`, `.claude/launch.json`, and the `.agent/` tree are the only other writable paths, per the plan. Section/block/snippet/CSS/JS files stay read-only — no new theme files, no new settings, no schema edits. Verification's `vh-tmp-` assets are the one transient exception and the revert removes them.
- `assets/` holds the design's crop for each Figma node, each raster's `original-source-*` beside it; reference captures at the folder root hold the frame. The bounds and identity checks keep a clipped or whole-frame render out.
- Upload the crops and let the CDN pick the format — no image encoder reaches the ledger.
- A hardcode is breadcrumbed before it exists and reverted on every exit — pass, cap, and abort — with the grep proof in the final output.
- Knowledge docs first: read `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` before any theme scan and run each spec's `format:` ladder on it; a scanner that runs writes its doc back, past its completeness gate, before the task continues. An explicit user refresh always wins.
- This skill produces both shared docs, so a theme missing one is scanned rather than worked around, and a doc at a higher `format:` is read as it stands and named in the output.
- Never change a global setting VALUE silently — globals restyle the entire storefront; every global change is an explicit, individually-approved plan line.
- A per-instance custom CSS/Liquid setting is used only when the theme already has it AND the plan flagged it.
- Prefer global-connected settings over raw per-instance values when both can hit the Figma value.
- Verify template/schema JSON structure via the Shopify dev MCP instead of guessing.
- The Browser pane leads when available; fallbacks apply only when it's absent or fails the capture-exactness check.
- The pixel-diff gate is mandatory: passing is numeric, the threshold never drops, and the mask list never grows silently.
- Only `result-desktop.png`, `result-mobile.png`, `diff-desktop.png`, and `diff-mobile.png` are generated at the visual-check root; overwrite them every iteration and generate no `clean-`, `section-`, or other render variant.
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
