---
name: figma-shopify-composer
description: Compose a pixel-accurate recreation of a Figma design from a theme's EXISTING sections, blocks, and settings — assemble and configure what the theme already ships, writing template JSON only: no new code, no new files, no new settings, no schema edits. Use when the user wants a Figma frame recreated by reusing existing sections or blocks, or asks to compose/assemble a design from existing settings only. Building a NEW section or block file from Figma is figma-shopify-builder's job — this skill only configures what already exists. Fidelity is measured — computed styles plus pixel diff against the Figma frames — never eyeballed.
---

# Figma → Shopify Composer

Recreate two Figma frames by composing the theme's existing sections, blocks, and settings — configuration, not code — and prove it pixel-accurate by measurement. The palette is fixed to what the theme already ships, so fidelity is forecast before anything is built and measured against that forecast after. Four phases — research (read-only on the theme), plan (stop for approval), implement (template JSON only), verify (numeric gate) — then cleanup that leaves the machine as found. Nothing is created or modified before plan approval except knowledge docs under `.agent/` (§Knowledge docs); the deliberate leftovers are the visual-check folder and the knowledge docs.

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
- Prefer settings that inherit from global theme settings (colors, typography, radius, borders, buttons) over per-instance raw values — the result stays wired into the theme's design system.

## Pixel-accurate is a measured result

The composition passes when, per breakpoint:

1. Every checked computed style matches its Figma value.
2. The image diff ratio against the Figma screenshot is ≤ 1% with anti-aliasing ignored, measured ON UNMASKED REGIONS — every masked region is individually approved in the plan (unassigned `image_picker` regions, accepted gaps).
3. Residual diff pixels are confirmed FROM THE DIFF IMAGE to be text-rasterization noise — Figma and Chromium rasterize fonts differently, so a literal 0% is unreachable. Layout, color, or spacing differences are never "noise".

The palette is fixed to existing capabilities, so the plan states upfront what will match EXACTLY, what APPROXIMATES, and what is UNACHIEVABLE without new code; the user approves that fidelity forecast before anything is written. Side-by-side eyeballing is for diagnosis only; passing is numeric.

## Browser tiers

**Primary: the Claude Code Desktop Browser pane** (desktop app with Browser enabled). Claude drives it directly — screenshots, DOM/computed-style inspection, interaction — and manages the dev server via `.claude/launch.json` (local dev servers need no site approval; preview/live store URLs are external sites and trigger a one-time permission card — Allow once / Always allow).

**Capture-exactness check:** the measured diff needs captures at the exact Figma frame widths and scale, with identical pixel dimensions, clipped to the composed region. Confirm the pane's screenshots can honor that; if not, the pane still does inspection and diagnosis while the MEASURED captures fall to the first fallback that can.

**Fallbacks, in order:** connected browser MCP (Chrome DevTools MCP / Playwright MCP) → installed Chrome → temporary Playwright via npx.

## Delegation

Bounded research and measurement go to subagents — isolated workers with their own context windows that return only a final report. Delegation earns its keep most in the capability inventory: scanning every section's schema would otherwise flood the main conversation. Delegation multiplies tokens: skip it for trivially small reads.

