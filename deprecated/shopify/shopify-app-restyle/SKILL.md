---
name: shopify-app-restyle
description: Restyle a third-party Shopify app's block/widget to match a Figma design — theme-only CSS overrides, every declaration !important and scoped under the app's container, proven by measured pixel diff. Use when the user wants to restyle, override, or customize an installed app's widget/app block to match Figma frames, or says "pixel-accurate"/"pixel-perfect" about an app widget. For theme-owned sections/blocks built from Figma, use figma-shopify-builder instead.
---

# Shopify App Restyle

Restyle a third-party app's storefront widget to its Figma frames without touching a single app file: everything ships as theme-owned overrides — every declaration `!important`, every selector **scoped** under the app's container so nothing **leaks** into the page. Pixel-accuracy is **measured**, never eyeballed: the run ends at a numeric gate (PASS) or an honest CAP, and the machine is left as found except one deliberate leftover, the visual-check folder.

## Inputs — ask for whichever are missing before starting

1. Figma desktop link (with node-id) and 2. Figma mobile link (with node-id).
3. App name, exactly as installed (e.g. "Easify Options") — locates its app-block entry in the template and its container/classes/stylesheets fast during inspection.
4. Target template (e.g. `templates/product.json`).
5. Placement: which section hosts the app block, and where it sits in that section's `block_order` (before/after which block, by customizer label or type) — used both to locate the widget and to verify/fix its position.
6. Page or product URL to inspect — optional; ask only if the widget's rendering is product-specific and the target is ambiguous.

## The gate — what pixel-accurate means

A measured result, all three:

1. Every checked computed style matches its Figma value.
2. Image diff ratio against the Figma screenshot ≤ 1%, anti-aliasing ignored.
3. Residual diff pixels are confirmed *from the diff image* to be text-rasterization noise (Figma and Chromium rasterize fonts differently; a literal 0% is unreachable). Layout, color, or spacing differences are never "noise".

Side-by-side eyeballing is for diagnosis only, never for passing.

## Browser tiers

**Primary: the Claude Code Desktop Browser pane** (session in the desktop app with Browser enabled) — drive it directly: screenshots, DOM/computed-style inspection, clicking, form filling. Local dev servers started via `.claude/launch.json` need no site approval; preview/live store URLs are external sites and trigger a one-time permission card (Allow once / Always allow); enable "Persist sessions" when the storefront is password-protected so the cookie survives restarts.

**Capture-exactness check:** the measured diff needs captures at the exact Figma frame widths and scale, identical pixel dimensions, clipped to the widget container. Confirm the pane's screenshots can honor that; if not, the pane still does inspection/interaction/diagnosis and the MEASURED captures fall to the first fallback that can: connected browser MCP (Chrome DevTools MCP / Playwright MCP) → installed Chrome → temporary Playwright via npx.

## Visual-check folder

`visual-check/<widget-name>/` at the ROOT of the theme repo, `<widget-name>` kebab-cased from the app/widget:

- `images/figma-desktop.png`, `images/figma-mobile.png` — references, written once at verification start.
- `images/result-*`, `images/diff-*` (per breakpoint, plus per verified state) — OVERWRITTEN after EVERY verification iteration, so the folder always shows the latest attempt across trial and error.
- `assets/images/` + `assets/svg/` — every asset in the Figma frames, exported via the Figma MCP: 4x-scale PNG for all assets into `assets/images/`, vectors additionally as SVG into `assets/svg/`, filenames kebab-cased from Figma layer names — upload-ready for the theme editor / app admin.

Not theme code: it must be gitignored (confirm the entry exists; plan the edit if missing — the Shopify CLI ignores non-theme root directories, so it is never pushed). Retained at the end; the user reviews it, uploads assets, and manages or deletes it themselves.

## Phase 1 — Research (read-only, no writes)

