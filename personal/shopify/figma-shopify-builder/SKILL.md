---
name: figma-shopify-builder
description: Build pixel-accurate Shopify theme sections or blocks from Figma designs. Use when the user shares Figma links/node-ids to implement in a theme, wants a section or block added to a JSON template or editable in the theme editor, or says "pixel-accurate"/"pixel-perfect" about a theme build.
---

# Figma → Shopify Builder

Pixel-accuracy is **proven** by comparing a real render against the Figma frames — never assumed from matching values. Every phase below feeds that proof.

## Inputs — collect before starting

Ask for whichever are missing (one AskUserQuestion round, before any work):

1. Figma desktop link (with node-id)
2. Figma mobile link (with node-id)
3. Build type: **section** or **block**. If block: detect the theme's architecture — theme blocks (`blocks/` dir) vs a block defined inside a host section's schema — and ask for the host section if scoped.
4. Target template (e.g. `templates/index.json`)
5. Placement: before/after which existing section (customizer label or type). For a block: which section instance and its position in `block_order`.
6. Data source: **theme settings** (everything editable in the theme editor, defaults = Figma copy) or **metafields** (namespace.key, owner type, how the owner resolves in this template — ask if unclear; connect via dynamic sources where supported).

## Phase 1 — Research (read-only, no writes)