Prefer the named custom agents `figma-extractor`, `theme-scanner`, and `visual-verifier` when installed in `~/.claude/agents/` or `.claude/agents/` — their definitions add tool-enforced restrictions (e.g. `disallowedTools: Write, Edit` on the verifier). Otherwise run the built-in general-purpose subagent with the embedded prompt below; in that fallback the no-theme-edits rule is instruction-enforced, so the prompt states it explicitly.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the Figma MCP / browser tools reach subagents (subagents inherit internal + MCP tools by default; the Browser pane's preview tools may be main-session-only). Any role whose tools don't reach a subagent runs in the main conversation instead.

**Handoff protocol:** subagents can't see the conversation and can't ask the user questions — every delegation prompt carries its exact inputs (node-ids, file paths, the requirements list, the approved mask list, capture specs); every worker writes FULL findings to a report file in the temp working directory (the theme-scanner writes the canonical knowledge doc instead — §Knowledge docs) and returns a short summary; ambiguities come back as OPEN QUESTIONS for the main agent to put to the user. The temp working directory is created per run (use the session scratchpad when available) and is deleted at cleanup.

**Never delegated:** the requirements-to-capabilities matching (1c — the synthesis that feeds the fidelity forecast), planning and every user approval (forecast, mask list, global-value changes), all implementation edits, and the diagnosis/fix half of the verification loop.

| Role | Phase | Report |
|---|---|---|
| figma-extractor | 1a, parallel | `figma-spec.md` |
| theme-scanner (read-only on the theme; runs only when `.agent/THEME-CAPABILITIES.md` is absent or stale) | 1b, parallel — shard across 2–3 instances on very large themes | `.agent/THEME-CAPABILITIES.md` (canonical; shards `{temp-dir}/THEME-CAPABILITIES-<n>.md`, merged into it by the main agent) |
| visual-verifier (never edits theme files) | 4, one call per iteration | `verify-report-<n>.md` |

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
4. Asset inventory: every exportable asset (layer name, raster or vector).
5. The REQUIREMENTS LIST — the distilled design: layout structure per
   breakpoint; each content element (headings, text, CTAs/buttons, images,
   badges); each style requirement (colors, typography, radius, borders,
   spacing, alignment).

Write the FULL findings to {temp-dir}/figma-spec.md with an OPEN QUESTIONS
section at the end for anything ambiguous. Return only a 3–5 line summary plus
the open questions.
```

### theme-scanner prompt

```
You are building the CAPABILITY INVENTORY of a Shopify theme: everything its
existing sections, blocks, and settings can already do. A Figma design will be
recreated from these capabilities alone — no new code — so what you catalog
decides what is achievable. READ-ONLY on the theme: your only writes are the
knowledge doc named below and, if sharded, your shard report.

Theme repo: {repo-path}
Target template: {template-path}
Requested placement: {placement}
Composition type: {section | block}
Scope: {full theme | shard — sections {range} only}
Mode: {FULL | INCREMENTAL — refresh only these stale/missing entries: {list}}

Catalog as a structured reference — exact setting ids, types, labels,
options/ranges, defaults:
1. Global design tokens: config/settings_schema.json — ids, types, labels,
   options/ranges, defaults. Schema only: current config/settings_data.json
   values are merchant-volatile, so the main agent reads them live, never
   from the doc. Also where globals become CSS variables
   (layout/theme.liquid, css-variables snippet, base CSS): color
   schemes/roles, typography scales, button styles, border radius, borders,
   spacing/layout options.
2. Every section in sections/ (within scope): display name, full settings
   list, its block types with their settings, presets. FLAG responsive
   settings — anything that differs per breakpoint (columns_desktop /
   columns_mobile, mobile layout switches, per-breakpoint spacing or image
   behavior) — these make desktop/mobile Figma differences achievable without
   code. Also flag any per-instance custom CSS/Liquid setting.
3. Theme blocks in blocks/ (if present), same detail.
4. Inheritance trace: for every color/typography/radius/border setting on a
   section or block, whether it INHERITS from a global (color scheme, CSS
   variable) or takes a raw per-instance value.
5. Conventions: usage conventions from other templates/*.json (realistic
   settings combinations for the cataloged sections) plus authoring
   conventions from 2–3 representative sections — schema style, CSS
   scoping, class naming, breakpoints.
6. Block architecture: blocks/ directory vs blocks defined inside host
   section schemas.
7. Metafield patterns: sections that already read metafields/metaobjects
   and their exact access patterns.
8. CSS load: how the theme loads custom CSS — asset naming, include point.
9. PER-RUN — return in your summary, never in the doc: the target template's
   placement anchor for "{placement}" in `order` (or the host section
   instance and its `block_order` for a block composition) — OPEN QUESTION
   if ambiguous.
10. PER-RUN (same): does .git/info/exclude carry a `.agent/` line?

Write the catalog to .agent/THEME-CAPABILITIES.md, opening with this header:
{knowledge-doc header, filled at dispatch — §Knowledge docs}
FULL mode covers every doc section; INCREMENTAL mode updates
only the listed entries plus the header. Sharded runs write
{temp-dir}/THEME-CAPABILITIES-{n}.md instead — the main agent merges them
into the canonical doc. Return only a 3–5 line summary, the per-run
findings (9–10), and the open questions.
```

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
images/figma-{breakpoint}.png
Approved mask list: {region → reason, from the approved plan} — apply exactly;
never add or grow a mask
Expected values: {temp-dir}/figma-spec.md
Capability map for tagging: .agent/THEME-CAPABILITIES.md + the approved
settings map
Key elements to assert: {list from the approved plan}
Diff tool: {npx pixelmatch … | npx odiff-bin …} (anti-aliasing ignored)

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
   images/result-{breakpoint}.png and diff-{breakpoint}.png with THIS
   iteration's capture and diff.

Write the FULL report to {temp-dir}/verify-report-{n}.md: diff ratio, mismatch
table with every mismatch TAGGED either "settings-fixable per the capability
map" (name the setting) or "undeclared gap", largest diff regions and where
they sit. Return only the diff ratio, mismatch count by tag, and one line on
the biggest offender.
```

## Knowledge docs — scan once, reuse

`.agent/` at the theme repo root holds every durable artifact this skill suite produces: shared knowledge docs at its root, per-skill outputs under `.agent/<skill-name>/`. Knowledge docs are written for an AI reader — tables, exact identifiers (section filenames, setting ids, types, defaults), composition rules and constraints, zero filler prose — and are the one exception to "nothing before approval": a scan writes its doc immediately, so the knowledge survives even an abandoned run.

This skill's canonical doc — **`.agent/THEME-CAPABILITIES.md`**, fixed sections: §Globals · §Section catalog · §Theme blocks · §Inheritance · §Conventions · §Block architecture · §Metafield patterns · §CSS load. Produced whole by this skill's scanner when absent or widely stale — a few changed files → INCREMENTAL update; an explicit refresh always regenerates. The shape is fixed, so a doc found present and fresh is simply read, whichever skill produced it. Consulted when present: `.agent/COMPONENTS.md` (the reuse inventory — its Flows/Patterns rows map design requirements to candidate sections).

Every knowledge doc opens with this header:

```
---
generated: <YYYY-MM-DD>
skill: <producing skill> (<agent role>)
theme: <theme name>
git: <branch> @ <short SHA>
scanned: <dirs + file counts>
refresh: user says "refresh theme capabilities" → regenerate
---
```

**Read before any scan (main agent, at 1b):**

1. Read `.agent/THEME-CAPABILITIES.md` when it exists.
2. Freshness check: its §Section catalog and §Theme blocks file lists vs `ls sections/ blocks/`, its header git line vs the current branch + short SHA. Present and fresh → skip the scan; read the placement anchor and `.git/info/exclude` inline (two small reads) and 1b is done. A few new or changed files → INCREMENTAL scan of just those entries. Absent or widely stale → FULL scan.
3. The scanner writes/updates the doc BEFORE 1c matching continues.
4. An explicit user refresh ("refresh theme capabilities" or similar) always wins: FULL rescan, doc rewritten.

**Root pointer:** the repo's root `AGENTS.md`/`CLAUDE.md` names this convention so future sessions find the docs before rescanning. Missing → append it (or create a minimal `CLAUDE.md` holding just this block, excluded like everything else) as a planned edit:

```
## 📚 Knowledge docs (check before any theme scan)
Skill outputs + knowledge docs live under `.agent/` — shared docs at its root,
per-skill outputs in `.agent/<skill-name>/`. Read `.agent/THEME-CAPABILITIES.md`
before any theme scan and search `.agent/COMPONENTS.md` before writing new
code; freshness checks + refresh instructions in their headers.
```

## The visual-check folder

`.agent/figma-shopify-composer/visual-check/<composition-name>/` in the theme repo, `<composition-name>` kebab-cased from the Figma frame name (e.g. `.agent/figma-shopify-composer/visual-check/hero/`):

- `images/figma-desktop.png`, `images/figma-mobile.png` — references, written once at verification start.
- `images/result-desktop.png`, `images/result-mobile.png`, `images/diff-desktop.png`, `images/diff-mobile.png` — overwritten after EVERY verification iteration, so the folder always shows the latest attempt and progress stays trackable across trial and error.
- `assets/images/` + `assets/svg/` — every asset in the Figma frames (images, icons, illustrations, logos) exported via the Figma MCP: 4x-scale PNG for all assets into `assets/images/`, vectors additionally as SVG into `assets/svg/`, filenames kebab-cased from Figma layer names. Upload-ready for the Shopify theme editor, where the user assigns them to the existing sections' `image_picker` settings.

The folder is not theme code: `.agent/` stays out of git via a `.git/info/exclude` line (confirm the `.agent/` line exists; append it as a planned edit if not — a local, never-committed file, and the Shopify CLI ignores non-theme root directories, so it is never pushed). It is retained at the end: the user reviews it, uploads assets, and manages or deletes it themselves.

## Phase 1 — Research (read-only on the theme)

Run 1a and 1b in parallel, then match in main. No theme file is created or modified; the one write is the knowledge doc (§Knowledge docs).

- **1a. Figma requirements** → figma-extractor: both frames via the Figma MCP; exact-values table (the settings-configuration targets AND the expected values for verification's computed-style assertions); per-breakpoint layout structure and desktop/mobile differences; screenshot scale + pixel dimensions; asset inventory; the distilled REQUIREMENTS LIST. Report: `figma-spec.md`.
- **1b. Capability inventory** — knowledge-doc check first (§Knowledge docs): present and fresh → read it, then the placement anchor and `.git/info/exclude` inline, done. Otherwise → theme-scanner (FULL or INCREMENTAL): global design tokens (schema) and their CSS-variable outputs; every section's settings/blocks/presets with responsive settings flagged; theme blocks; the inheritance trace (global-connected vs raw per-instance) for every color/typography/radius/border setting; usage + authoring conventions; block architecture; metafield access patterns; custom-CSS load conventions; per-run, the target-template placement anchor (OPEN QUESTION if ambiguous) and the exclude check. Writes `.agent/THEME-CAPABILITIES.md`, sharded across 2–3 scanners on very large themes and merged by the main agent. Current global values: read live from `config/settings_data.json` in main.
- **1c. Match requirements to capabilities** (main agent, from `figma-spec.md` + `.agent/THEME-CAPABILITIES.md`): for every requirement, the existing capability that achieves it — which section type (or stack of section instances), which block types, which settings and values, per breakpoint. Where a style value should come from a global, check whether the CURRENT global value already equals the Figma value — if it doesn't, that is a decision point, never a silent change. Anything with no existing capability is a GAP: record the closest achievable approximation and its visible cost, and whether an existing per-instance custom CSS/Liquid setting (an existing setting, so within the constraint) could close it.
- **1d. Tooling detection** (main agent, non-mutating checks only): Browser pane availability first, then fallbacks per Browser tiers; run the capture-exactness check; the Agent tool and which tools reach subagents (fix the delegation map). Render path: Shopify CLI + `shopify.theme.toml` → `shopify theme dev` (desktop app: defined in `.claude/launch.json` so the pane manages the server); otherwise a preview/live store URL. There is NO static-render fallback — composed existing sections depend on the full theme runtime (snippets, global settings, theme CSS/JS), which a local Liquid engine cannot reproduce. Diff tool: Node/npx for `npx pixelmatch` / `npx odiff-bin`. Record the tiers and any temporary installs required.
- **1e. Ask**: put anything still ambiguous — including OPEN QUESTIONS from the reports — to the user as concise questions before planning.

**Done when:** `figma-spec.md` exists and `.agent/THEME-CAPABILITIES.md` is current (fresh header); every requirement is matched to a capability or recorded as a gap; every OPEN QUESTION is answered; and the tooling record names browser tier, capture source (exactness result), render path, diff tool, delegation map, temp dir, and the exclude status.

## Phase 2 — Plan (stop for approval)

Present the complete plan and stop. Create or modify nothing until the user approves. Approval covers the temporary installs, the mask list, and any global-value change or custom-CSS usage the plan explicitly lists.

- **Composition**: which existing section type(s) — one instance or a stack — and/or which existing block types, in what order.
- **Settings map**: for every chosen section instance and block, every setting id → value, per breakpoint where responsive settings exist, with the Figma value it satisfies. Text/link settings carry the Figma copy. Image settings stay unassigned — the user uploads the exported assets via the theme editor and assigns them; their regions go on the mask list.
- **Global-inheritance table**: requirement → global-connected setting used → whether the current global value already matches Figma. Where it doesn't, the user picks one: a per-instance override setting (if one exists) / changing the global VALUE — flagged loudly, it restyles the whole storefront / accepting the current global as an approved gap.
- **Fidelity forecast**: EXACT (fully met by existing capabilities), APPROXIMATE (closest achievable, visible cost described), UNACHIEVABLE without new code — accept as a gap or defer to the figma-shopify-builder skill. A per-instance custom CSS/Liquid setting proposed as a gap-closer is its own flagged line item.
- **Mask list**: unassigned image regions + every approved gap, each with its reason. The gate applies to everything unmasked.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append adding it.
- **Asset-export list**: every inventoried asset → 4x PNG into `.agent/figma-shopify-composer/visual-check/<composition-name>/assets/images/`, vectors additionally as SVG into `assets/svg/`, kebab-case names from Figma layers.
- **Template diff**: the exact JSON — new entries in `sections` (type = existing section file, with the settings map and `blocks` + `block_order`) inserted into `order` at the input placement; or, for a block composition, the block entries and `block_order` position inside the host section instance.
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced so far.
- **Verification approach**: browser tier (with the capture-exactness result), render path, whether `.claude/launch.json` will be created/updated (a planned file if so), capture widths and scale, key elements for computed-style assertions, pixel-diff tool + pass threshold (default: diff ratio ≤ 1% on unmasked regions, anti-aliasing ignored), iteration cap (default: 8 per breakpoint, plateau exit after 2 iterations without improvement), and the exact temporary-install list with method (npx / project-local / venv) and removal confirmation.

**Done when:** the user has approved.

## Phase 3 — Implement (main agent only)

Touch only planned files; no delegated edits.

- Edit the target template JSON exactly as approved — section entries with their settings maps and block configurations at the approved position — showing the diff again before writing.
- Apply any approved global-value change in `config/settings_data.json` exactly as listed in the plan, and nothing beyond it.
- Append the `.agent/` line to `.git/info/exclude` if planned.
- Export the Figma assets per the approved list via the Figma MCP into `.agent/figma-shopify-composer/visual-check/<composition-name>/assets/images/` and `assets/svg/`.

**Done when:** every planned edit is in place as approved and nothing else changed — no new theme files, no new settings, no edited section/block/snippet/CSS/JS file.

## Phase 4 — Verify

**Static:** the target template (and `config/settings_data.json`, if edited) still parses as valid JSON; `shopify theme check` on changed files if available; fix errors.

**Visual** — the gate is numeric; never assumed, never skipped silently. At verification start, write `images/figma-desktop.png` / `images/figma-mobile.png` into the visual-check folder.

- **Render:** `shopify theme dev` when available (Browser pane manages it via `.claude/launch.json` in the desktop app); otherwise the preview/live store URL in the browser. There is no static fallback — composed existing sections require the full theme runtime. If neither path is possible, stop and report exactly what's missing.
- **Capture:** Browser pane screenshots if the capture-exactness check passed; otherwise connected browser MCP or installed Chrome; otherwise `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the cleanup ledger). The pane remains the inspection/diagnosis surface regardless.
- **Capture hygiene, before every capture:** exact Figma frame widths at the Figma screenshot's scale — identical pixel dimensions (diff tools require same-size inputs); clip to the composed region (the added section instance(s) or host section), not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle; apply the approved mask list so the diff measures only what is supposed to match.

**Loop, per breakpoint** — with delegation, steps 1–3 run as ONE visual-verifier call per iteration; the main agent reads `verify-report-<n>.md`, performs step 4, and launches the next round. Without delegation, the loop runs in main as written.

1. **Computed styles first**: getComputedStyle on the key elements vs the Figma values (font-family/size/weight, line-height, letter-spacing, color, background, padding, margin, gap, border, border-radius). A mismatch is fixed by ADJUSTING SETTINGS VALUES in the template JSON per the capability map — never by editing section/block code. If no setting can move the value, it's an undeclared gap: surface it, don't hack it.
2. **Pixel-diff gate**: `npx pixelmatch` or `npx odiff-bin` vs the Figma screenshot with the approved masks applied; record the diff ratio and save the diff image — every iteration.
3. **Live tracking**: immediately overwrite `images/result-*.png` and `images/diff-*.png` in the visual-check folder with this iteration's capture and diff.
4. **Diagnosis** (main agent): on failure, read the DIFF IMAGE / mismatch report to localize the mismatch and map it to a settings value (or an undeclared gap), fix, re-render, re-capture, repeat from step 1.

**Exit:** PASS when the pixel-accurate definition holds at both breakpoints — the gate passes on unmasked regions and every masked region is on the approved list. CAP after 8 iterations per breakpoint, or 2 consecutive iterations without diff-ratio improvement (the main agent tracks count and plateau across verifier reports) — then stop and report the final diff ratio, the diff image, the suspected remaining cause, and whether it is a settings issue or an undeclared capability gap. The threshold never drops and the mask list never grows silently. Note the report scope: fidelity is proven at the two captured widths only.

**Cleanup:** the ledger lists every temporary install (name, method, location). Once verification passes or caps: uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall; `.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/` in full — the knowledge docs for the next run, plus `.agent/figma-shopify-composer/visual-check/<composition-name>/` (references, live-updated result/diff images, exported assets) — untracked via `.git/info/exclude`. The user reviews the comparisons before committing, uploads the assets through the theme editor and assigns them to the image settings, and manages the folder themselves. Nothing lands in git except the planned template/config edits.

**Final output (no explanatory prose):** files changed (expected: the template JSON; possibly `settings_data.json`, the `.git/info/exclude` append, `.claude/launch.json`) with confirmation that NO new theme files were created and NO schemas were edited; final diff ratio per breakpoint with pass/cap status; the masked-region list with each mask's approval reason; the fidelity outcome vs the forecast (EXACT / APPROXIMATE / undeclared gaps discovered); the delegation map; the tooling ledger with removal confirmation (or "nothing installed"); knowledge-doc status — `.agent/THEME-CAPABILITIES.md` reused (fresh) / updated / created; the path `.agent/figma-shopify-composer/visual-check/<composition-name>/` with a one-line inventory (references, result/diff images, asset counts per format) and exclusion confirmation.

## Rules

- Read every file before editing; show a diff before overwriting anything existing.
- Ask instead of assuming.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- The template JSON (plus approved `settings_data.json` values) is the only build surface; `.git/info/exclude`, `.claude/launch.json`, and the `.agent/` tree are the only other writable paths, per the plan. Section/block/snippet/CSS/JS files stay read-only — no new theme files, no new settings, no schema edits.
- Knowledge docs first: read `.agent/THEME-CAPABILITIES.md` and freshness-check it before any theme scan; a scan that runs writes the doc back before the task continues. An explicit user refresh always wins.
- Never change a global setting VALUE silently — globals restyle the entire storefront; every global change is an explicit, individually-approved plan line.
- A per-instance custom CSS/Liquid setting is used only when the theme already has it AND the plan flagged it.
- Prefer global-connected settings over raw per-instance values when both can hit the Figma value.
- Verify template/schema JSON structure via the Shopify dev MCP instead of guessing.
- The Browser pane leads when available; fallbacks apply only when it's absent or fails the capture-exactness check.
- The pixel-diff gate is mandatory: passing is numeric, the threshold never drops, and the mask list never grows silently.
- Result/diff images are overwritten every iteration — the folder always shows the latest attempt.
- `.agent/` lives at the repo root, is always excluded via `.git/info/exclude`, and is never committed.
- Prefer `npx` over `npm i -g`; project-local or venv installs over global ones.
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