- **Figma**: pull design context + screenshot for both node-ids via the Figma MCP. Extract exact typography (incl. letter-spacing), colors, spacing, sizes, radii, frame widths, desktop/mobile differences, and every widget state visible in the frames (selected option, open dropdown, error…). These values are both the override targets AND the expected values for the computed-style assertions. Note each screenshot's scale (1x/2x) and pixel dimensions — captures must match them exactly for the diff. Inventory every exportable asset (name, raster/vector).
- **Tooling** (non-mutating checks only): Browser pane availability + the capture-exactness check (per Browser tiers). Render: Shopify CLI + `shopify.theme.toml` → `shopify theme dev` (in the desktop app, define it in `.claude/launch.json` so the pane manages the server); otherwise a preview/live store URL. There is NO static-render fallback — app-block markup only exists on a real store render; a local Liquid engine cannot produce it. Diff tool: Node/npx for `npx pixelmatch` / `npx odiff-bin`. Check `.gitignore` for a `visual-check/` entry.
- **Live widget** (pane when available, otherwise the fallback browser; locate it by app name): extract the full outerHTML of the widget container, all matched CSS rules with their stylesheet origins, and inline styles. Flag JS-injected inline `!important` styles — a theme stylesheet cannot beat those; they go on the not-CSS-fixable list. Identify stable selectors: the app's container class/ID, its classes and data-attributes — generated IDs and `nth-child` chains break when the app updates or the merchant edits options. Baseline screenshots at the Figma frame widths; save all snapshots to a temp directory outside the theme repo.
- **Wrong-state widget**: whenever the dev preview disagrees with the live site (e.g. sold out on `shopify theme dev`, in stock on the published theme — which changes how the widget renders), stop inspecting and run [environment-mismatch.md](environment-mismatch.md), stopping at the first step that fixes it. Nothing inspected or captured from a wrong-state widget counts.
- **Theme**: in the target template, locate the app block entry and the placement anchor in `block_order` (ask if ambiguous; stop and ask if the app block is absent). Learn how the theme loads custom CSS and mirror those conventions. Map Figma values to global typography/color variables only where they genuinely match; otherwise exact Figma values.
- **Difference list**: element by element, per state → (a) CSS-fixable and (b) NOT fixable by CSS — markup/structure differences, text/labels configured in the app admin, app-served images/icons, JS-set inline `!important`. Where a (b)-item is an app-served image/icon, note its Figma export lands in the visual-check `assets/` folders for app-admin upload.

Done when: every Figma value is written down against its scoped selector or its (b)-item, and the browser/render/diff tiers are decided.

## Phase 2 — Plan (write it out, then proceed — no approval pause)

An audit trail in the transcript, not a checkpoint:

- Override stylesheet filename (e.g. `assets/<app-handle>-overrides.css`) + load point per theme conventions — app CSS can load async, so `!important` is relied on rather than load order.
- The override table: element → scoped selector → property: current value → target value (exact Figma value or mapped theme variable) → media query if breakpoint-specific.
- The not-CSS-fixable list, each item with its remedy (app admin setting / accept as-is / upload the exported asset). Reported, not gated: fix everything CSS can fix and carry this list to the final output. Never DOM hacks.
- The `block_order` diff to reach the input-5 placement — or confirmation it's already right.
- Git hygiene: confirmation `visual-check/` is gitignored, or the `.gitignore` diff adding it.
- The asset-export list: every inventoried asset → 4x PNG into `visual-check/<widget-name>/assets/images/` (vectors additionally as SVG into `assets/svg/`), kebab-case names.
- Verification approach: browser tier with the capture-exactness result (pane or which fallback takes the measured captures), render path, whether `.claude/launch.json` is created/updated (a planned file if so), capture widths and scale, widget states to verify, key elements for computed-style assertions, diff tool + pass threshold (default ≤ 1%, AA ignored), iteration cap (default 8 per breakpoint, plateau exit after 2 without improvement), and the exact temporary installs with method (npx / project-local / venv) — listed installs proceed without approval; the cleanup ledger guarantees removal.

The only reasons to stop: a missing input, genuine ambiguity, or the live publish swap (protocol step 8).