- Pull both frames via the Figma MCP: `get_design_context` + `get_screenshot` per node-id, `get_variable_defs` for the token names, `get_metadata` when you need exact geometry. The design context is React/Tailwind reference code — adapt it, never transplant it. Screenshot metadata gives the true frame widths: they become the capture widths in Phase 4.
- Extract exact typography, colors, spacing, gaps, radii, image dimensions, and every desktop/mobile layout difference. Where the two frames **disagree** (copy, colors), surface it and get one ruling to apply throughout — content divergence is usually design drift, style divergence is usually responsive intent.
- Verify every Figma font family exists in Shopify's font library (check the shopify.dev handles list). A missing family means a sibling substitute or a picker — a flagged decision, never a silent swap.
- Check for global typography/color settings: `config/settings_schema.json` plus wherever the theme emits CSS variables (`layout/theme.liquid`, a css-variables snippet, base CSS). Map each Figma value to a global where one exists; otherwise it will be applied directly. List every unmapped value — never silently decide.
- Read 2–3 structurally similar sections/blocks and mirror the theme's conventions: schema style, CSS scoping (`#{{ section.id }}` + `{% style %}`), class naming, breakpoints, `shopify:section:load` re-init.
- Read the target template; locate the placement anchor in `order` (or the host section's `block_order`). Ask if ambiguous.
- Detect verification tooling with non-mutating checks only: Shopify CLI + `shopify.theme.toml`, connected browser MCP (Chrome DevTools / Playwright MCP), installed Chrome, Node/npx, Python. Record which render + capture tier applies and every temporary install it would need.

Done when: every Figma value is written down with its source (global var | frame | downloaded asset), the unmapped list exists, the placement anchor is unambiguous, and the verification tier + install list is recorded.

## Phase 2 — Plan (a record, not a gate)

Post the plan, then continue straight into Phase 3 **in the same message** — invoking this skill is the approval, listed temporary installs included. Never end the turn asking "approve?". Questions happen once, up front, only for missing inputs or a fork neither the design nor the theme can answer.

The plan states:

- Filename + display name.
- Schema outline: all text/links/images editable, defaults matching the Figma copy; repeated items become blocks; images via `image_picker` (Figma images are sizing reference only — pickers can't hold defaults, so bundled asset fallbacks keep the build pixel-accurate out of the box).
- Typography/color mapping table (Figma value → global var or exact value), unmapped values flagged.
- Responsive strategy: which breakpoint switches mobile → desktop.
- Figma assets to download into `assets/`.
- The exact template JSON diff: new key in `sections` + `order` position, or block entry + `block_order` position.
- Verification approach: render + capture tier, capture widths, and the exact temporary-install list (npx / project-local / venv) — each entry removed in cleanup.

## Phase 3 — Implement

Follow the plan; touch only planned files; show the diff when editing an existing file. Rules from real builds:

- **One content table** drives both the schema preset and the template JSON blocks — JSON templates do **not** apply presets, so the template must carry the full block payload or the section renders empty.
- Template JSON opens with a `/* comment */` header: strip it to parse, preserve it on write.
- **Size caps**: section schema ≤ 64KB, template JSON ≤ 256KB. Re-check after inlining SVGs; minify inter-tag whitespace before sacrificing content.
- **Icon/graphic slots are dual-mode**: an `image_picker` (wins when set) paired with an `html` setting carrying the **exact Figma SVG** as its value — schema default for singleton slots; per-instance values in preset + template for repeated blocks (a block *type* holds only one default). Raster artwork (masked textures) can't be SVG: bundle it in `assets/` as the final fallback.
- **Figma exports are contaminated**: node exports can embed ancestor backdrops (page, section, parent card — gradients, filters and all). Extract the node's own group from the SVG, or re-export isolated (`contentsOnly`) for raster. Read every downloaded asset before shipping it.
- When Figma's hand-built columns drift a few pixels against each other, a synchronized grid (shared rows) is the correct build — note the delta as a documented deviation for Phase 4.
- Verify Liquid/schema syntax via the Shopify dev MCP instead of guessing.

## Phase 4 — Verify (the proof)

Static first: template JSON parses (comment stripped); `shopify theme check` and any repo validators on changed files; fix errors.

Visual — required; never assumed or skipped silently:

**Render (first available):**
1. `shopify theme dev` when the CLI (npx works) + `shopify.theme.toml` exist. Gated storefronts need `--store-password` (ask once). A one-time browser login is the only legitimate pause. If an *unrelated* broken theme file blocks the upload, serve with `--ignore <file>` and file an issue — don't fix out-of-scope files.
2. Static approximation otherwise: temporary Liquid engine (`python-liquid` in a throwaway venv), schema defaults stubbed, theme CSS variables inlined, fonts loaded from the same upstream families (Shopify's library is largely Google fonts, so typography fidelity holds). Flag all results as an approximation. Blocks render inside their host section; metafield sources get real values on a dev store, Figma copy in a static stub.

**Capture (first available):** connected browser MCP or installed Chrome; else temporary Playwright via npx (`npx playwright install chromium` — the browser goes on the ledger). Theme-dev specifics that waste hours when unknown: wait on `load`, never `networkidle` (the hot-reload socket keeps the network busy); the section wrapper is `#shopify-section-template--…__<template-key>`; hide the theme's sticky header group before element screenshots or it composites over the capture.

**Compare loop:** capture desktop + mobile at the Figma frame widths; compare against the Phase 1 screenshots — typography, spacing, colors, alignment, sizing, layout order. `npx pixelmatch` quantifies when dimensions match (crop first). Measure discrepancies with pixel probes/region crops instead of guessing. Expect a rasterizer-class residue (word-wrap flips, antialiasing, gradient interpolation) — distinguish it from real defects. Fix → re-render → re-capture until no visible difference remains at either breakpoint beyond the plan's documented deviations. Temp output lives outside the theme repo.

If no render or capture path exists even with temporary installs, stop and report exactly what's missing.

### Cleanup — leave the machine as found, with one exception

Ledger every temporary install (name, method, location) as it happens. Once the proof passes: uninstall project-local packages, delete venvs, `npx playwright uninstall` downloaded browsers, clear the npx cache, and delete the static harness, temp renders, and intermediate captures. A login session the user completed themselves stays (it's theirs — note it).

**Retain** only the final comparison set: Figma references + final result captures (desktop + mobile, plus finals of any documented deviations), self-explanatory names (`figma-desktop.png` / `result-desktop.png`), in a clearly named folder **outside the theme repo** (e.g. sibling `../<theme>-visual-check/`) so it can never be committed. The user reviews it, then deletes it — it is the one deliberate leftover.

### Final output (no other prose)

- Files created/changed.
- The tooling ledger, each install with removal confirmation — or "nothing installed".
- Absolute paths of the retained comparison images.

## Rules

- Read every file before editing; show a diff before overwriting anything existing.
- Ask instead of assuming — once, up front.
- Prefer `npx` over `npm i -g`; project-local or venv installs over global ones.

## Usage example

```
Use the figma-shopify-builder skill.
- Desktop: <figma link with node-id>
- Mobile: <figma link with node-id>
- Type: section
- Template: templates/index.json
- Place: after "Autoplay Slider"
- Data source: theme settings
```
