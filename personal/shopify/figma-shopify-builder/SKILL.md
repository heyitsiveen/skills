---
name: figma-shopify-builder
description: Build pixel-accurate Shopify sections or blocks from Figma designs. Use when the user shares Figma links (desktop + mobile node-ids) to implement in a theme, asks for a section or block added to a template, wants content editable via theme-editor settings, or wants it driven by metafields/metaobjects. Fidelity is measured — computed styles plus pixel diff against the Figma frames — never eyeballed.
---

# Figma → Shopify Builder

Build a theme section or block from two Figma frames and prove it pixel-accurate by measurement. Four phases — research (read-only on the theme), plan (stop for approval), implement, verify (numeric gate) — then cleanup that leaves the machine as found. Nothing is created or modified before plan approval except knowledge docs under `.agent/` (§Knowledge docs); the deliberate leftovers are the visual-check folder and the knowledge docs.

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

   Metafield/metaobject definitions and values live in Shopify admin, not theme code: the plan writes out the exact spec + sample values (matching the Figma copy) for the user to create; theme code only reads them and renders a graceful empty state when the data is absent.

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

Prefer the named custom agents `figma-extractor`, `theme-scanner`, and `visual-verifier` when installed in `~/.claude/agents/` or `.claude/agents/` — their definitions add tool-enforced restrictions (e.g. `disallowedTools: Write, Edit` on the verifier). Otherwise run the built-in general-purpose subagent with the embedded prompt below; in that fallback the no-theme-edits rule is instruction-enforced, so the prompt states it explicitly.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the Figma MCP / browser tools reach subagents (subagents inherit internal + MCP tools by default; the Browser pane's preview tools may be main-session-only). Any role whose tools don't reach a subagent runs in the main conversation instead.

**Handoff protocol:** subagents can't see the conversation and can't ask the user questions — every delegation prompt carries its exact inputs (node-ids, file paths, capture specs, the expected-values file path); every worker writes FULL findings to a report file in the temp working directory (the theme-scanner writes the missing knowledge docs instead — §Knowledge docs) and returns a short summary; ambiguities come back as OPEN QUESTIONS for the main agent to put to the user. The repeated-items inventory is figma-extractor output, but the json-vs-metaobject ask always happens in the main conversation. The temp working directory is created per run (use the session scratchpad when available) and is deleted at cleanup.

**Never delegated:** planning, user approvals, all implementation edits, the json-vs-metaobject ask, the metafield-data stop-and-hand-over, and the diagnosis/fix half of the verification loop.

| Role | Phase | Report |
|---|---|---|
| figma-extractor | 1, parallel | `figma-spec.md` |
| theme-scanner (read-only on the theme; runs only when a knowledge doc is absent or stale) | 1, parallel | `.agent/THEME-CAPABILITIES.md` (when absent/stale) + `.agent/COMPONENTS.md` (when absent/stale) |
| visual-verifier (never edits theme files) | 4, one call per iteration | `verify-report-<n>.md` |

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
5. Asset inventory: every exportable asset (layer name, raster or vector).

Write the FULL findings to {temp-dir}/figma-spec.md with an OPEN QUESTIONS
section at the end for anything ambiguous. Return only a 3–5 line summary plus
the open questions.
```

### theme-scanner prompt

```
You are scanning a Shopify theme to ground a new {section|block} build.
READ-ONLY on the theme: your only writes are the knowledge docs named below.

Theme repo: {repo-path}
Target template: {template-path}
Requested placement: {placement}
Data source: {theme settings | metafields — owner type + namespace.key(s)}
Run: {items, from the main agent's doc check — 1 when THEME-CAPABILITIES.md
is absent/widely stale (FULL) or a few entries changed (INCREMENTAL — only:
{list}) · 2 when COMPONENTS.md is absent or stale · 3 and 4 always}

Report on:
1. The capability catalog — every doc section, exact setting ids, types,
   labels, options/ranges, defaults:
   §Globals — config/settings_schema.json (schema only: current
   config/settings_data.json values are merchant-volatile, so the main agent
   reads them live, never from the doc) and where globals become CSS
   variables (layout/theme.liquid, css-variables snippet, base CSS).
   §Section catalog — every section in sections/: display name, full
   settings list, block types with their settings, presets; FLAG responsive
   settings and per-instance custom CSS/Liquid settings.
   §Theme blocks — blocks/ (if present), same detail.
   §Inheritance — per color/typography/radius/border setting: INHERITS from
   a global or takes a raw per-instance value.
   §Conventions — usage conventions from other templates/*.json plus
   authoring conventions from 2–3 representative sections: schema style,
   CSS scoping, class naming, breakpoints.
   §Block architecture — blocks/ dir vs blocks defined in host section
   schemas.
   §Metafield patterns — sections that already read metafields/metaobjects
   and their exact access patterns.
   §CSS load — how the theme loads custom CSS: asset naming, include point.
2. The FULL reuse inventory: every customElements.define registration
   (→ Custom web components); reusable JS utils not tied to one component
   (→ JavaScript); parameterized Liquid utility snippets/filters
   (→ Functions); multi-step flows, e.g. add-to-cart, quick-view (→ Flows);
   recurring structural patterns, e.g. drawer, sticky header (→ Patterns).
   One row per item, minor items included — a thin row beats an omission:
   name | file path(s) | what it does | reuse keywords.
3. PER-RUN — return in your summary, never in a doc: the target template's
   placement anchor in `order` (or the host section's `block_order`) for
   "{placement}" — OPEN QUESTION if ambiguous.
4. PER-RUN (same): does .git/info/exclude carry a `.agent/` line?

Write item 1 to .agent/THEME-CAPABILITIES.md (FULL creates the doc;
INCREMENTAL updates only the listed entries plus the header) and item 2 to
.agent/COMPONENTS.md — five category tables in the order above — each
opening with this header:
{knowledge-doc header, filled at dispatch — §Knowledge docs}
Return only a 3–5 line summary, the per-run findings (3, 4), and the open
questions.
```

### visual-verifier prompt

```
You are measuring one verification iteration of a Shopify {section|block}
against its Figma reference. You NEVER edit theme files — measure, record,
report only.

Iteration: {n} — breakpoint {desktop|mobile}, width {w}px, scale {s}, expected
capture dimensions {W}x{H}px
Render at: {dev-server-url | static-html-path}
Clip to container: {selector}
Figma reference: .agent/figma-shopify-builder/visual-check/{name}/images/
figma-{breakpoint}.png
Expected values: {temp-dir}/figma-spec.md
Key elements to assert: {list from the approved plan}
Diff tool: {npx pixelmatch … | npx odiff-bin …} (anti-aliasing ignored)

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
4. Overwrite .agent/figma-shopify-builder/visual-check/{name}/images/
   result-{breakpoint}.png and diff-{breakpoint}.png with THIS iteration's
   capture and diff.

Write the FULL report to {temp-dir}/verify-report-{n}.md: mismatch table, diff
ratio, largest diff regions and where they sit. Return only the diff ratio,
mismatch count, and one line on the biggest offender.
```

## Knowledge docs — scan once, reuse

`.agent/` at the theme repo root holds every durable artifact this skill suite produces: shared knowledge docs at its root, per-skill outputs under `.agent/<skill-name>/`. Knowledge docs are written for an AI reader — tables, exact identifiers (filenames, setting ids, types, defaults), rules and constraints, zero filler prose — and are the one exception to "nothing before approval": a scan writes its doc immediately, so the knowledge survives even an abandoned run.

This skill's docs:

- **`.agent/THEME-CAPABILITIES.md`** — the capability catalog, fixed sections: §Globals · §Section catalog · §Theme blocks · §Inheritance · §Conventions · §Block architecture · §Metafield patterns · §CSS load. Produced whole by this skill's scanner when absent or widely stale — a few changed files → INCREMENTAL update of just those entries; identical shape whichever skill produced it, so a doc found present and fresh is simply read. This skill reads §Globals + §Conventions always, §Metafield patterns for a metafields source, §Block architecture for a block build. After verification passes, append the built section's/block's entry to §Section catalog or §Theme blocks (plus §Inheritance rows for its settings) and refresh the header — the doc stays current with what this skill adds.
- **`.agent/COMPONENTS.md`** — the reuse inventory: five category tables (Custom web components · JavaScript · Functions · Flows · Patterns), row schema `name | file path(s) | what it does | reuse keywords`. Produced only when absent or stale — the theme-scanner produces the FULL inventory (item 2); present and fresh → read it (identical shape whichever skill produced it). Search it by reuse keyword before writing new code — match → reuse or extend. After verification passes, append a row for the built section/block (and any new custom element) and refresh the header — the inventory stays current.

Every knowledge doc opens with this header — identical fields no matter which skill produced the doc (COMPONENTS.md's refresh phrase is "refresh components"; THEME-CAPABILITIES.md's is "refresh theme capabilities"):

```
---
generated: <YYYY-MM-DD>
skill: <producing skill> (<agent role>)
theme: <theme name>
git: <branch> @ <short SHA>
scanned: <dirs + file counts>
refresh: user says "refresh <components | theme capabilities>" → regenerate
---
```

**Read before the theme scan (main agent, Phase 1):**

1. Read `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` when they exist.
2. Freshness check: each doc's file lists and `scanned:` counts vs the current `sections/`/`blocks/`/JS-source listings, its header git line vs the current branch + short SHA. Both present and fresh → skip the scan; read the placement anchor and `.git/info/exclude` inline, done. A doc absent or widely stale → the scanner produces it in full; `.agent/THEME-CAPABILITIES.md` with a few changed files → INCREMENTAL update of just those entries.
3. The scanner writes the missing docs BEFORE planning continues.
4. An explicit user refresh ("refresh theme capabilities" / "refresh components" or similar) always wins: the scanner regenerates that doc.

**Root pointer:** the repo's root `AGENTS.md`/`CLAUDE.md` names this convention so future sessions find the docs before rescanning. Missing → append it (or create a minimal `CLAUDE.md` holding just this block, excluded like everything else) as a planned edit:

```
## 📚 Knowledge docs (check before any theme scan)
Skill outputs + knowledge docs live under `.agent/` — shared docs at its root,
per-skill outputs in `.agent/<skill-name>/`. Read `.agent/THEME-CAPABILITIES.md`
before any theme scan and search `.agent/COMPONENTS.md` before writing new
code; freshness checks + refresh instructions in their headers.
```

## The visual-check folder

`.agent/figma-shopify-builder/visual-check/<section-or-block-name>/` in the theme repo, kebab-cased from the section/block name (e.g. `.agent/figma-shopify-builder/visual-check/hero/`):

- `images/figma-desktop.png`, `images/figma-mobile.png` — references, written once at verification start.
- `images/result-desktop.png`, `images/result-mobile.png`, `images/diff-desktop.png`, `images/diff-mobile.png` — overwritten after EVERY verification iteration, so the folder always shows the latest attempt and progress stays trackable across trial and error.
- `assets/images/` + `assets/svg/` — every asset in the Figma frames (images, icons, illustrations, logos) exported via the Figma MCP: 4x-scale PNG for all assets into `assets/images/`, vectors additionally as SVG into `assets/svg/`, filenames kebab-cased from Figma layer names. Upload-ready for Shopify: assigned to `image_picker` settings (theme-settings source) or uploaded as Files and referenced from metafield/metaobject values (metafields source).

The folder is not theme code: `.agent/` stays out of git via a `.git/info/exclude` line (confirm the `.agent/` line exists; append it as a planned edit if not — a local, never-committed file, and the Shopify CLI ignores non-theme root directories, so it is never pushed). It is retained at the end: the user reviews it, uploads assets, and manages or deletes it themselves.

## Phase 1 — Research (read-only on the theme)

Run the two delegations in parallel, plus tooling detection. No theme file is created or modified; the only writes are the missing knowledge docs (§Knowledge docs).

- **Figma extraction** → figma-extractor: both frames via the Figma MCP; exact-values table (implementation targets AND expected values for verification); screenshot scale + pixel dimensions; desktop/mobile differences; repeated-items inventory; asset inventory. Report: `figma-spec.md`.
- **Theme reads** — knowledge-doc check first (§Knowledge docs): both docs present and fresh → read them, then the placement anchor and `.git/info/exclude` inline, done. Otherwise → theme-scanner: the full capability catalog when `.agent/THEME-CAPABILITIES.md` is absent or widely stale (INCREMENTAL entries when a few files changed); the full reuse inventory when `.agent/COMPONENTS.md` is absent or stale; per-run, the template placement anchor (OPEN QUESTION if ambiguous) and the exclude check. Produces the missing docs. Where globals exist the plan maps each Figma value to them; where they don't, Figma values apply directly — unmapped values get listed, never silently decided.
- **Tooling detection** (main agent, non-mutating checks only): Browser pane availability first, then fallbacks per Browser tiers; run the capture-exactness check; the Agent tool and which tools reach subagents (fix the delegation map); Shopify CLI + `shopify.theme.toml` (desktop app: `shopify theme dev` defined in `.claude/launch.json` so the pane manages the server); Python for the static-approximation fallback; Node/npx for the pixel-diff tool (`npx pixelmatch` / `npx odiff-bin`). Record the render tier, capture tier, and any temporary installs required.

**Done when:** `figma-spec.md` exists; `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` exist and are current (produced this run if absent); every OPEN QUESTION has been put to the user and answered — including the json-vs-metaobject ask when the source is metafields and the design repeats — and the tooling record names render tier, capture tier, delegation map, and required temp installs.

## Phase 2 — Plan (stop for approval)

Present the complete plan and stop. Create or modify nothing until the user approves. Approving the plan also approves the listed temporary installs.

The plan states:

- **File**: filename + display name.
- **Schema**, per data source — theme settings: every text/link/image editable with defaults matching the Figma copy; images via `image_picker` (Figma images are sizing reference only — the exported assets are what the user uploads and assigns in the theme editor); repeated items as editor blocks. Metafields: which content is metafield-driven (repeated items render from the data, not editor blocks) and which residual settings remain in the schema.
- **Data-source mapping** (metafields only): each Figma content element → the metafield that fills it, with owner type and resolution. For repeated items, the chosen type in FULL — json: namespace.key, owner type, exact item schema (every key: type + the Figma element it fills), malformed-item handling; metaobject: definition type, every field key (type + the Figma element it fills), access path (`list.metaobject_reference` vs `shop.metaobjects`), entry-ordering mechanism. Plus sample values matching the Figma copy, written ready to create in admin, and which fields connect via dynamic sources.
- **Typography/color mapping**: table to theme globals, or hardcode note; unmapped values flagged.
- **Breakpoints**: responsive strategy.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append adding it.
- **Asset-export list**: every inventoried asset → 4x PNG into `.agent/figma-shopify-builder/visual-check/<name>/assets/images/`, vectors additionally as SVG into `assets/svg/`, kebab-case names from Figma layers; separately, any code-referenced assets that also go into the theme's `assets/`.
- **Template diff**: the exact JSON diff (new key in `sections` + `order` position, or block entry + `block_order` position).
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced so far.
- **Verification approach**: browser tier (with the capture-exactness result), render tier, whether `.claude/launch.json` will be created/updated (a planned file if so), capture widths and scale, key elements for computed-style assertions, pixel-diff tool + pass threshold (default: diff ratio ≤ 1%, anti-aliasing ignored), iteration cap (default: 8 per breakpoint, plateau exit after 2 iterations without improvement), and the exact temporary-install list with method (npx / project-local / venv) and removal confirmation.

**Done when:** the user has approved.

## Phase 3 — Implement (main agent only)

Touch only planned files; no delegated edits.

- Create the section/block file per the plan: mapped globals where they exist, exact Figma values otherwise; both breakpoints exact.
- Metafields source: the Liquid reads the approved metafields — iterating `metafield.value` for json (validating and skipping malformed items), or the metaobject entries' fields per the approved access path and ordering — with exact access syntax verified via the Shopify dev MCP, dynamic sources connected where the editor supports them, and a graceful empty state when data is absent.
- Edit the template JSON exactly as approved, showing the diff again before writing.
- Append the `.agent/` line to `.git/info/exclude` if planned.
- Export the Figma assets per the approved list via the Figma MCP: all assets into `.agent/figma-shopify-builder/visual-check/<name>/assets/images/` and `assets/svg/`, code-referenced ones also into the theme's `assets/`.

**Done when:** every planned file exists as approved and nothing else changed.

## Phase 4 — Verify

**Static:** the template JSON still parses; `shopify theme check` on changed files if available; fix errors.

**Visual** — the gate is numeric; never assumed, never skipped silently. At verification start, write `images/figma-desktop.png` / `images/figma-mobile.png` into the visual-check folder.

- **Render:** `shopify theme dev` when the CLI + `shopify.theme.toml` exist (desktop app: the Browser pane manages it via `.claude/launch.json`). Otherwise a static approximation via a temporary Liquid engine (e.g. `python-liquid` in a throwaway venv) with schema defaults stubbed and relevant theme CSS inlined — flagged as an approximation; the computed-style and pixel-diff layers still run against it in a real browser (the pane opens the static HTML directly). Blocks render within their host section.
- **Metafield data check** (metafields source, before the loop, main agent): `theme dev` renders the dev store's REAL metafield/metaobject data. Confirm the approved definitions and values exist and match the plan's spec; if they don't, STOP and hand the user the exact definition spec + sample values from the approved plan to create in admin, then resume once populated — verification never runs against an empty or wrong-shape render. The static approximation instead stubs the values with the Figma copy per the plan's mapping.
- **Capture:** Browser pane screenshots if the capture-exactness check passed; otherwise connected browser MCP or installed Chrome; otherwise `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the cleanup ledger). The pane remains the inspection/diagnosis surface regardless.
- **Capture hygiene, before every capture:** exact Figma frame widths at the Figma screenshot's scale — identical pixel dimensions (diff tools require same-size inputs); clip to the section/block container, not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle; stub or hide dynamic content not part of the comparison.

**Loop, per breakpoint** — with delegation, steps 1–3 run as ONE visual-verifier call per iteration; the main agent reads `verify-report-<n>.md`, performs step 4, and launches the next round. Without delegation, the loop runs in main as written.

1. **Computed styles first**: getComputedStyle on the key elements vs the Figma values (font-family/size/weight, line-height, letter-spacing, color, background, padding, margin, gap, border-radius). Fix every mismatch before looking at pixels.
2. **Pixel-diff gate**: `npx pixelmatch` or `npx odiff-bin` vs the Figma screenshot; record the diff ratio and save the diff image — every iteration.
3. **Live tracking**: immediately overwrite `images/result-*.png` and `images/diff-*.png` in the visual-check folder with this iteration's capture and diff.
4. **Diagnosis** (main agent): on failure, read the DIFF IMAGE / mismatch report to localize the mismatch and map it to a cause — metafields source: distinguish a code/style cause from a DATA cause; wrong or missing values get reported to the user with corrected sample values, not patched around in code. Fix, re-render, re-capture, repeat from step 1.

**Exit:** PASS when the pixel-accurate definition holds at both breakpoints. CAP after 8 iterations per breakpoint, or 2 consecutive iterations without diff-ratio improvement (the main agent tracks count and plateau across verifier reports) — then stop and report the final diff ratio, the diff image, and the suspected remaining cause. The threshold never drops silently. Note the report scope: fidelity is proven at the two captured widths only.

If no render or capture path exists even with temporary installs: stop and report exactly what's missing.

**Cleanup:** the ledger lists every temporary install (name, method, location). Once verification passes or caps: update the knowledge docs — the built section's/block's entry into `.agent/THEME-CAPABILITIES.md` (§Section catalog or §Theme blocks, plus §Inheritance rows for its settings) and a row for it (and any new custom element) into `.agent/COMPONENTS.md`, refreshing both headers (date, git line, scanned counts); uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall; `.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/` in full — the knowledge docs for the next run, plus `.agent/figma-shopify-builder/visual-check/<name>/` (references, live-updated result/diff images, exported assets) — untracked via `.git/info/exclude`. The user reviews the comparisons before committing, uses the assets per the data source (theme-editor `image_picker` assignment, or Files upload referenced from metafield/metaobject values), and manages the folder themselves. Nothing lands in git except the planned theme files.

**Final output (no explanatory prose):** files created/changed; [metafields] the final definition spec + sample values as created/confirmed, plus empty-state confirmation; final diff ratio per breakpoint with pass/cap status; the delegation map; the tooling ledger with removal confirmation (or "nothing installed"); knowledge-doc status — `.agent/THEME-CAPABILITIES.md` reused (fresh) / updated / created and `.agent/COMPONENTS.md` reused / created, plus the post-build updates: the new build's catalog entry and its inventory row, headers refreshed; the path `.agent/figma-shopify-builder/visual-check/<name>/` with a one-line inventory (references, result/diff images, asset counts per format) and exclusion confirmation.

## Rules

- Read every file before editing; show a diff before overwriting anything existing.
- Ask instead of assuming — including the json-vs-metaobject choice when the source is metafields, the data repeats, and the user hasn't specified it.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- Metafield data must exist and match the spec before verification — otherwise stop and hand over the spec.
- The Browser pane leads when available; fallbacks apply only when it's absent or fails the capture-exactness check.
- The pixel-diff gate is mandatory: passing is numeric, and the threshold never drops silently.
- Result/diff images are overwritten every iteration — the folder always shows the latest attempt.
- `.agent/` lives at the repo root, is always excluded via `.git/info/exclude`, and is never committed.
- Knowledge docs first: read `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md`, freshness-checked, before any theme scan; a missing or stale doc is produced or updated before the task continues. An explicit user refresh always wins.
- Knowledge docs stay current: a passing build writes its new section/block into both docs (catalog entry + inventory row, headers refreshed) before the final report.
- Verify Liquid/schema syntax — including metafield and metaobject access — via the Shopify dev MCP instead of guessing.
- Prefer `npx` over `npm i -g`; project-local or venv installs over global ones.
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