## Phase 3 — Implement

- The override stylesheet per plan: every declaration carries `!important`; every selector scoped under the app's container so nothing leaks into the rest of the page; mapped theme variables where planned, exact Figma values otherwise; media queries per the planned breakpoint strategy.
- The stylesheet include at the planned load point; the `block_order` edit if planned; the `.gitignore` edit if planned. Diffs inline when editing existing files (audit trail, not a checkpoint).
- Export the Figma assets per plan into `assets/images/` + `assets/svg/` via the Figma MCP.
- Touch only planned files. App-served files and assets are NEVER modified.
- Verify Liquid/schema syntax via the Shopify dev MCP instead of guessing.

## Phase 4 — Verify

Static first: the template still parses as valid JSON (if edited); `shopify theme check` on changed files if available; fix errors.

Then visual — the gate is numeric, never assumed, never skipped silently:

- At start, write `images/figma-desktop.png` / `images/figma-mobile.png` into the visual-check folder.
- **Render**: `shopify theme dev` when available (pane manages it via `.claude/launch.json`); otherwise the preview/live store URL. Neither possible → stop and report exactly what's missing. A state mismatch reappearing here → [environment-mismatch.md](environment-mismatch.md) before continuing.
- **Capture**: pane screenshots if the capture-exactness check passed; otherwise connected browser MCP or installed Chrome; otherwise `npx playwright screenshot` (with `npx playwright install chromium` if no system browser — the download goes on the ledger). The pane stays the interaction/inspection surface regardless.
- **Hygiene before every capture**: exact Figma frame widths at the Figma screenshot's scale (identical pixel dimensions — diff tools require same-size inputs); clip to the widget container, not the full page; animations/transitions disabled; wait for `document.fonts.ready` + network idle; reproduce each Figma widget state by interacting in the browser before capturing it.
- **Loop, per breakpoint and state, in this order**:
  1. Computed styles first: getComputedStyle on the key elements vs the Figma values (font-family/size/weight, line-height, letter-spacing, color, background, padding, margin, gap, border-radius). Fix every mismatch before looking at pixels.
  2. Pixel-diff gate: `npx pixelmatch` / `npx odiff-bin` vs the Figma screenshot; record the ratio and save the diff image every iteration.
  3. Live tracking, every iteration, no exceptions: immediately overwrite `images/result-<breakpoint>[-<state>].png` and `images/diff-<breakpoint>[-<state>].png`.
  4. Diagnose from the DIFF IMAGE — it localizes the mismatch; map it to a cause, fix, hard-refresh, re-capture, back to 1.
  5. Leak check: surrounding page elements unaffected by the overrides.
- **Exit**: PASS when the gate holds at both breakpoints and all verified states. CAP after 8 iterations per breakpoint or 2 consecutive without diff-ratio improvement → report the final ratio, diff image, and suspected remaining cause; never thrash, never silently lower the threshold. Scope note: fidelity is proven at the two captured widths only.

**Cleanup**: ledger every temporary install (name, method, location; prefer npx over `npm i -g`, project-local/venv over global). On PASS or CAP: uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, delete the temp directory. The pane is a built-in — nothing to remove; `.claude/launch.json`, if created, is project config and stays. RETAIN `visual-check/<widget-name>/` in full, untracked via `.gitignore`. Nothing from the task gets committed: temporary tooling removed, machine left as found — the visual-check folder is the one deliberate leftover.

**Final output** (no explanatory prose): files created/changed · final diff ratio per breakpoint/state with PASS/CAP · the not-CSS-fixable list · the tooling ledger with removal confirmation (or "nothing installed") · `visual-check/<widget-name>/` path + one-line inventory (references, result/diff images, asset counts per format) + gitignore confirmation · which protocol step resolved any environment mismatch (for step 8, confirmation the original theme is live again).

## Rules

- Read every file before editing it.
- Never pause for approval once inputs are complete — the only stops: a missing input, genuine ambiguity, or the live publish swap (which never runs without the user's explicit go-ahead).

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
