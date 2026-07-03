---
name: figma-shopify-builder
description: Build pixel-accurate Shopify theme sections or blocks from Figma designs. Use when the user shares Figma links/node-ids to implement in a Shopify theme, asks for a section or block added to a JSON template, or says "pixel-accurate"/"pixel-perfect" about a theme build.
---

# Figma → Shopify Builder

Pixel-accuracy is proven by measurement, never assumed from source values. The enemy is the **invented value**: any CSS value not traceable to the design context, a downloaded asset, or container math. Every pitfall below started as one.

## Inputs — collect before starting

Ask for whichever are missing; do not start without 1–6:

1. Figma desktop link (with node-id) and 2. Figma mobile link (with node-id).
3. Build type: **section** or **block**. If block: check for a `blocks/` dir (theme blocks) vs section-scoped; ask for the host section if scoped.
4. Target template (e.g. `templates/index.json`).
5. Placement anchor: before/after which section (customizer label or type); for a block, which section instance and `block_order` position.
6. Data source: **theme settings** (schema settings/blocks, defaults = Figma copy) or **metafields** (namespace.key, owner type, how the owner resolves in this template; use dynamic sources where supported).
7. Destination URL for every link/button in the design (otherwise they ship as `#`).
8. When desktop and mobile frames disagree on copy or colors, which frame wins (default: desktop; confirm once, apply throughout).

## Phase 1 — Research (read-only)

- Pull design context **and** screenshot for both node-ids via the Figma MCP. Design context is a starting point, not ground truth — see the trust table in Known pitfalls.
- Record, per auto-layout container: gap, padding (all four sides), and child alignment (`items-end` etc.). These three are what translations silently drop.
- Download every line/divider/hairline/graphic **asset** referenced in the design context and read its actual fill/stroke/dimensions. Never style a 1px detail from how a screenshot looks.
- Read `config/settings_schema.json` and the theme's CSS-variable emitter (`snippets/css-variables.liquid`, `layout/theme.liquid`, or base CSS). Map each Figma font/color to a global variable where one exists; list unmapped values for the plan. Note any global CSS that could override section styles (e.g. absent `font-smoothing`, base element styles).
- Read 2–3 structurally similar sections/blocks; mirror schema style, CSS scoping (`#type-{{ section.id }}` + `{% style %}`), class naming, and breakpoint (`@media (width >= 64rem)` or whatever the theme uses).
- Read the target template; find the placement anchor in `order` (or `block_order`). Ask if ambiguous.

Done when: every Figma text/color/spacing value is written down with its source (global var | design context | asset file | container math), and no container is missing gap/padding/alignment notes.

## Phase 2 — Plan (write it, then build — never wait for sign-off)

- Filename + display name; schema outline (repeated items → blocks; images via `image_picker` — Figma image fills are sizing reference only, with bundled asset fallbacks so the build renders out of the box).
- Typography/color mapping table (Figma value → global var or exact value); flag unmapped values as section settings with Figma defaults.
- Breakpoint strategy; assets to download into `assets/`; the exact template JSON diff.
- The plan is a written record, not a checkpoint: post it and continue straight into Phase 3 **in the same message**. Never ask "approve?"/"should I proceed?", never end the turn awaiting sign-off ("Approve and I'll build it" is banned) — invoking this skill IS the approval, and this overrides any global "check in before major changes" rule.
- Questions are only for missing inputs (1–8) or a genuine fork neither the design nor the theme can answer (AskUserQuestion, before the plan) — ask, absorb answers, build.

## Phase 3 — Implement

Follow the plan; touch only planned files; show diffs inline when editing existing files (audit trail, not a checkpoint). Rules that came from real failures:

- **Wrapper gaps**: when regrouping auto-layout siblings into a wrapper div, re-apply the parent's gap inside the wrapper.
- **Per-container gaps**: use each container's own gap; never uniformize. Adjacent cards (gap 0) get separation via margins, not gap.
- **Subgrid**: a shared grid's `gap` is inherited as row-gap by subgrid children — set `gap: 0` on the shared grid and separate columns with margins. Container padding on a subgrid item is absorbed into its edge tracks (safe for card padding); cell-level padding cannot create space between the cell and the card edge.
- **Alignment semantics**: translate `items-end`/bottom-aligned columns explicitly (offset or row-span) — columns that skip a header are shorter, not stretched.
- **Wrap layouts**: item widths come from container math (`calc(50% - gap/2)`), not nominal Figma widths — Figma frames can carry nominal sizes that overflow their own container.
- **Column ratios**: mobile/desktop track widths come from the design's flex ratios (`flex-1` = equal split), never guessed percentages.
- **Text transforms** are per-node; never share a `text-transform` across sibling variants.
- **Dark sections**: set `-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;` on the root — macOS subpixel AA renders light-on-dark text visibly bolder than Figma.
- **Template JSON**: Shopify JSON templates open with a `/* comment */` header — strip it before parsing, preserve it on write. Blocks added via a JSON template do **not** inherit preset blocks; write the full block payload (generate schema-preset and template blocks from one content table so they cannot drift).
- Verify Liquid/schema syntax via the Shopify dev MCP instead of guessing.

## Phase 4 — Verify (red → green; this is where pixel-accuracy is proven)

Static checks first: template JSON parses (comment stripped); `shopify theme check` / repo schema validators if available.

Then the **measurement loop** — mandatory; something must actually render the build so current-vs-Figma comparison can happen:

1. Pick the renderer by what the repo offers: a `shopify.theme.toml` means the CLI is configured — run `shopify theme dev` and drive the live preview URL. Without it, build a static harness: extract the `{% style %}` CSS from the *shipped* liquid with settings substituted, expand the markup with default content, load real fonts. Regenerate the harness from the liquid after every fix so it measures the artifact, not a copy.
2. Drive the renderer with whatever browser is available — Playwright's bundled Chromium (installed per Tooling hygiene — scratchpad-contained, browsers included), headless system Chrome, or a connected browser MCP. Viewport = the Figma frame widths (e.g. 1440/375; Playwright's option is `viewport`, not `viewportSize`).
3. Assert the Figma numbers, minimum set: sibling gaps; column widths/tops/bottoms/inter-column gaps; cross-column row alignment; content→card-edge distances; computed typography (size, weight, line-height, letter-spacing, style, **text-transform**); border and divider computed colors; mobile visible-column count at scroll 0 and wrap behavior (items-per-row).
4. Screenshot desktop + mobile and eyeball against the Figma screenshots — the eyeball pass catches what numbers miss (letter case, wrapping, iconography).
5. Iterate until the loop is green **and** the eyeball pass shows no discrepancy.

If the user reports a discrepancy after shipping: re-pull the Figma node and re-download its assets before re-verifying your own values — a repeat report means the reference was wrong, not the check.

Final output: short list of files created/changed + one line confirming tooling cleanup ran (see Tooling hygiene). No explanatory prose.

## Tooling hygiene — zero footprint

Harness tooling (Playwright, Liquid engines, browsers, image tools) is scaffolding, never a deliverable. When the task ends, the machine must look untouched except for the theme files.

- Prefer installs that cannot leak: `npx <pkg>` for one-shot Node CLIs; `npm i` only inside the scratchpad (never `-g`). Python: venv inside the scratchpad (`python3 -m venv <scratchpad>/venv`) — never `pip install --user`/system pip, which persist outside it (`~/Library/Python/<ver>` on macOS, `~/.local` on Linux).
- Playwright drops browsers in `~/Library/Caches/ms-playwright` by default — `export PLAYWRIGHT_BROWSERS_PATH=<scratchpad>/pw-browsers` before `playwright install` so binaries land in the scratchpad too.
- Keep an install manifest as you go: every "Successfully installed …" line, **including auto-pulled dependencies** (e.g. python-liquid drags in dateutil/pytz/babel/markupsafe) — deps you didn't name still count as yours. Don't pipe installer output through `tail`/filters that hide it.
- On completion or abort, remove everything that escaped the scratchpad: `python -m playwright uninstall --all` (while the package still exists), then `pip uninstall -y <manifest>`, then prune their cached wheels (`pip cache remove`). Uninstall only manifest entries — never anything that predated the task.
- Scratchpad contents are session-isolated and need no cleanup.

## Known pitfalls (from the field — each was a real bug)

Trust table for Figma MCP design context:

| Trust as-is | Derive/cross-check | Silent — must fetch |
| --- | --- | --- |
| font family/size/weight, line-height, letter-spacing; colors; per-node dims | nested per-container gaps; child alignment (`items-end`); container padding; flex ratios → track widths; nominal widths vs container math | image-asset internals (stroke/fill of lines, dividers, graphics); rendering environment (font smoothing) |

| Symptom | Root cause | Prevention |
| --- | --- | --- |
| Heading flush against paragraph | Wrapper div dropped the auto-layout parent's gap | Wrapper-gaps rule (Implement); sibling-gap assertion (Verify) |
| Uniform gutters where Figma has adjacent cards | Nested gaps "simplified" to one value | Per-container gap notes (Research); no uniformizing (Implement) |
| Rows/cards taller than Figma | Grid gap inherited as subgrid row-gap | Subgrid rule (Implement) |
| First column wrongly equal-height | `items-end` bottom-alignment ignored | Alignment notes (Research) + explicit translation (Implement) |
| Missing space under last row | Container padding dropped; then mis-fixed on the cell | Container-padding transfer (Implement); edge-distance assertion (Verify) |
| Everything "looks bolder" than Figma | macOS subpixel AA on dark bg; values were already exact | Dark-section smoothing rule (Implement); check rendering before touching weights |
| Titles ALL-CAPS vs sentence case | Shared class over-generalized `text-transform` | Per-node transforms (Implement); transform assertion + eyeball (Verify) |
| Badges wrap 1-per-row vs 2×2 | Nominal 156px widths overflow their container | Container-math widths (Implement); wrap assertion (Verify) |
| Third column peeking on mobile | Guessed 45%/48% tracks; design said `flex-1` | Flex-ratio widths (Implement); visible-count assertion (Verify) |
| Gold divider vs near-invisible hairline; reported twice | Styled an image asset from its screenshot glow; then "verified" the wrong element | Download assets, read stroke (Research); re-pull Figma on repeat reports (Verify) |
| Shipped unverified; every visual bug reached the user | Static checks only — no measurement loop existed | Phase 4 loop is mandatory before done |
| Tooling choked on template JSON | Shopify's `/* comment */` header | Strip-and-preserve rule (Implement) |
| Build stalled at "Approve and I'll build it" | Plan treated as an approval gate | Phase 2: plan is a record — build in the same message |
| playwright + python-liquid (+4 silent deps) left in `~/Library/Python`, ~100MB browser cache behind | `pip install --user`; default browser path; no uninstall pass | Tooling hygiene: scratchpad-contained installs + manifest uninstall |
