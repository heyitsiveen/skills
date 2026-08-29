---
name: shopify-app-restyle
description: Restyle a third-party Shopify app's block or widget to match a Figma design with scoped !important CSS overrides — the app's own code and assets are never touched. Use when the user wants an installed app's widget or app block (product options, reviews, bundles, gift wrap, …) restyled, overridden, or customized to Figma frames, or asks for pixel-accurate styling of app-injected UI. The overrides read from a design spec extracted from the Figma frames, report computed styles against it per breakpoint and per state, and save the rendered result for review.
---

# Shopify App Restyle

Restyle a third-party app's storefront widget to match two Figma frames without touching the app: scoped `!important` overrides in the theme, written from a design spec extracted from those frames. Four phases — research (read-only on the theme), plan (an audit trail, not a checkpoint), implement, render and report — then cleanup that leaves the machine as found. The run is **gate-free**: nothing pauses for approval, not even the plan; the only stops are a missing input, genuine ambiguity, or the live publish swap ([environment-mismatch](environment-mismatch.md) step 8, which never runs without the user's explicit go-ahead). The deliberate leftovers are the visual-check folder and the knowledge docs (§Knowledge docs).

## Inputs

Collect before starting; ask for any that are missing.

1. **Figma desktop link** — with node-id.
2. **Figma mobile link** — with node-id.
3. **App name, exactly as installed** — e.g. "Easify Options"; finds the app-block entry in the template and the widget's container/classes/stylesheets fast.
4. **Target template** — e.g. `templates/product.json`.
5. **Placement** — which section hosts the app block and where it sits in that section's `block_order` (before/after which block, by customizer label or type). Locates the widget and verifies/fixes its position.
6. **Page or product URL to inspect** — optional; ask only if the widget's rendering is product-specific and the target is ambiguous.

## The design spec is the authority

`figma-spec.md` — the **design spec** — is the single document the overrides read from. Every declaration in the override stylesheet traces to it: the exact-values table, the desktop/mobile differences, the layout intent, the stacking and overlap, the group rhythm, the widget states, and the asset inventory. It is extracted once, in Phase 1, quoted inline in the plan, and never re-derived mid-run; a value that is not in it is an OPEN QUESTION, not a judgement call.

Pixel accuracy is still the goal. It is no longer a claim the skill makes on its own behalf: the run ends with a **style report** — computed styles against the design spec's values, per breakpoint AND per state — plus the rendered result saved to the visual-check folder next to the Figma references, one render per state, and the user judges the result by eye.

The per-state axis is this skill's own: an app widget changes appearance on interaction, and state-dependent styling is exactly where an override breaks, so Phase 4's capture hygiene, its `style-reporter` call, and its style report all run per state as well as per breakpoint.

## Browser tiers

**Primary: the Claude Code Desktop Browser pane** (desktop app with Browser enabled). Claude drives it directly — screenshots, DOM/computed-style inspection, clicking, form filling — and manages the dev server via `.claude/launch.json` (local dev servers need no site approval). Preview/live store URLs are external sites: expect a one-time permission card (Allow once / Always allow). Enable "Persist sessions" when the storefront is password-protected so the cookie survives restarts. When available, it does the whole capture job — including the interactions that reproduce each state.

**Fallbacks, in order:** connected browser MCP (Chrome DevTools MCP / Playwright MCP) → installed Chrome → temporary Playwright via npx.

## Delegation

Bounded research and measurement go to subagents — isolated workers with their own context windows that return only a final report — so bulk Figma payloads, DOM dumps, and the result screenshots stay out of the main conversation, and independent research runs in parallel. Delegation multiplies tokens: skip it for trivially small reads.

