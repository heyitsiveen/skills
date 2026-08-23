---
name: shopify-app-restyle
description: Restyle a third-party Shopify app's block or widget to match a Figma design with scoped !important CSS overrides — the app's own code and assets are never touched. Use when the user wants an installed app's widget or app block (product options, reviews, bundles, gift wrap, …) restyled, overridden, or customized to Figma frames, or asks for pixel-accurate styling of app-injected UI. Fidelity is measured — computed styles plus pixel diff against the Figma frames — never eyeballed.
---

# Shopify App Restyle

Restyle a third-party app's storefront widget to match two Figma frames without touching the app: scoped `!important` overrides in the theme, proven pixel-accurate by measurement. Four phases — research (read-only on the theme), plan (an audit trail, not a checkpoint), implement, verify (numeric gate) — then cleanup that leaves the machine as found. The run is **gate-free**: once the inputs are complete nothing pauses for approval; the only stops are a missing input, genuine ambiguity, or the live publish swap ([environment-mismatch](environment-mismatch.md) step 8, which never runs without the user's explicit go-ahead). The deliberate leftovers are the visual-check folder and the knowledge docs (§Knowledge docs).

## Inputs

Collect before starting; ask for any that are missing.

1. **Figma desktop link** — with node-id.
2. **Figma mobile link** — with node-id.
3. **App name, exactly as installed** — e.g. "Easify Options"; finds the app-block entry in the template and the widget's container/classes/stylesheets fast.
4. **Target template** — e.g. `templates/product.json`.
5. **Placement** — which section hosts the app block and where it sits in that section's `block_order` (before/after which block, by customizer label or type). Locates the widget and verifies/fixes its position.
6. **Page or product URL to inspect** — optional; ask only if the widget's rendering is product-specific and the target is ambiguous.

## Pixel-accurate is a measured result

The restyle passes when, per breakpoint and per verified state:

1. Every checked computed style matches its Figma value.
2. The image diff ratio against the Figma screenshot is ≤ 1% with anti-aliasing ignored.
3. Residual diff pixels are confirmed FROM THE DIFF IMAGE to be text-rasterization noise — Figma and Chromium rasterize fonts differently, so a literal 0% is unreachable. Layout, color, or spacing differences are never "noise".

Side-by-side eyeballing is for diagnosis only; passing is numeric.

## Browser tiers

**Primary: the Claude Code Desktop Browser pane** (desktop app with Browser enabled). Claude drives it directly — screenshots, DOM/computed-style inspection, clicking, form filling — and manages the dev server via `.claude/launch.json` (local dev servers need no site approval). Preview/live store URLs are external sites: expect a one-time permission card (Allow once / Always allow). Enable "Persist sessions" when the storefront is password-protected so the cookie survives restarts.

**Capture-exactness check:** the measured diff needs captures at the exact Figma frame widths and scale, with identical pixel dimensions, clipped to the widget container. Confirm the pane's screenshots can honor that; if not, the pane still does inspection, interaction, and diagnosis while the MEASURED captures fall to the first fallback that can.

**Fallbacks, in order:** connected browser MCP (Chrome DevTools MCP / Playwright MCP) → installed Chrome → temporary Playwright via npx.

## Delegation

Bounded research and measurement go to subagents — isolated workers with their own context windows that return only a final report — so bulk Figma payloads, DOM dumps, and per-iteration screenshots stay out of the main conversation, and independent research runs in parallel. Delegation multiplies tokens: skip it for trivially small reads.

