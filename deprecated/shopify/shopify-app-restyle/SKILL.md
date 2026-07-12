---
name: shopify-app-restyle
description: Restyle a third-party Shopify app's block or widget to match a Figma design using theme-only CSS overrides — every declaration `!important`, scoped to the app's container, nothing app-served touched, proven pixel-accurate by side-by-side capture at desktop + mobile widths. Use when the user wants to restyle, override, or customize an installed app's app block / app widget / storefront UI to a Figma frame, or mentions pixel-accurate app-block CSS overrides.
---

# Shopify App Restyle

Make a third-party app's storefront widget match a Figma design without owning its
markup. You cannot edit the app's HTML or its files — you can only **outrun its CSS**
from the theme. An **override** is the unit of work: one CSS declaration that carries
`!important` and is scoped under the app's container. That pairing is non-negotiable —
app CSS loads async, so load order can't be trusted; `!important` + scope is what wins.

This workflow is **gate-free**: once inputs are complete, run all four phases without
pausing for approval. Stop only for (a) a missing input, (b) genuine ambiguity, or
(c) the live publish swap (`environment-mismatch.md` step 8). The plan and diffs you
emit are an audit trail, not checkpoints.

Tools: **Figma MCP** (read the design), **Shopify dev MCP** (verify Liquid/schema, not
guess), **browser MCP / Chrome DevTools MCP / Playwright MCP** (inspect + capture).

## Inputs — gather before starting; ask for any missing

1. **Figma desktop link** (with node-id) — required.
2. **Figma mobile link** (with node-id) — required.
3. **App name**, exactly as installed (e.g. "Easify Options") — required. Locates its
   app-block entry in the template and its container/classes fast.
4. **Target template** (e.g. `templates/product.json`) — required.
5. **Placement** — which section hosts the app block, and where it sits in that
   section's `block_order` (before/after which block, by customizer label or type) —
   required. Used to locate the widget and to verify/fix its position.
6. **Page/product URL to inspect** — optional; ask only if the widget's rendering is
   product-specific and the target is ambiguous.

## Phase 1 — Research (read-only, no writes)

- **Figma.** Pull both frames via the Figma MCP (design context + screenshot per
  node-id). Extract exact typography, colors, spacing, sizes, radii, and **frame widths
  (these are the capture widths in Phase 4)**; the desktop/mobile deltas; and every
  widget **state** the frames show (selected option, open dropdown, error, …).
- **Tooling.** Detect (non-mutating): Shopify CLI + `shopify.theme.toml` →
  `shopify theme dev`; else a preview/live store URL. **There is no static-render
  fallback** — app-block markup exists only on a real store render, so a local Liquid
  engine cannot produce it. Capture side: browser MCP → installed Chrome → temporary
  Playwright via npx.
- **Inspect the live widget** (locate it by the app name). Extract the container's full
  outerHTML, every matched CSS rule with its stylesheet origin, and inline styles. Any
  **JS-injected inline `!important`** goes on the **not-CSS-fixable list** — a theme
  stylesheet cannot beat it. Pick **stable hooks** to target: the app's container
  class/ID, its classes and data-attributes — never generated IDs or `nth-child`
  chains, which break on app updates or option edits. Take baseline screenshots at the
  Figma frame widths; save all snapshots to this build's subfolder inside the
  repo-root `visual-check/` folder (gitignored — see **Retain**).
  - **Wrong state?** If the widget renders in a different state on dev vs live
    (e.g. sold out on one, in stock on the other) — STOP and follow
    `environment-mismatch.md`. A comparison against the wrong state is not evidence.
- **Read the theme.** In the target template, locate the app-block entry and the
  placement anchor in `block_order` (ask if ambiguous; **stop and ask if the app block
  is absent** from the template). Learn how the theme loads custom CSS — mirror that
  convention. Note global typography/color variables; map Figma values to them only
  where they **genuinely match**, else use exact Figma values.

**Done when:** a difference list exists — element by element, per state — split into
(a) CSS-fixable and (b) **not-CSS-fixable** (markup/structure, admin-configured text,
app-served images/icons, JS-set inline `!important`).