Prefer the named custom agents `figma-extractor`, `widget-inspector`, and `style-reporter` when installed in `~/.claude/agents/` or `.claude/agents/` — their definitions add tool-enforced restrictions (e.g. `disallowedTools: Write, Edit` on the style reporter). Otherwise run the built-in general-purpose subagent with the embedded prompt below; in that fallback the no-theme-edits rule is instruction-enforced, so the prompt states it explicitly.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the Figma MCP / browser tools reach subagents (subagents inherit internal + MCP tools by default; the Browser pane's preview tools may be main-session-only). Any role whose tools don't reach a subagent runs in the main conversation instead.

**Handoff protocol:** subagents can't see the conversation and can't ask the user questions — every delegation prompt carries its exact inputs (node-ids, selectors, file paths, the design spec's path, capture specs); every worker writes FULL findings to a report file in the temp working directory (the widget-inspector writes the app-widget doc plus a per-run report — §Knowledge docs) and returns a short summary; ambiguities come back as OPEN QUESTIONS for the main agent to put to the user. The temp working directory is created per run (use the session scratchpad when available) and is deleted at cleanup.

**Never delegated:** planning, user approvals, all implementation edits, the environment-mismatch steps that need the user (6 and 8), and the correction round that follows the style report.

| Role | Phase | Report |
|---|---|---|
| figma-extractor | 1, parallel | `figma-spec.md` — the design spec |
| widget-inspector (read-only on the theme; skips re-derivation when the knowledge docs are fresh) | 1, parallel | `app-widget-<app-handle>.md` (§Knowledge docs) + per-run `theme-widget-report.md` |
| style-reporter (never edits theme files) | 4, once per breakpoint and state, plus the correction round's re-check | `style-report-<breakpoint>[-<state>].md` |

### figma-extractor prompt

```
You are extracting a Figma design spec for restyling a third-party Shopify app
widget. Work only from the Figma MCP; do not read or modify the theme repo.

Frames:
- Desktop: {figma-desktop-link} (node-id {desktop-node-id})
- Mobile: {figma-mobile-link} (node-id {mobile-node-id})

This document is the DESIGN SPEC: the single authority the override stylesheet
reads from. Nothing is re-derived from Figma later, so anything the restyle
needs must be in it — and anything you are unsure of is an OPEN QUESTION,
never a guess.

For each node-id call get_design_context and get_screenshot, then compile:
1. Exact-values table per breakpoint: typography (family, size, weight,
   line-height, letter-spacing), colors, spacing (padding/margin/gap), sizes,
   border-radii, frame width. These are the CSS override targets AND the
   expected values for computed-style assertions — record exactly.
2. Desktop vs mobile differences (stacking, order, visibility, alignment).
3. Layout intent, per breakpoint: which elements form a row, a grid or a stack,
   the group each belongs to, and how that grouping changes between desktop and
   mobile (a desktop 3-up row becoming a mobile stack, and in what order).
4. Stacking and overlap: z-order wherever elements sit over one another, which
   element is on top, and the offset and overlap amount of each overlapping pair.
5. Group rhythm: the spacing BETWEEN sibling groups, per breakpoint — not only
   per-element margins. Give the gap between each pair of adjacent groups and
   name the repeating interval where one exists.
6. Every widget state visible in the frames — selected option, open dropdown,
   hover, error, … — and which values change in each. Name the interaction that
   reproduces each one. The render-and-report phase captures and asserts per
   state, so a state you do not record is a state nobody checks.
7. Asset inventory — one row per exportable asset: layer name | node-id |
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

Sections 3, 4 and 5 are WRITTEN FROM THE SCREENSHOT — read the image, describe
what the widget actually does — and EVERY claim in them is backed by a value
from get_design_context, cited inline (the layout mode, the item spacing, the
absolute position, the bounds). A claim you cannot back with a value is an
OPEN QUESTION, not an assertion. The screenshot is the source of the structure;
the design context is the source of the numbers.

Open the document with this header line, verbatim, before section 1:

    producer: shopify-app-restyle — write surface: its own override
    stylesheet only — the app's own code and assets are never touched

Write the FULL findings to {temp-dir}/figma-spec.md with an OPEN QUESTIONS
section at the end for anything ambiguous. Return only a 3–5 line summary plus
the open questions.
```

### widget-inspector prompt

```
You are inspecting a live third-party app widget on a Shopify storefront, plus
the theme that hosts it. READ-ONLY on the theme: your only writes are the
knowledge docs named below and your per-run report.

App name (as installed): {app-name}
Page to inspect: {url}
Browser: {browser-tier}
Theme repo: {repo-path}
Target template: {template-path}
Requested placement: {placement}
Capture widths: desktop {w}px / mobile {w}px (the Figma frame widths)
Knowledge docs: .agent/shopify-app-restyle/app-widget-{app-handle}.md,
.agent/THEME-CAPABILITIES.md, and .agent/COMPONENTS.md {— current contents
attached | absent}. For each shared doc, run its format-version ladder before
trusting it: absent → derive/scan the needed content; equal → verify its
scanned counts, file lists, and git line; lower → leave it for a producer to
regenerate and report it as stale; higher → read as-is and report
read-as-newer. Verify the app-widget doc in the live DOM: compare the live
container outerHTML against its snapshot — equal → reuse its selectors/rules
and skip re-deriving 1–3; different or absent → do 1–3 in full and rewrite
the doc. THEME-CAPABILITIES, when usable, answers 6–7 in the exact contract
sections `## §CSS load` and `## §Globals` — read those headings; absent or
stale → derive both sections per-run. COMPONENTS at the current format is
appended only at cleanup, then its format gate is rerun; a higher-format
COMPONENTS doc is read-as-newer and left byte-for-byte unchanged.

In the browser, find the widget the app renders (search the DOM for the app's
name, handle, or vendor prefix in classes, ids, and data-attributes), then:
1. The widget container's full outerHTML.
2. All matched CSS rules with their stylesheet origins (app-served vs theme),
   plus inline styles. FLAG any JS-injected inline !important styles — theme
   CSS cannot beat those; they belong on the not-CSS-fixable list.
3. Stable selectors for overrides: the app's container class/ID, its classes
   and data-attributes — never generated IDs or nth-child chains.
4. Baseline screenshots at both capture widths, saved under {temp-dir}
   (outside the theme repo).
Theme reads:
5. PER-RUN — in {template-path}: the app block's entry (its `type` carries the
   app handle) and the placement anchor in the host section's `block_order`
   for "{placement}" — OPEN QUESTION if either is ambiguous, or if the app
   block is absent.
6. How the theme loads custom CSS (asset naming, include point) — the
   conventions an override stylesheet must mirror.
7. The theme's global typography/color variables — names and where they are
   defined (from THEME-CAPABILITIES when attached, derived here otherwise);
   resolve their CURRENT values live and report them per-run; the main agent
   decides any mapping to Figma values.

Write the widget findings (1–3) to .agent/shopify-app-restyle/
app-widget-{app-handle}.md, opening with its header:
{knowledge-doc header, filled at dispatch — §Knowledge docs}; skip it when
the freshness check proved the doc current. Write the per-run findings
(4–5, plus 6–7 when derived here) to {temp-dir}/theme-widget-report.md with
OPEN QUESTIONS at the end — .agent/THEME-CAPABILITIES.md is read-only for
this skill. Return only a 3–5 line summary plus the open questions.
```

### style-reporter prompt

```
You are producing the style report for one breakpoint and one state of a
restyled third-party app widget built from a design spec. You NEVER edit theme
files — no Write, no Edit, no shell command that changes a theme file. Your
ONLY writes are the result screenshot and the report file named below.
Capture, assert, record, report.

Breakpoint: {desktop|mobile}, width {w}px
State: {default | the state name, plus the interaction that reproduces it}
Render at: {dev-server-url | preview-url}
Widget container: {selector}
Design spec (the expected values): {temp-dir}/figma-spec.md
Key elements to assert: {list from the plan, for THIS state}

1. Capture hygiene, then capture: viewport at the Figma frame width above;
   animations/transitions disabled; wait for document.fonts.ready + network
   idle; reproduce the state by interacting; clip to the widget container, not
   the full page.
2. Computed styles: getComputedStyle on each key element vs the design spec's
   values FOR THIS STATE (font-family/size/weight, line-height,
   letter-spacing, color, background, padding, margin, gap, border-radius).
   Record every mismatch: the state above, element, property, expected, actual.
3. Write the capture to .agent/shopify-app-restyle/visual-check/{widget-name}/
   result-{breakpoint}[-{state}].png, overwriting what is there. The state
   suffix is used only for states in the plan; generate no diff image and no
   `clean-`, `section-`, or other render variant.
4. Leak check: inspect the elements around the widget (siblings, host section,
   page chrome) and report anything the override stylesheet affects outside
   the widget container.

Write the FULL table to {temp-dir}/style-report-{breakpoint}[-{state}].md: one
row per mismatch — state | element | property | expected | actual — followed by
the leak findings. Every row carries the state, so the main agent's report
stays legible once the states are merged. Return that table as TEXT only, plus
the mismatch count and the leak findings. Return no images.
```

## Knowledge docs — scan once, reuse

`.agent/` at the theme repo root holds every durable artifact this skill suite produces: shared knowledge docs at its root, per-skill outputs under `.agent/<skill-name>/`. Knowledge docs are written for an AI reader — tables, exact identifiers (selectors, classes, data-attributes, variable names), rules and constraints, zero filler prose — and are written by the run that scans, immediately, so the knowledge survives even an aborted run.

This skill's docs:

- **`.agent/shopify-app-restyle/app-widget-<app-handle>.md`** — one per app, `<app-handle>` kebab-cased from the installed app name: the widget container's outerHTML snapshot, stable override selectors, matched CSS rules with origins (app-served vs theme), and the JS-injected inline-`!important` list. Freshness is a live check: compare the current container outerHTML against the stored snapshot — equal → trust the doc; different → full re-inspection, doc rewritten (app updates are the staleness source).
- **`.agent/THEME-CAPABILITIES.md`** — read-only here; its shape is fixed, so it reads the same no matter which skill produced it. This skill reads the exact contract headings `## §Globals` (variable names and wiring — current values resolve live) and `## §CSS load` (how the theme loads custom CSS); absent → the widget-inspector derives those two sections per-run into its report. This skill adds no sections, blocks, or settings, so it never updates this doc.
- **`.agent/COMPONENTS.md`** — appended-to here: at cleanup, where the doc exists at this skill's format, add one row for the override stylesheet — name · `assets/<app-handle>-overrides.css` + its include point · what it restyles · reuse keywords — plus, only when the override introduces a reusable/recurring motion treatment (named `@keyframes`, a hover/loading treatment applied across the widget), one Animations row (under `## Animations`) pointing at the same stylesheet + include point, its `what it does` opening with trigger + tech and its trigger words repeated in `reuse keywords`; plain color/spacing overrides add no Animations row. Refresh the header fields (date, git line, counts), append one dated line to `updates:` naming the affected categories, and rerun the format spec's completeness gate. Doc absent, lower-format, or higher-format → skip the append and report its status; a future full inventory scan discovers the stylesheet.

This skill's app-widget doc opens with this header (`scanned:` records the inspected URL + container selector; the shared docs carry the same fields with their own refresh phrases):

```
---
generated: <YYYY-MM-DD>
skill: <producing skill> (<agent role>)
theme: <theme name>
git: <branch> @ <short SHA>
scanned: <dirs + file counts | URL + container selector>
refresh: user says "refresh app widget" → regenerate
---
```

**Read before inspection (main agent, Phase 1):** read both docs when they exist and pass their contents to the widget-inspector, which records each shared doc's observed `format:` value, verifies freshness in the live DOM before trusting them, and re-derives only what is missing or stale. An explicit user refresh always wins: full re-inspection, docs rewritten.

**Root pointer:** the repo's root `AGENTS.md`/`CLAUDE.md` names this convention so future sessions find the docs before rescanning. Missing → append it (or create a minimal `CLAUDE.md` holding just this block, excluded like everything else) — an audit-trail edit like any other:

```
## 📚 Knowledge docs (check before any theme scan)
Skill outputs + knowledge docs live under `.agent/` — shared docs at its root,
per-skill outputs in `.agent/<skill-name>/`. Read `.agent/THEME-CAPABILITIES.md`
before any theme scan and search `.agent/COMPONENTS.md` before writing new
code; freshness checks + refresh instructions in their headers.
```

## The visual-check folder

`.agent/shopify-app-restyle/visual-check/<widget-name>/` in the theme repo, kebab-cased from the app/widget name (e.g. "Product Options Pro" → `.agent/shopify-app-restyle/visual-check/product-options-pro/`). Its root holds the design spec and two image classes:

- **The design spec**, at the folder root — `figma-spec.md`, copied in from the temp directory at render start and retained, so the values this restyle was given survive the run.
- **Figma references**, at the folder root — `figma-desktop.png` / `figma-mobile.png`; where the plan has state-specific Figma frames, use only `figma-{breakpoint}-{state}.png`.
- **Clean renders**, at the folder root — `result-desktop.png` / `result-mobile.png`, written by the style reporter, one per breakpoint and state: `result-{breakpoint}-{state}.png` for each state the plan names, so every state is separately reviewable by eye.
- No diff images, and no `clean-`, `section-`, or other render variants are generated. These whole-frame files are what the user compares by eye.
- **Per-asset exports**, in `assets/`, flat — the shipping file for each Figma node, each raster's `original-source-*` beside it, and `UPLOAD.md` (§Asset export).
- `HARDCODE-ACTIVE.md` — present only while a hardcode is live (§Hardcode-then-revert).

The folder is not theme code: `.agent/` stays out of git via a `.git/info/exclude` line (confirm the `.agent/` line exists; append it as a planned edit if not — a local, never-committed file, and the Shopify CLI ignores non-theme root directories, so it is never pushed). At cleanup, the root retains only the design spec and the allowed Figma-reference and result images; `assets/` remains for the user to review and upload, while `HARDCODE-ACTIVE.md` is deleted after every revert.

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

## Asset delivery — uploaded to the app

These exports are the remedy for the app-served images and icons on the not-CSS-fixable list: the user uploads them in the app admin, where the app then serves them itself.

| Asset | Export as |
|---|---|
| Icon, flat illustration, logo, line art | **SVG** |
| Photo, hero, product shot | **PNG** where any pixel is transparent, **JPEG** where fully opaque |

Upload what ships: whatever the app hands to Shopify's CDN gets re-encoded to WebP or AVIF per browser and per derivative on its own, so pre-converting only adds a generation of loss and no image encoder ever reaches the ledger.

The crop is framed to the Figma node, which the override's own geometry then reproduces — the two agree by construction. Where the container's aspect is on the not-CSS-fixable list, the app re-crops the crop: report the region with both aspects and hand over `original-source-<name>` instead, so the app crops once from the full picture. This is the one case where a *cropped* row falls back to its original source, so the plan and the final output name it.

Where existing theme or app code pipes an asset through `image_url` with `format: 'pjpg'`, it forfeits WebP and AVIF entirely — report it on the region under measurement.

**Inline branch:** where the user designates an asset as carrying motion or a hover/scheme colour change, this skill reaches it through its own stylesheet — the `.svg` is committed to the theme's `assets/` and the override applies `mask-image` with `background-color: currentColor`, which restores full colour control over a shape the app's markup owns. The app's own files stay untouched, as always. That asset is theme code and the app admin cannot swap it, so the plan and the final output name each one.

## Hardcode-then-revert

App-served images only change once the user uploads the export in the app admin, so until then the widget renders the app's old art and the result screenshot would show the wrong picture in a region that is already correct in the design — the one thing the user is going to judge the restyle by. The render puts the exported assets in directly, then puts the app's own back.

**Before hardcoding**, write `HARDCODE-ACTIVE.md` into the visual-check folder: every file path about to be touched, the original markup verbatim, and every temp asset copied into the theme's `assets/`. It is the snapshot the revert restores from.

**Hardcode once**, after the render is up and before the first capture, in the override stylesheet — the app's markup is never touched, so the swap is a scoped `background-image`. Injected regions sit between sentinels and temp assets carry the `vh-tmp-` prefix, which is what makes both greppable:

```css
/* VERIFY-HARDCODE-START <name> */
.app-container .widget__icon {
  background-image: url("{{ 'vh-tmp-icon.svg' | asset_url }}") !important;
}
/* VERIFY-HARDCODE-END <name> */
```

Correction-round fixes go outside the marked region.

**Revert** on every exit — completion and abort alike: restore from the breadcrumb, delete `assets/vh-tmp-*`, delete the breadcrumb. The region returns to the not-CSS-fixable list, where its remedy was an app-admin upload all along.

**Prove it** in the final output: `grep -r VERIFY-HARDCODE` over the theme returns nothing, and no `vh-tmp-*` remains. A revert that fails reports **REVERT FAILED** with the breadcrumb path.

A session that dies mid-render leaves the breadcrumb and the sentinels in place. Finding either at the start of a run means reverting from it first.

## Phase 1 — Research (read-only on the theme)

**Stranded-hardcode check first** (main agent, before anything else): a `HARDCODE-ACTIVE.md` in any `.agent/shopify-app-restyle/visual-check/*/`, or a `grep -r VERIFY-HARDCODE` hit in the theme, is a hardcode a previous session left live. Revert it per §Hardcode-then-revert and report it before the run continues — a stranded hardcode is the one theme edit this phase makes, and leaving it live in a client's theme is the risk the mechanism exists to close.

Run the two delegations in parallel, plus tooling detection. Beyond that revert, no theme file is created or modified; the one canonical write is the app-widget doc (§Knowledge docs).

- **Figma extraction** → figma-extractor: both frames via the Figma MCP; the producer/write-surface header; exact-values table (the override targets AND the style report's expected values); desktop/mobile differences; layout intent; stacking and overlap; group rhythm; every visible widget state with the interaction that reproduces it; asset inventory. Report: `figma-spec.md`, the design spec. This is the run's only extraction — the overrides read from it and never return to Figma for a value.
- **Widget inspection + theme reads** → widget-inspector (in main if browser tools don't reach subagents), knowledge docs read first and passed in (§Knowledge docs): locate the widget by app name; verify doc freshness against the live container outerHTML; container outerHTML; matched rules with origins; JS-injected inline `!important` styles flagged; stable selectors; baseline screenshots at the Figma frame widths (read the widths via a cheap Figma `get_metadata` call at dispatch); per-run, the app-block entry + placement anchor in the target template; the theme's custom-CSS conventions and global typography/color variables (from `.agent/THEME-CAPABILITIES.md` when present, derived per-run otherwise). Writes/updates the app-widget doc; per-run report: `theme-widget-report.md`.
- **Tooling detection** (main agent, non-mutating checks only): Browser pane availability first, then fallbacks per Browser tiers; the Agent tool and which tools reach subagents (fix the delegation map). Render path: Shopify CLI + `shopify.theme.toml` → `shopify theme dev` (desktop app: defined in `.claude/launch.json` so the pane manages the server); otherwise a preview/live store URL. A real store render is required — app-block markup only exists there, so a local Liquid engine cannot produce it and there is NO static fallback. Check `.git/info/exclude` for a `.agent/` line.
- **Wrong-state check**: the dev preview must agree with the live site on everything that changes how the widget renders — availability (in stock vs sold out), widget presence, options shown. On any disagreement, pause and work [environment-mismatch.md](environment-mismatch.md) to the first step that fixes it; a wrong-state widget is never inspected or restyled against.
- **Difference list** (main agent, from `figma-spec.md`, the knowledge docs, and `theme-widget-report.md`), element by element and per state, split into (a) CSS-fixable and (b) not fixable by CSS — markup/structure differences, text and labels configured in the app admin, app-served images/icons, JS-set inline `!important` styles. Where a not-CSS-fixable item is an app-served image/icon, note that its Figma export will be in the visual-check `assets/` folder for app-admin upload, and that the render shows it through a hardcode meanwhile (§Hardcode-then-revert).

**Done when:** the design spec `figma-spec.md` exists, carrying its producer/write-surface header and all seven sections; the widget report exists and the app-widget doc is current (fresh header); every OPEN QUESTION has been put to the user and answered; the tooling record names browser tier, capture source, render path, delegation map, temp dir, and the exclude status; any dev/live disagreement is resolved (note the step); and the difference list places every Figma-vs-live difference in exactly one of the two lists.

## Phase 2 — Plan (write it out, then continue)

The plan is an audit trail in the transcript, not a checkpoint — write it in full, then proceed straight to Phase 3. The run has no approval stop; writing the plan out is what makes the design spec's numbers reviewable in the transcript. It states:

- **The design spec, quoted inline**: the exact-values table reproduced in the plan itself, per breakpoint and per state, plus the layout intent, the stacking and overlap, and the group rhythm — quoted, never referenced by file path. Nothing after this re-reads Figma, so the numbers themselves sit in the transcript. Every OPEN QUESTION is resolved above it.
- **Stylesheet**: filename (e.g. `assets/<app-handle>-overrides.css`) and load point per the theme's CSS conventions. App CSS can load async — `!important` carries the win, not load order.
- **Override table**: element → scoped selector → property: current value → target value (exact Figma value, or a theme variable where it genuinely matches) → media query if breakpoint-specific.
- **Not-CSS-fixable list**: each item with its remedy — app-admin setting, accept as-is, or upload the exported asset. Reported, not gated: everything CSS can fix gets fixed; the list rides through to the final output. Never attempt DOM hacks.
- **Placement**: the `block_order` diff moving the app block to the input-5 position, or confirmation it already sits there.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append adding it.
- **Asset-export list** (§Asset export, §Asset delivery): every inventoried asset → node-id, kind, source field, format, computed scale, and filename in `.agent/shopify-app-restyle/visual-check/<widget-name>/assets/`, plus the not-CSS-fixable row it remedies and, for a raster fill, its `original-source-*` twin; `assets/UPLOAD.md` is written from this list.
- **Hardcode plan** (§Hardcode-then-revert): every app-served image region to be hardcoded for the render, its temp `vh-tmp-` asset, and the selector the swap targets.
- **Inline-branch list** (§Asset delivery): every asset the user designated as carrying motion or a hover/scheme colour change → the `.svg` committed to the theme's `assets/`, its `mask-image` rule, and its selector — each named as not swappable from the app admin.
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced so far.
- **Render-and-report approach**: browser tier, render path, whether `.claude/launch.json` will be created/updated (a planned file if so), the capture width per breakpoint, the widget container selector, **the state list** — every state from the design spec with the interaction that reproduces it and its `-<state>` render filename — the key elements the style report asserts per breakpoint and state, and the exact temporary-install list with method (on-demand runner / project-local / venv) — listed installs proceed without approval; the cleanup ledger still guarantees their removal.

## Phase 3 — Implement (main agent only)

Touch only planned files; no delegated edits; app-served files and assets stay untouched.

- Create the override stylesheet per the plan, from the design spec alone — its exact values, its layout intent, its stacking and overlap, its group rhythm, its per-state values: every declaration carries `!important`; every selector is scoped under the app's container so nothing leaks into the rest of the page; mapped theme variables where planned, exact Figma values otherwise; media queries per the planned breakpoint strategy. Figma is not re-read; a value the spec does not carry goes back to the user.
- Add the stylesheet include at the planned load point. Apply the planned `block_order` edit; append the `.agent/` line to `.git/info/exclude` if planned. Read every file before editing; show the diff inline for every edited file — audit trail, not checkpoint.
- Export the Figma assets per the plan (§Asset export) into `.agent/shopify-app-restyle/visual-check/<widget-name>/assets/`; run the bounds, identity and count checks. Inline-branch assets are also committed to the theme's `assets/`, with their `mask-image` rules in the override stylesheet.

**Done when:** every planned file exists as planned, every edit's diff is in the transcript, nothing outside the plan changed, and all three export checks pass — bounds, identity, and both counts — with `assets/UPLOAD.md` written.

## Phase 4 — Render and report

**Static, first:** an edited template still parses as valid JSON; `shopify theme check` on changed files if available; fix errors.

Then **seven steps, in this order** — render → data check → capture hygiene → `style-reporter` → correction round → style report → cleanup. The three Figma-driven skills share this shape; the one thing this skill varies is the AXIS those steps run over — capture hygiene, the `style-reporter` call, and the style report all run per state as well as per breakpoint, because an app widget's appearance changes on interaction and a state-dependent override is exactly what breaks. Nothing else varies. There is no loop, no iteration cap and no pass/fail verdict: the run passes through the seven once and ends by handing the user the evidence.

At the start, write the Figma references the plan names into the visual-check folder — `figma-desktop.png` / `figma-mobile.png`, or the per-state `figma-{breakpoint}-{state}.png` set where the plan has state-specific frames — and copy the design spec in beside them as `figma-spec.md`.

**1. Render.** `shopify theme dev` when available (Browser pane manages it via `.claude/launch.json` in the desktop app); otherwise the preview/live store URL. There is no static fallback — app-block markup only exists on a real store, so a local Liquid engine cannot produce it.

**2. Data check** (main agent) — the shape's data check in its plain form. Each skill's render pulls its own kind of data, so each fills this step with the check that data needs; filling the slot is not varying the shape — the per-state axis is the one thing this skill varies. The widget renders the app's OWN data and the store's real product state, so the dev preview must still agree with the live site on everything Phase 1's wrong-state check listed. On any disagreement, work [environment-mismatch.md](environment-mismatch.md) to the first step that fixes it and resume once it agrees — nothing is captured against a wrong-state widget.

**3. Capture hygiene** (before every capture, per breakpoint AND per state): the Figma frame width per breakpoint; clip to the widget container, not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle; reproduce the state by interacting in the browser before capturing it. No scale-matching and no pixel-dimension requirement — nothing compares the capture to the reference mechanically. Capture source: the Browser pane, else connected browser MCP or installed Chrome, else `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the cleanup ledger). **Hardcode last** (main agent, before the first capture): breadcrumb, then inject per §Hardcode-then-revert, so the result screenshots show the design rather than the app's pending art.

**4. `style-reporter`, once per breakpoint and state.** One call per (breakpoint, state) pair from the plan's state list — desktop and mobile × default plus every named state: it captures, asserts the key elements' computed styles against the design spec's values for that state, writes `result-{breakpoint}[-{state}].png` into the visual-check folder, runs the leak check, and returns a text mismatch table. It never edits theme files and returns no images. Without delegation the same work runs in the main conversation, once per pair.

**5. Correction round** (main agent, once). Read the returned tables and fix what they name IN THE OVERRIDE STYLESHEET — never by editing app-served files and never with a DOM hack. A mismatch CSS cannot move (a JS-set inline `!important`, markup, an app-admin string) belongs on the not-CSS-fixable list, surfaced there rather than worked around. Fixes go outside any hardcode sentinel region. Then re-render and re-run `style-reporter` once per affected breakpoint and state. One pass, one re-check, then stop; whatever remains goes into the report as-is.

**Revert** closes this step, the last capture now taken: restore from the breadcrumb and prove it per §Hardcode-then-revert.

**6. Style report — per breakpoint AND per state.** Emit the surviving mismatches: one row per mismatch — state, element, property, expected value, actual value — and "no mismatches" where there are none. The state column is what makes a hover-only or open-only regression legible; a row without it is unactionable. Leak findings ride with it. It is output, not judgment: it never blocks completion and carries no threshold, ratio, iteration count, plateau state or verdict. It sits beside `result-{breakpoint}[-{state}].png` and the Figma references, which the user compares by eye, one render per state. Note the report scope: computed styles were checked at the two captured widths, on the key elements the plan named, in the states the plan listed.

If no render or capture path exists even with temporary installs: revert any live hardcode, then stop and report exactly what's missing.

**7. Cleanup.** The ledger lists every temporary install (name, method, location). When `.agent/COMPONENTS.md` is at this skill's format, append the override-stylesheet row (plus the Animations row when the override introduces reusable motion), refresh its header and `updates:`, and rerun its format gate; absent, lower-format, and higher-format docs are reported and left unchanged. Then uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall; `.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/` in full — the knowledge docs for the next run, plus `.agent/shopify-app-restyle/visual-check/<widget-name>/` (the design spec, the references, the result renders per breakpoint and state, exported assets) — untracked via `.git/info/exclude`. The user reviews it, uploads the files `assets/UPLOAD.md` lists via the theme editor / app admin, and manages the folder themselves. Nothing from the task gets committed.

**Final output (no explanatory prose):** files created/changed; the revert proof (`grep -r VERIFY-HARDCODE` clean, no `vh-tmp-*` remaining) or **REVERT FAILED** with the breadcrumb path; the style report per breakpoint and state — state, element, property, expected, actual per surviving mismatch, or "no mismatches" — with the leak findings; the not-CSS-fixable list (if any), each hardcoded region named among them; any source-quality flags; any region where the original source ships instead of the crop, with both aspects; any inline-branch assets, named as not swappable from the app admin; the delegation map; the tooling ledger with removal confirmation (or "nothing installed"); knowledge-doc status — `app-widget-<app-handle>.md` reused (fresh) / updated / created; `.agent/THEME-CAPABILITIES.md` observed `format: <n>` and read as fresh/stale/higher-version-as-is, or absent (`format: unknown`; exact sections `## §Globals` + `## §CSS load` derived per-run); `.agent/COMPONENTS.md` observed `format: <n>` and row appended for the override stylesheet (+ Animations row when the override added reusable motion), or absent/lower/higher (`format: <n>`; skipped); the path `.agent/shopify-app-restyle/visual-check/<widget-name>/` with a one-line inventory (the design spec, the references, the result renders per breakpoint and state, shipping files and `original-source-*` counts per format, `UPLOAD.md`) and exclusion confirmation; which environment-mismatch step resolved any dev/live disagreement — and after step 8, confirmation the original theme is live again.

## Rules

- Read every file before editing; include the diff inline when editing an existing file.
- Gate-free once inputs are complete: the only stops are a missing input, genuine ambiguity, or the live publish swap — which never runs without the user's explicit go-ahead.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- The Browser pane leads when available; fallbacks apply only when it's absent.
- The design spec is the authority: the overrides read from it alone, no value is re-read from Figma after Phase 1, and a value it does not carry goes back to the user.
- The style report reports; it never blocks completion. One check against the design spec, one correction round, then it is emitted with whatever remains — no threshold, no ratio, no iteration count, no verdict.
- Per state as well as per breakpoint: capture hygiene, the `style-reporter` call, and the style report all run over both axes, and the report carries a state column. This is the skill's only permitted variation from the shared seven-step shape.
- Only `figma-{breakpoint}[-{state}].png` and `result-{breakpoint}[-{state}].png` names are generated at the visual-check root, alongside the design spec — one result render per state the plan lists, no diff images, and no `clean-`, `section-`, or other render variant.
- `assets/` holds the shipping file for each Figma node — its crop where one exists, its original source where none does — each raster's `original-source-*` beside it; reference captures at the folder root hold the frame. The bounds, identity and alpha checks keep a clipped, whole-frame or page-backed render out.
- Upload what ships and let the CDN pick the format — no image encoder reaches the ledger.
- A hardcode is breadcrumbed before it exists and reverted on every exit — completion and abort alike — with the grep proof in the final output.
- `.agent/` lives at the repo root, is always excluded via `.git/info/exclude`, and is never committed.
- Knowledge docs first: read `.agent/shopify-app-restyle/app-widget-<app-handle>.md`, `.agent/THEME-CAPABILITIES.md`, and `.agent/COMPONENTS.md`, record each shared doc's `format:` value, and run the relevant format-version ladder before any widget inspection or theme scan; an inspection that runs writes the app-widget doc back before the task continues. Use the exact `## §Globals` and `## §CSS load` headings; an absent or stale THEME-CAPABILITIES doc triggers the declared per-run derivation. Cleanup appends COMPONENTS rows only when that doc exists at this skill's format; absent, lower-format, and higher-format docs are reported and left unchanged. Refresh `updates:` and rerun the format gate after an append. An explicit user refresh always wins.
- Knowledge docs stay current: a completed restyle appends its override stylesheet as a `.agent/COMPONENTS.md` row (plus an Animations row when the override introduces reusable motion), refreshes its header and `updates:` list, and reruns the format spec's completeness gate (when the doc exists) before the final report.
- Every override declaration carries `!important` and sits scoped under the app's container; selectors target the app's stable classes/data-attributes — never generated IDs or `nth-child` chains.
- Overrides only: app-served files and assets are never modified, and DOM hacks are never attempted — not-CSS-fixable items get reported with a remedy instead.
- Verify Liquid/schema syntax via the Shopify dev MCP instead of guessing.
- CLI tools: check installed first (on PATH, project dep, or npm script) — installed → invoke directly (`shopify theme dev`, `npm run …`), no runner. Not installed → on-demand runner (`npx` / `pnpm dlx` / `bunx` / `pipx run`), never a global install. Runner impossible (persistent binary/venv needed) → project-local or venv, on the ledger.
- Leave the machine as it was found — the retained `.agent/` tree (knowledge docs + visual-check) is the one deliberate leftover, kept for the next run, review, and asset uploads.

## Usage

```
Use the shopify-app-restyle skill.
- Desktop: <figma link with node-id>
- Mobile: <figma link with node-id>
- App: "Easify Options"
- Template: templates/product.json
- Place: app block after the "Ship" accordion block
- Inspect: <product page URL>   (optional)
```