Prefer the named custom agents `figma-extractor`, `widget-inspector`, and `visual-verifier` when installed in `~/.claude/agents/` or `.claude/agents/` — their definitions add tool-enforced restrictions (e.g. `disallowedTools: Write, Edit` on the verifier). Otherwise run the built-in general-purpose subagent with the embedded prompt below; in that fallback the no-theme-edits rule is instruction-enforced, so the prompt states it explicitly.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the Figma MCP / browser tools reach subagents (subagents inherit internal + MCP tools by default; the Browser pane's preview tools may be main-session-only). Any role whose tools don't reach a subagent runs in the main conversation instead.

**Handoff protocol:** subagents can't see the conversation and can't ask the user questions — every delegation prompt carries its exact inputs (node-ids, selectors, file paths, capture specs); every worker writes FULL findings to a report file in the temp working directory (the widget-inspector writes the app-widget doc plus a per-run report — §Knowledge docs) and returns a short summary; ambiguities come back as OPEN QUESTIONS for the main agent to put to the user. The temp working directory is created per run (use the session scratchpad when available) and is deleted at cleanup.

**Never delegated:** planning, user approvals, all implementation edits, the environment-mismatch steps that need the user (6 and 8), and the diagnosis/fix half of the verification loop.

| Role | Phase | Report |
|---|---|---|
| figma-extractor | 1, parallel | `figma-spec.md` |
| widget-inspector (read-only on the theme; skips re-derivation when the knowledge docs are fresh) | 1, parallel | `app-widget-<app-handle>.md` (§Knowledge docs) + per-run `theme-widget-report.md` |
| visual-verifier (never edits theme files) | 4, one call per iteration | `verify-report-<n>.md` |

### figma-extractor prompt

```
You are extracting a Figma design spec for restyling a third-party Shopify app
widget. Work only from the Figma MCP; do not read or modify the theme repo.

Frames:
- Desktop: {figma-desktop-link} (node-id {desktop-node-id})
- Mobile: {figma-mobile-link} (node-id {mobile-node-id})

For each node-id call get_design_context and get_screenshot, then compile:
1. Exact-values table per breakpoint: typography (family, size, weight,
   line-height, letter-spacing), colors, spacing (padding/margin/gap), sizes,
   border-radii, frame width. These are the CSS override targets AND the
   expected values for computed-style assertions — record exactly.
2. Desktop vs mobile differences (stacking, order, visibility, alignment).
3. Every widget state visible in the frames — selected option, open dropdown,
   hover, error, … — and which values change in each.
4. Each screenshot's scale (1x/2x) and pixel dimensions — captures must match
   them exactly for the pixel diff.
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
appended only after the verification gate, then its format gate is rerun; a
higher-format COMPONENTS doc is read-as-newer and left byte-for-byte unchanged.

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

### visual-verifier prompt

```
You are measuring one verification iteration of a restyled third-party app
widget against its Figma reference. You NEVER edit theme files — measure,
record, report only.

Iteration: {n} — breakpoint {desktop|mobile}, width {w}px, scale {s}, expected
capture dimensions {W}x{H}px
State(s) to verify: {default, plus each state and the interactions that
reproduce it}
Render at: {dev-server-url | preview-url}
Widget container: {selector}
Figma reference: .agent/shopify-app-restyle/visual-check/{widget-name}/
figma-{breakpoint}.png
(per-state references where extracted: figma-{breakpoint}-{state}.png)
Expected values: {temp-dir}/figma-spec.md
Key elements to assert: {list from the plan}
Diff tool: {pixelmatch … | odiff-bin …} (installed direct, else via npx; anti-aliasing ignored)

Per state:
1. Capture hygiene, then capture: viewport at the exact width and scale above;
   animations/transitions disabled; wait for document.fonts.ready + network
   idle; reproduce the state by interacting; clip to the widget container. The
   capture's pixel dimensions must equal the reference's exactly.
2. Computed styles: getComputedStyle on each key element vs the expected
   values (font-family/size/weight, line-height, letter-spacing, color,
   background, padding, margin, gap, border-radius). Record every mismatch:
   element, property, expected, actual.
3. Pixel diff vs the reference; record the diff ratio; save the diff image.
4. Overwrite .agent/shopify-app-restyle/visual-check/{widget-name}/
   result-{breakpoint}[-{state}].png and diff-{breakpoint}[-{state}].png with
   THIS iteration's capture and diff. State suffixes are allowed only for
   states in the approved plan; do not generate `clean-`, `section-`, or other
   render variants.
5. Leak check: inspect the elements around the widget (siblings, host section,
   page chrome) and report anything the override stylesheet affects outside
   the widget container.

Write the FULL report to {temp-dir}/verify-report-{n}.md: mismatch table, diff
ratio per state, largest diff regions and where they sit, leak findings.
Return only the diff ratio(s), mismatch count, and one line on the biggest
offender.
```

## Knowledge docs — scan once, reuse

`.agent/` at the theme repo root holds every durable artifact this skill suite produces: shared knowledge docs at its root, per-skill outputs under `.agent/<skill-name>/`. Knowledge docs are written for an AI reader — tables, exact identifiers (selectors, classes, data-attributes, variable names), rules and constraints, zero filler prose — and are written by the run that scans, immediately, so the knowledge survives even an aborted run.

This skill's docs:

- **`.agent/shopify-app-restyle/app-widget-<app-handle>.md`** — one per app, `<app-handle>` kebab-cased from the installed app name: the widget container's outerHTML snapshot, stable override selectors, matched CSS rules with origins (app-served vs theme), and the JS-injected inline-`!important` list. Freshness is a live check: compare the current container outerHTML against the stored snapshot — equal → trust the doc; different → full re-inspection, doc rewritten (app updates are the staleness source).
- **`.agent/THEME-CAPABILITIES.md`** — read-only here; its shape is fixed, so it reads the same no matter which skill produced it. This skill reads the exact contract headings `## §Globals` (variable names and wiring — current values resolve live) and `## §CSS load` (how the theme loads custom CSS); absent → the widget-inspector derives those two sections per-run into its report. This skill adds no sections, blocks, or settings, so it never updates this doc.
- **`.agent/COMPONENTS.md`** — appended-to here: after verification passes and the doc exists at this skill's format, add one row for the override stylesheet — name · `assets/<app-handle>-overrides.css` + its include point · what it restyles · reuse keywords — plus, only when the override introduces a reusable/recurring motion treatment (named `@keyframes`, a hover/loading treatment applied across the widget), one Animations row (under `## Animations`) pointing at the same stylesheet + include point, its `what it does` opening with trigger + tech and its trigger words repeated in `reuse keywords`; plain color/spacing overrides add no Animations row. Refresh the header fields (date, git line, counts), append one dated line to `updates:` naming the affected categories, and rerun the format spec's completeness gate. Doc absent, lower-format, or higher-format → skip the append and report its status; a future full inventory scan discovers the stylesheet.

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

`.agent/shopify-app-restyle/visual-check/<widget-name>/` in the theme repo, kebab-cased from the app/widget name (e.g. "Product Options Pro" → `.agent/shopify-app-restyle/visual-check/product-options-pro/`). The root has exactly three image classes:

- **Figma references**, at the folder root — `figma-desktop.png` / `figma-mobile.png`; when the approved plan has state-specific Figma frames, use only `figma-{breakpoint}-{state}.png`.
- **Clean renders**, at the folder root — `result-desktop.png` / `result-mobile.png`; for approved state-specific checks, use only `result-{breakpoint}-{state}.png`.
- **Image diffs**, at the folder root — `diff-desktop.png` / `diff-mobile.png`; for approved state-specific checks, use only `diff-{breakpoint}-{state}.png`.
- No `clean-`, `section-`, or other render variants are generated. These whole-frame files are the only measured comparison set; the pixel diff measures the frame.
- **Per-asset exports**, in `assets/`, flat — the shipping crop for each Figma node, each raster's `original-source-*` beside it, and `UPLOAD.md` (§Asset export).
- `HARDCODE-ACTIVE.md` — present only while a verification hardcode is live (§Hardcode-then-revert).

The folder is not theme code: `.agent/` stays out of git via a `.git/info/exclude` line (confirm the `.agent/` line exists; append it as a planned edit if not — a local, never-committed file, and the Shopify CLI ignores non-theme root directories, so it is never pushed). At cleanup, the root retains only the allowed Figma/reference, result, and diff images; `assets/` remains for the user to review and upload, while `HARDCODE-ACTIVE.md` is deleted after every revert.

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

## Asset delivery — uploaded to the app

These exports are the remedy for the app-served images and icons on the not-CSS-fixable list: the user uploads them in the app admin, where the app then serves them itself.

| Asset | Export as |
|---|---|
| Icon, flat illustration, logo, line art | **SVG** |
| Photo, hero, product shot | **PNG** crop |

Upload the crops: whatever the app hands to Shopify's CDN gets re-encoded to WebP or AVIF per browser and per derivative on its own, so pre-converting only adds a generation of loss and no image encoder ever reaches the ledger.

The crop is framed to the Figma node, which the override's own geometry then reproduces — the two agree by construction. Where the container's aspect is on the not-CSS-fixable list, the app re-crops the crop: report the region with both aspects and hand over `original-source-<name>` instead, so the app crops once from the full picture. This is the one case where the original source ships, so the plan and the final output name it.

Where existing theme or app code pipes an asset through `image_url` with `format: 'pjpg'`, it forfeits WebP and AVIF entirely — report it on the region under measurement.

**Inline branch:** where the user designates an asset as carrying motion or a hover/scheme colour change, this skill reaches it through its own stylesheet — the `.svg` is committed to the theme's `assets/` and the override applies `mask-image` with `background-color: currentColor`, which restores full colour control over a shape the app's markup owns. The app's own files stay untouched, as always. That asset is theme code and the app admin cannot swap it, so the plan and the final output name each one.

## Hardcode-then-revert

App-served images only change once the user uploads the export in the app admin, so until then the widget renders the app's old art and the diff measures a region that is already correct in the design. Verification renders the exported assets directly, then puts the app's own back.

**Before hardcoding**, write `HARDCODE-ACTIVE.md` into the visual-check folder: every file path about to be touched, the original markup verbatim, and every temp asset copied into the theme's `assets/`. It is the snapshot the revert restores from.

**Hardcode once**, before the loop rather than per iteration, in the override stylesheet — the app's markup is never touched, so the swap is a scoped `background-image`. Injected regions sit between sentinels and temp assets carry the `vh-tmp-` prefix, which is what makes both greppable:

```css
/* VERIFY-HARDCODE-START <name> */
.app-container .widget__icon {
  background-image: url("{{ 'vh-tmp-icon.svg' | asset_url }}") !important;
}
/* VERIFY-HARDCODE-END <name> */
```

Iteration fixes go outside the marked region.

**Revert** on every exit — pass, cap, and abort: restore from the breadcrumb, delete `assets/vh-tmp-*`, delete the breadcrumb. The region returns to the not-CSS-fixable list, where its remedy was an app-admin upload all along.

**Prove it** in the final output: `grep -r VERIFY-HARDCODE` over the theme returns nothing, and no `vh-tmp-*` remains. A revert that fails reports **REVERT FAILED** with the breadcrumb path.

A session that dies mid-verification leaves the breadcrumb and the sentinels in place. Finding either at the start of a run means reverting from it first.

## Phase 1 — Research (read-only on the theme)

**Stranded-hardcode check first** (main agent, before anything else): a `HARDCODE-ACTIVE.md` in any `.agent/shopify-app-restyle/visual-check/*/`, or a `grep -r VERIFY-HARDCODE` hit in the theme, is a hardcode a previous session left live. Revert it per §Hardcode-then-revert and report it before the run continues — a stranded hardcode is the one theme edit this phase makes, and leaving it would corrupt every measurement that follows.

Run the two delegations in parallel, plus tooling detection. Beyond that revert, no theme file is created or modified; the one canonical write is the app-widget doc (§Knowledge docs).

- **Figma extraction** → figma-extractor: both frames via the Figma MCP; exact-values table (the override targets AND the expected values for verification's computed-style assertions); desktop/mobile differences; every visible widget state; screenshot scale + pixel dimensions; asset inventory. Report: `figma-spec.md`.
- **Widget inspection + theme reads** → widget-inspector (in main if browser tools don't reach subagents), knowledge docs read first and passed in (§Knowledge docs): locate the widget by app name; verify doc freshness against the live container outerHTML; container outerHTML; matched rules with origins; JS-injected inline `!important` styles flagged; stable selectors; baseline screenshots at the Figma frame widths (read the widths via a cheap Figma `get_metadata` call at dispatch); per-run, the app-block entry + placement anchor in the target template; the theme's custom-CSS conventions and global typography/color variables (from `.agent/THEME-CAPABILITIES.md` when present, derived per-run otherwise). Writes/updates the app-widget doc; per-run report: `theme-widget-report.md`.
- **Tooling detection** (main agent, non-mutating checks only): Browser pane availability first, then fallbacks per Browser tiers; run the capture-exactness check; the Agent tool and which tools reach subagents (fix the delegation map). Render path: Shopify CLI + `shopify.theme.toml` → `shopify theme dev` (desktop app: defined in `.claude/launch.json` so the pane manages the server); otherwise a preview/live store URL. A real store render is required — app-block markup only exists there, so a local Liquid engine cannot produce it and there is NO static fallback. Diff tool: installed `pixelmatch`/`odiff` (PATH or project `node_modules/.bin`) invoked directly, else `npx pixelmatch` / `npx odiff-bin`. Check `.git/info/exclude` for a `.agent/` line.
- **Wrong-state check**: the dev preview must agree with the live site on everything that changes how the widget renders — availability (in stock vs sold out), widget presence, options shown. On any disagreement, pause measurement and work [environment-mismatch.md](environment-mismatch.md) to the first step that fixes it; a wrong-state widget is never inspected or verified against.
- **Difference list** (main agent, from `figma-spec.md`, the knowledge docs, and `theme-widget-report.md`), element by element and per state, split into (a) CSS-fixable and (b) not fixable by CSS — markup/structure differences, text and labels configured in the app admin, app-served images/icons, JS-set inline `!important` styles. Where a not-CSS-fixable item is an app-served image/icon, note that its Figma export will be in the visual-check `assets/` folder for app-admin upload, and that verification measures it through a hardcode meanwhile (§Hardcode-then-revert).

**Done when:** both reports exist and the app-widget doc is current (fresh header); every OPEN QUESTION has been put to the user and answered; the tooling record names browser tier, capture source (exactness result), render path, diff tool, delegation map, temp dir, and the exclude status; any dev/live disagreement is resolved (note the step); and the difference list places every Figma-vs-live difference in exactly one of the two lists.

## Phase 2 — Plan (write it out, then continue)

The plan is an audit trail in the transcript, not a checkpoint — write it in full, then proceed straight to Phase 3. It states:

- **Stylesheet**: filename (e.g. `assets/<app-handle>-overrides.css`) and load point per the theme's CSS conventions. App CSS can load async — `!important` carries the win, not load order.
- **Override table**: element → scoped selector → property: current value → target value (exact Figma value, or a theme variable where it genuinely matches) → media query if breakpoint-specific.
- **Not-CSS-fixable list**: each item with its remedy — app-admin setting, accept as-is, or upload the exported asset. Reported, not gated: everything CSS can fix gets fixed; the list rides through to the final output. Never attempt DOM hacks.
- **Placement**: the `block_order` diff moving the app block to the input-5 position, or confirmation it already sits there.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append adding it.
- **Asset-export list** (§Asset export, §Asset delivery): every inventoried asset → node-id, kind, source field, format, computed scale, and filename in `.agent/shopify-app-restyle/visual-check/<widget-name>/assets/`, plus the not-CSS-fixable row it remedies and, for a raster fill, its `original-source-*` twin; `assets/UPLOAD.md` is written from this list.
- **Hardcode plan** (§Hardcode-then-revert): every app-served image region to be hardcoded for measurement, its temp `vh-tmp-` asset, and the selector the swap targets.
- **Inline-branch list** (§Asset delivery): every asset the user designated as carrying motion or a hover/scheme colour change → the `.svg` committed to the theme's `assets/`, its `mask-image` rule, and its selector — each named as not swappable from the app admin.
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced so far.
- **Verification approach**: browser tier with the capture-exactness result (pane captures, or which fallback), render path, whether `.claude/launch.json` will be created/updated (a planned file if so), capture widths and scale, the widget states to verify, key elements for computed-style assertions, diff tool + pass threshold (default: ≤ 1%, anti-aliasing ignored), iteration cap (default: 8 per breakpoint, plateau exit after 2 iterations without improvement), and the exact temporary-install list with method (on-demand runner / project-local / venv) — listed installs proceed without approval; the cleanup ledger still guarantees their removal.

## Phase 3 — Implement (main agent only)

Touch only planned files; no delegated edits; app-served files and assets stay untouched.

- Create the override stylesheet per the plan: every declaration carries `!important`; every selector is scoped under the app's container so nothing leaks into the rest of the page; mapped theme variables where planned, exact Figma values otherwise; media queries per the planned breakpoint strategy.
- Add the stylesheet include at the planned load point. Apply the planned `block_order` edit; append the `.agent/` line to `.git/info/exclude` if planned. Read every file before editing; show the diff inline for every edited file — audit trail, not checkpoint.
- Export the Figma assets per the plan (§Asset export) into `.agent/shopify-app-restyle/visual-check/<widget-name>/assets/`; run the bounds, identity and count checks. Inline-branch assets are also committed to the theme's `assets/`, with their `mask-image` rules in the override stylesheet.

**Done when:** every planned file exists as planned, every edit's diff is in the transcript, nothing outside the plan changed, and all three export checks pass — bounds, identity, and both counts — with `assets/UPLOAD.md` written.

## Phase 4 — Verify

**Static:** an edited template still parses as valid JSON; `shopify theme check` on changed files if available; fix errors.

**Visual** — the gate is numeric; never assumed, never skipped silently. At verification start, write `figma-desktop.png` / `figma-mobile.png` into the visual-check folder.

- **Render:** `shopify theme dev` when available (Browser pane manages it via `.claude/launch.json` in the desktop app); otherwise the preview/live store URL. If neither is possible, stop and report exactly what's missing. If a dev/live disagreement reappears, work [environment-mismatch.md](environment-mismatch.md) before continuing — a wrong-state widget is never verified against.
- **Capture:** Browser pane screenshots if the capture-exactness check passed; otherwise connected browser MCP or installed Chrome; otherwise `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the cleanup ledger). The pane remains the interaction/inspection surface regardless.
- **Capture hygiene, before every capture:** exact Figma frame widths at the Figma screenshot's scale — identical pixel dimensions (diff tools require same-size inputs); clip to the widget container, not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle; reproduce each Figma widget state by interacting in the browser before capturing it.

**Hardcode** (main agent, before the loop): breadcrumb, then inject per §Hardcode-then-revert, so the loop measures the design rather than the app's pending art.

**Loop, per breakpoint and state** — with delegation, steps 1–3 and 5 run as ONE visual-verifier call per iteration; the main agent reads `verify-report-<n>.md`, performs step 4, and launches the next round. Without delegation, the loop runs in main as written.

1. **Computed styles first**: getComputedStyle on the key elements vs the Figma values (font-family/size/weight, line-height, letter-spacing, color, background, padding, margin, gap, border-radius). Fix every mismatch before looking at pixels.
2. **Pixel-diff gate**: the planned diff tool (installed direct, else npx) vs the Figma screenshot; record the diff ratio and save the diff image — every iteration.
3. **Live tracking**: immediately overwrite `result-<breakpoint>[-<state>].png` and `diff-<breakpoint>[-<state>].png` in the visual-check folder with this iteration's capture and diff. State suffixes must be approved; generate no `clean-`, `section-`, or other render variant.
4. **Diagnosis** (main agent): on failure, read the DIFF IMAGE / mismatch report to localize the mismatch, map it to a cause, fix, hard-refresh, re-capture, repeat from step 1.
5. **Leak check**: the overrides affect nothing outside the widget container.

**Revert** (main agent, the moment the loop exits — pass or cap): restore from the breadcrumb and prove it per §Hardcode-then-revert, before anything else.

**Exit:** PASS when the pixel-accurate definition holds at both breakpoints and all verified states. CAP after 8 iterations per breakpoint, or 2 consecutive iterations without diff-ratio improvement (the main agent tracks count and plateau across verifier reports) — then stop and report the final diff ratio, the diff image, and the suspected remaining cause. The threshold never drops silently. Note the report scope: fidelity is proven at the two captured widths only.

**Cleanup:** the ledger lists every temporary install (name, method, location). Once verification passes or caps: when `.agent/COMPONENTS.md` is at this skill's format, append the override-stylesheet row (plus the Animations row when the override introduces reusable motion), refresh its header and `updates:`, and rerun its format gate; absent, lower-format, and higher-format docs are reported and left unchanged. Uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall; `.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/` in full — the knowledge docs for the next run, plus `.agent/shopify-app-restyle/visual-check/<widget-name>/` (references, live-updated result/diff images, exported assets) — untracked via `.git/info/exclude`. The user reviews it, uploads the files `assets/UPLOAD.md` lists via the theme editor / app admin, and manages the folder themselves. Nothing from the task gets committed.

**Final output (no explanatory prose):** files created/changed; the revert proof (`grep -r VERIFY-HARDCODE` clean, no `vh-tmp-*` remaining) or **REVERT FAILED** with the breadcrumb path; final diff ratio per breakpoint/state with pass/cap status; the not-CSS-fixable list (if any), each hardcoded region named among them; any source-quality flags; any region where the original source ships instead of the crop, with both aspects; any inline-branch assets, named as not swappable from the app admin; the delegation map; the tooling ledger with removal confirmation (or "nothing installed"); knowledge-doc status — `app-widget-<app-handle>.md` reused (fresh) / updated / created; `.agent/THEME-CAPABILITIES.md` observed `format: <n>` and read as fresh/stale/higher-version-as-is, or absent (`format: unknown`; exact sections `## §Globals` + `## §CSS load` derived per-run); `.agent/COMPONENTS.md` observed `format: <n>` and row appended for the override stylesheet (+ Animations row when the override added reusable motion), or absent/lower/higher (`format: <n>`; skipped); the path `.agent/shopify-app-restyle/visual-check/<widget-name>/` with a one-line inventory (references, result/diff images, shipping crops and `original-source-*` counts per format, `UPLOAD.md`) and exclusion confirmation; which environment-mismatch step resolved any dev/live disagreement — and after step 8, confirmation the original theme is live again.

## Rules

- Read every file before editing; include the diff inline when editing an existing file.
- Gate-free once inputs are complete: the only stops are a missing input, genuine ambiguity, or the live publish swap — which never runs without the user's explicit go-ahead.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- The Browser pane leads when available; fallbacks apply only when it's absent or fails the capture-exactness check.
- The pixel-diff gate is mandatory: passing is numeric, eyeballing only diagnoses, and the threshold never drops silently.
- Only approved `figma-{breakpoint}[-{state}].png`, `result-{breakpoint}[-{state}].png`, and `diff-{breakpoint}[-{state}].png` names are generated at the visual-check root; overwrite result/diff files every iteration and generate no `clean-`, `section-`, or other render variant.
- `assets/` holds the design's crop for each Figma node, each raster's `original-source-*` beside it; reference captures at the folder root hold the frame. The bounds and identity checks keep a clipped or whole-frame render out.
- Upload the crops and let the CDN pick the format — no image encoder reaches the ledger.
- A hardcode is breadcrumbed before it exists and reverted on every exit — pass, cap, and abort — with the grep proof in the final output.
- `.agent/` lives at the repo root, is always excluded via `.git/info/exclude`, and is never committed.
- Knowledge docs first: read `.agent/shopify-app-restyle/app-widget-<app-handle>.md`, `.agent/THEME-CAPABILITIES.md`, and `.agent/COMPONENTS.md`, record each shared doc's `format:` value, and run the relevant format-version ladder before any widget inspection or theme scan; an inspection that runs writes the app-widget doc back before the task continues. Use the exact `## §Globals` and `## §CSS load` headings; an absent or stale THEME-CAPABILITIES doc triggers the declared per-run derivation. A passing run appends COMPONENTS rows only when that doc exists at this skill's format; absent, lower-format, and higher-format docs are reported and left unchanged. Refresh `updates:` and rerun the format gate after an append. An explicit user refresh always wins.
- Knowledge docs stay current: a passing restyle appends its override stylesheet as a `.agent/COMPONENTS.md` row (plus an Animations row when the override introduces reusable motion), refreshes its header and `updates:` list, and reruns the format spec's completeness gate (when the doc exists) before the final report.
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