## Phase 2 — Plan (write it out, then proceed — gate-free)

Emit, in the transcript:

- **Override stylesheet** filename (e.g. `assets/<app-handle>-overrides.css`) and load
  point, per the theme's CSS convention.
- **Override table:** element → scoped selector → property: current value → target
  value (exact Figma value or mapped theme variable) → media query if breakpoint-only.
- **Not-CSS-fixable list**, each item with its remedy (app admin setting / accept
  as-is). Reported, never gated — never attempt DOM hacks — and carried to the final
  output.
- **`block_order` diff** to move the app block to the input-5 placement, or a note that
  it's already positioned correctly.
- **Verification approach:** render + capture tier, capture widths, states to verify,
  and every temporary install with its method (npx / project-local / venv).

## Phase 3 — Implement

- Create the override stylesheet from the table: every declaration an **override**
  (`!important`, scoped under the app container — see Rules); mapped theme variables
  where planned, exact Figma values otherwise; media queries per the plan.
- Add the include at the planned load point. Apply the `block_order` edit if planned.
  Show diffs inline when editing existing files.
- Touch only planned files. **Never** modify app-served files or assets.

**Done when:** stylesheet created, include added, placement applied, and no
unplanned file touched.

## Phase 4 — Verify — pixel-accuracy is proven, never assumed

- **Static.** Template still parses as valid JSON (if edited); run `shopify theme check`
  on changed files if available; fix errors.
- **Render.** `shopify theme dev` if available, else the preview/live URL. If neither is
  possible, stop and report exactly what's missing — never skip visual verification
  silently. If a **wrong state** reappears here, run `environment-mismatch.md` before
  comparing.
- **Capture.** Browser MCP / Chrome DevTools MCP / installed Chrome first; else
  temporary Playwright via npx (`npx playwright screenshot`; `npx playwright install
  chromium` if no system browser — the download goes on the **cleanup ledger**).
- Capture desktop + mobile at the Figma frame widths. Drive the browser into **every
  state** the frames show before capturing it.
- Compare each capture side-by-side with its Figma frame: typography, spacing, colors,
  alignment, sizing, layout order. Optional image diff via npx (`pixelmatch`/`odiff`).
- Spot-check surrounding page elements — confirm no override **leaked** outside the
  widget.

**Done when:** at **both** breakpoints, across **every** state the frames show, no
visible difference remains and nothing leaked. Fix → hard-refresh → re-capture until
then; intermediate captures are disposable.

### Cleanup — leave the machine as found, with one exception

Ledger every temporary install (name, method, location). On pass: uninstall
project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers,
and delete temp renders, snapshots, and intermediate captures.

**Retain** only the final comparison set: Figma references + final result captures
(desktop + mobile, plus finals of any extra states), self-explanatory names
(`figma-desktop.png` / `result-desktop.png`), in this build's subfolder inside
the root `visual-check/` folder (e.g. `visual-check/<app-handle>/`). Add
`visual-check/` to the theme's `.gitignore` (one entry covers every build's
subfolder — create `.gitignore` if absent) so the set lives in the repo yet is
never committed.
The user reviews it, then deletes it — it is the one deliberate leftover.

### Final output (no other prose)

- Files created/changed.
- The not-CSS-fixable list (if any).
- The cleanup ledger, each install with removal confirmation — or "nothing installed".
- Absolute paths of the retained comparison images.
- Which `environment-mismatch.md` step resolved any state mismatch (and, if step 8 ran,
  confirmation the original theme is live again).

## Rules

- **Every override is `!important` and scoped** to the app's container — so nothing
  leaks out and the theme wins against async app CSS.
- **Stable hooks only** — the app's classes and data-attributes; never generated IDs or
  brittle `nth-child` chains.
- **Never touch app-served files or assets.** Read every theme file before editing;
  show diffs when editing existing files.
- **Gate-free.** No approval pauses once inputs are complete; stop only for a missing
  input, genuine ambiguity, or the live publish swap.
- **The live publish swap is last resort** and never runs without explicit user
  confirmation.
- Verify Liquid/schema via the **Shopify dev MCP**, don't guess.
- `npx` over `npm i -g`; project-local or venv over global.

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
