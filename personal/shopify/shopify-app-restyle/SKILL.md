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
5. Asset inventory: every exportable asset (layer name, raster or vector).

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
Knowledge docs: .agent/shopify-app-restyle/app-widget-{app-handle}.md and
.agent/THEME-CAPABILITIES.md {— current contents attached | absent}. Verify
freshness in the live DOM before trusting: compare the live container
outerHTML against the doc's snapshot — equal → reuse its selectors/rules and
skip re-deriving 1–3; different or absent → do 1–3 in full and rewrite the
doc. THEME-CAPABILITIES, when attached, already answers 6–7 (§CSS load,
§Globals) — read it there; absent → derive 6–7 per-run.

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
   defined go in the doc; resolve their CURRENT values live and report them
   per-run; the main agent decides any mapping to Figma values.

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
images/figma-{breakpoint}.png
(per-state references where extracted: figma-{breakpoint}-{state}.png)
Expected values: {temp-dir}/figma-spec.md
Key elements to assert: {list from the plan}
Diff tool: {npx pixelmatch … | npx odiff-bin …} (anti-aliasing ignored)

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
4. Overwrite .agent/shopify-app-restyle/visual-check/{widget-name}/images/
   result-{breakpoint}[-{state}].png and diff-{breakpoint}[-{state}].png with
   THIS iteration's capture and diff.
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
- **`.agent/THEME-CAPABILITIES.md`** — read-only here; its shape is fixed, so it reads the same no matter which skill produced it. This skill reads §Globals (variable names and wiring — current values resolve live) and §CSS load (how the theme loads custom CSS); absent → the widget-inspector derives those two per-run into its report.

Every knowledge doc opens with this header (an app-widget doc's `scanned:` records the inspected URL + container selector):

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

**Read before inspection (main agent, Phase 1):** read both docs when they exist and pass their contents to the widget-inspector, which verifies freshness in the live DOM before trusting them and re-derives only what is missing or stale. An explicit user refresh always wins: full re-inspection, docs rewritten.

**Root pointer:** the repo's root `AGENTS.md`/`CLAUDE.md` names this convention so future sessions find the docs before rescanning. Missing → append it (or create a minimal `CLAUDE.md` holding just this block, excluded like everything else) — an audit-trail edit like any other:

```
## 📚 Knowledge docs (check before any theme scan)
Skill outputs + knowledge docs live under `.agent/` — shared docs at its root,
per-skill outputs in `.agent/<skill-name>/`. Read `.agent/THEME-CAPABILITIES.md`
before any theme scan and search `.agent/COMPONENTS.md` before writing new
code; freshness checks + refresh instructions in their headers.
```

## The visual-check folder

`.agent/shopify-app-restyle/visual-check/<widget-name>/` in the theme repo, kebab-cased from the app/widget name (e.g. "Product Options Pro" → `.agent/shopify-app-restyle/visual-check/product-options-pro/`):

- `images/figma-desktop.png`, `images/figma-mobile.png` — references, written once at verification start.
- `images/result-*.png`, `images/diff-*.png` — per breakpoint, plus per verified state — overwritten after EVERY verification iteration, so the folder always shows the latest attempt and progress stays trackable across trial and error.
- `assets/images/` + `assets/svg/` — every asset in the Figma frames exported via the Figma MCP: 4x-scale PNG for all assets into `assets/images/`, vectors additionally as SVG into `assets/svg/`, filenames kebab-cased from Figma layer names. Upload-ready for the Shopify theme editor / app admin.

The folder is not theme code: `.agent/` stays out of git via a `.git/info/exclude` line (confirm the `.agent/` line exists; append it as a planned edit if not — a local, never-committed file, and the Shopify CLI ignores non-theme root directories, so it is never pushed). It is retained at the end: the user reviews it, uploads assets, and manages or deletes it themselves.

## Phase 1 — Research (read-only on the theme)

Run the two delegations in parallel, plus tooling detection. No theme file is created or modified; the one canonical write is the app-widget doc (§Knowledge docs).

- **Figma extraction** → figma-extractor: both frames via the Figma MCP; exact-values table (the override targets AND the expected values for verification's computed-style assertions); desktop/mobile differences; every visible widget state; screenshot scale + pixel dimensions; asset inventory. Report: `figma-spec.md`.
- **Widget inspection + theme reads** → widget-inspector (in main if browser tools don't reach subagents), knowledge docs read first and passed in (§Knowledge docs): locate the widget by app name; verify doc freshness against the live container outerHTML; container outerHTML; matched rules with origins; JS-injected inline `!important` styles flagged; stable selectors; baseline screenshots at the Figma frame widths (read the widths via a cheap Figma `get_metadata` call at dispatch); per-run, the app-block entry + placement anchor in the target template; the theme's custom-CSS conventions and global typography/color variables (from `.agent/THEME-CAPABILITIES.md` when present, derived per-run otherwise). Writes/updates the app-widget doc; per-run report: `theme-widget-report.md`.
- **Tooling detection** (main agent, non-mutating checks only): Browser pane availability first, then fallbacks per Browser tiers; run the capture-exactness check; the Agent tool and which tools reach subagents (fix the delegation map). Render path: Shopify CLI + `shopify.theme.toml` → `shopify theme dev` (desktop app: defined in `.claude/launch.json` so the pane manages the server); otherwise a preview/live store URL. A real store render is required — app-block markup only exists there, so a local Liquid engine cannot produce it and there is NO static fallback. Diff tool: Node/npx for `npx pixelmatch` / `npx odiff-bin`. Check `.git/info/exclude` for a `.agent/` line.
- **Wrong-state check**: the dev preview must agree with the live site on everything that changes how the widget renders — availability (in stock vs sold out), widget presence, options shown. On any disagreement, pause measurement and work [environment-mismatch.md](environment-mismatch.md) to the first step that fixes it; a wrong-state widget is never inspected or verified against.
- **Difference list** (main agent, from `figma-spec.md`, the knowledge docs, and `theme-widget-report.md`), element by element and per state, split into (a) CSS-fixable and (b) not fixable by CSS — markup/structure differences, text and labels configured in the app admin, app-served images/icons, JS-set inline `!important` styles. Where a not-CSS-fixable item is an app-served image/icon, note that its Figma export will be in the visual-check `assets/` folders for app-admin upload.

**Done when:** both reports exist and the app-widget doc is current (fresh header); every OPEN QUESTION has been put to the user and answered; the tooling record names browser tier, capture source (exactness result), render path, diff tool, delegation map, temp dir, and the exclude status; any dev/live disagreement is resolved (note the step); and the difference list places every Figma-vs-live difference in exactly one of the two lists.

## Phase 2 — Plan (write it out, then continue)

The plan is an audit trail in the transcript, not a checkpoint — write it in full, then proceed straight to Phase 3. It states:

- **Stylesheet**: filename (e.g. `assets/<app-handle>-overrides.css`) and load point per the theme's CSS conventions. App CSS can load async — `!important` carries the win, not load order.
- **Override table**: element → scoped selector → property: current value → target value (exact Figma value, or a theme variable where it genuinely matches) → media query if breakpoint-specific.
- **Not-CSS-fixable list**: each item with its remedy — app-admin setting, accept as-is, or upload the exported asset. Reported, not gated: everything CSS can fix gets fixed; the list rides through to the final output. Never attempt DOM hacks.
- **Placement**: the `block_order` diff moving the app block to the input-5 position, or confirmation it already sits there.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append adding it.
- **Asset-export list**: every inventoried asset → 4x PNG into `.agent/shopify-app-restyle/visual-check/<widget-name>/assets/images/`, vectors additionally as SVG into `assets/svg/`, kebab-case names from Figma layers.
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced so far.
- **Verification approach**: browser tier with the capture-exactness result (pane captures, or which fallback), render path, whether `.claude/launch.json` will be created/updated (a planned file if so), capture widths and scale, the widget states to verify, key elements for computed-style assertions, diff tool + pass threshold (default: ≤ 1%, anti-aliasing ignored), iteration cap (default: 8 per breakpoint, plateau exit after 2 iterations without improvement), and the exact temporary-install list with method (npx / project-local / venv) — listed installs proceed without approval; the cleanup ledger still guarantees their removal.

## Phase 3 — Implement (main agent only)

Touch only planned files; no delegated edits; app-served files and assets stay untouched.

- Create the override stylesheet per the plan: every declaration carries `!important`; every selector is scoped under the app's container so nothing leaks into the rest of the page; mapped theme variables where planned, exact Figma values otherwise; media queries per the planned breakpoint strategy.
- Add the stylesheet include at the planned load point. Apply the planned `block_order` edit; append the `.agent/` line to `.git/info/exclude` if planned. Read every file before editing; show the diff inline for every edited file — audit trail, not checkpoint.
- Export the Figma assets per the plan via the Figma MCP into `.agent/shopify-app-restyle/visual-check/<widget-name>/assets/images/` and `assets/svg/`.

**Done when:** every planned file exists as planned, every edit's diff is in the transcript, the assets are exported, and nothing outside the plan changed.

## Phase 4 — Verify

**Static:** an edited template still parses as valid JSON; `shopify theme check` on changed files if available; fix errors.

**Visual** — the gate is numeric; never assumed, never skipped silently. At verification start, write `images/figma-desktop.png` / `images/figma-mobile.png` into the visual-check folder.

- **Render:** `shopify theme dev` when available (Browser pane manages it via `.claude/launch.json` in the desktop app); otherwise the preview/live store URL. If neither is possible, stop and report exactly what's missing. If a dev/live disagreement reappears, work [environment-mismatch.md](environment-mismatch.md) before continuing — a wrong-state widget is never verified against.
- **Capture:** Browser pane screenshots if the capture-exactness check passed; otherwise connected browser MCP or installed Chrome; otherwise `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the cleanup ledger). The pane remains the interaction/inspection surface regardless.
- **Capture hygiene, before every capture:** exact Figma frame widths at the Figma screenshot's scale — identical pixel dimensions (diff tools require same-size inputs); clip to the widget container, not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle; reproduce each Figma widget state by interacting in the browser before capturing it.

**Loop, per breakpoint and state** — with delegation, steps 1–3 and 5 run as ONE visual-verifier call per iteration; the main agent reads `verify-report-<n>.md`, performs step 4, and launches the next round. Without delegation, the loop runs in main as written.

1. **Computed styles first**: getComputedStyle on the key elements vs the Figma values (font-family/size/weight, line-height, letter-spacing, color, background, padding, margin, gap, border-radius). Fix every mismatch before looking at pixels.
2. **Pixel-diff gate**: `npx pixelmatch` or `npx odiff-bin` vs the Figma screenshot; record the diff ratio and save the diff image — every iteration.
3. **Live tracking**: immediately overwrite `images/result-<breakpoint>[-<state>].png` and `images/diff-<breakpoint>[-<state>].png` in the visual-check folder with this iteration's capture and diff.
4. **Diagnosis** (main agent): on failure, read the DIFF IMAGE / mismatch report to localize the mismatch, map it to a cause, fix, hard-refresh, re-capture, repeat from step 1.
5. **Leak check**: the overrides affect nothing outside the widget container.

**Exit:** PASS when the pixel-accurate definition holds at both breakpoints and all verified states. CAP after 8 iterations per breakpoint, or 2 consecutive iterations without diff-ratio improvement (the main agent tracks count and plateau across verifier reports) — then stop and report the final diff ratio, the diff image, and the suspected remaining cause. The threshold never drops silently. Note the report scope: fidelity is proven at the two captured widths only.

**Cleanup:** the ledger lists every temporary install (name, method, location). Once verification passes or caps: uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall; `.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/` in full — the knowledge docs for the next run, plus `.agent/shopify-app-restyle/visual-check/<widget-name>/` (references, live-updated result/diff images, exported assets) — untracked via `.git/info/exclude`. The user reviews it, uploads assets via the theme editor / app admin, and manages the folder themselves. Nothing from the task gets committed.

**Final output (no explanatory prose):** files created/changed; final diff ratio per breakpoint/state with pass/cap status; the not-CSS-fixable list (if any); the delegation map; the tooling ledger with removal confirmation (or "nothing installed"); knowledge-doc status — `app-widget-<app-handle>.md` reused (fresh) / updated / created; `THEME-CAPABILITIES.md` read (fresh) / absent (globals + CSS-load derived per-run); the path `.agent/shopify-app-restyle/visual-check/<widget-name>/` with a one-line inventory (references, result/diff images, asset counts per format) and exclusion confirmation; which environment-mismatch step resolved any dev/live disagreement — and after step 8, confirmation the original theme is live again.

## Rules

- Read every file before editing; include the diff inline when editing an existing file.
- Gate-free once inputs are complete: the only stops are a missing input, genuine ambiguity, or the live publish swap — which never runs without the user's explicit go-ahead.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- The Browser pane leads when available; fallbacks apply only when it's absent or fails the capture-exactness check.
- The pixel-diff gate is mandatory: passing is numeric, eyeballing only diagnoses, and the threshold never drops silently.
- Result/diff images are overwritten every iteration — the folder always shows the latest attempt.
- `.agent/` lives at the repo root, is always excluded via `.git/info/exclude`, and is never committed.
- Knowledge docs first: read `.agent/shopify-app-restyle/app-widget-<app-handle>.md` and `.agent/THEME-CAPABILITIES.md`, freshness-checked, before any widget inspection or theme scan; an inspection that runs writes the app-widget doc back before the task continues. An explicit user refresh always wins.
- Every override declaration carries `!important` and sits scoped under the app's container; selectors target the app's stable classes/data-attributes — never generated IDs or `nth-child` chains.
- Overrides only: app-served files and assets are never modified, and DOM hacks are never attempted — not-CSS-fixable items get reported with a remedy instead.
- Verify Liquid/schema syntax via the Shopify dev MCP instead of guessing.
- Prefer `npx` over `npm i -g`; project-local or venv installs over global ones.
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
