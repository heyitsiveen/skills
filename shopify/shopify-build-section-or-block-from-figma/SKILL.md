---
name: shopify-build-section-or-block-from-figma
description: Use when the user wants to BUILD a NEW Shopify theme SECTION (new .liquid file in `sections/`) OR a NEW BLOCK (new .liquid file in `blocks/`) from Figma designs, and wire it into the theme. For sections, wires into a JSON template's `order` array. For blocks, wires into a specific section's `blocks` / `block_order` (or just registers the block type for reuse). The skill scans the theme's existing conventions, fetches both desktop + mobile Figma designs via the Figma MCP, generates a new `.liquid` file that matches theme patterns, and inserts it at the requested position. Required inputs vary by type — for a section, four inputs (template, position, desktop URL, mobile URL); for a block, five inputs (type=block, parent section, position within that section, desktop URL, mobile URL) or four for register-only. Triggers on phrases like "build this Figma as a new section", "create a new Shopify block from Figma", "turn this Figma into a new .liquid block and add it to the Hero section", "build this Figma as a reusable block", or any request supplying the Figma URLs + a placement instruction that mentions a section or block. Prefer this over `shopify-add-section-or-preset-from-figma` when the Figma design cannot be composed from existing sections/blocks and a new `.liquid` file is needed.
user-invocable: true
---

# Shopify Build Section or Block From Figma

Build a new `.liquid` section or block from Figma designs and wire it into a Shopify theme. Unlike `shopify-add-section-or-preset-from-figma` (JSON composition from existing primitives), this skill creates a new `.liquid` file — either in `sections/` or `blocks/`.

## Decide first: section or block?

The two require different schemas, file locations, and placement mechanics. Ask if unclear:

- **Build a section** when the Figma design is a full-width page module (hero, product spotlight, testimonial carousel). Section files live in `sections/`. They are placed in a JSON template's `order` array.
- **Build a block** when the Figma design is a smaller reusable component (card, button variant, accordion item, custom layout primitive). Block files live in `blocks/`. They are placed inside a specific section's `blocks` + `block_order` — OR just registered as a theme block for future use.

A good rule of thumb: if the Figma design is meant to sit beside other sections on a page, it's a section. If it's meant to be nested inside or alongside other blocks within a section, it's a block.

## Required inputs

Ask for any missing ones via `AskUserQuestion` **BEFORE any code is generated**. Do NOT start writing the `.liquid` file until every input below is confirmed. Missing placement inputs are the #1 cause of "the block doesn't appear in the editor" bugs.

### For a section (4 inputs, always required)

1. **Template** — e.g., `index.json`, `product.json`, `collection.json`, or a section-group like `sections/footer-group.json` / `sections/header-group.json`.
2. **Position** — `After "<X>"`, `Before "<Y>"`, `After "<A>", before "<B>"`, or `Order #N`.
3. **Desktop Figma URL** — `figma.com/design/{fileKey}/...?node-id={a}-{b}`.
4. **Mobile Figma URL** — same format.

**Optional invocation key** — the user may specify `Data Source: Settings | Metafield | Mix` in their request to skip the data-source interview. Accepted values:
- `Settings` — every field lives in the section schema (editable per instance in theme editor).
- `Metafield` — every dynamic field pulls from product/collection/page metafields or metaobjects.
- `Mix` — headings, padding, colors from settings; content (body copy, card lists, swatches) from metafields/metaobjects.

If the key is missing, Step 3c MUST ask via `AskUserQuestion` before any code is generated.

### For a block (5 inputs, always required)

1. **Type** — `block` (explicitly state this to disambiguate from section workflow).

2. **Schema placement (multi-select checklist, REQUIRED)** — which parent schemas should list this block type in their `"blocks":` array? Deep-scan the codebase first (`grep -lE '"blocks":\\s*\\[' sections/*.liquid blocks/*.liquid`) to build the full list of discovered parents, then present them as a checklist so the user can tick one or more:

   ```
   [ ] sections/section.liquid
   [ ] sections/footer.liquid
   [ ] sections/header.liquid
   [ ] blocks/group.liquid
   [ ] blocks/accordion-item.liquid
   [ ] blocks/tabs.liquid
   [ ] ... (every discovered parent)
   [ ] ALL
   ```

   **Why mandatory**: a block that isn't listed in a parent's schema `"blocks":` array is invisible in that parent's "Add block" picker. Worse, if a template JSON instance references the block under an unregistered parent, Shopify's git integration silently rolls back the JSON reference. Never guess this — always ask.

3. **Template + position (ALWAYS required, even for blocks)** — which JSON file to wire a live instance into, AND the exact position. Applies to both sections and blocks. Typical targets:
   - `templates/<name>.json` — page-level template
   - `sections/footer-group.json`, `sections/header-group.json` — section-group templates (footer/header layouts composed of multiple sections)
   - `Register only` — create the block type for reuse; skip wiring a live instance (still complete step 2 so merchants can add it later)
   
   Position format: `After "<X>"`, `Before "<Y>"`, `Order #N`. For blocks, include the target section + block_order slot (e.g., `Inside section_abc123 in index.json, after block_xyz789`).

4. **Desktop Figma URL**.
5. **Mobile Figma URL**.

**Interview order**: ask schema placement + wire target FIRST (they drive everything else), then design-decision questions. Split across two `AskUserQuestion` calls if needed to stay under the 4-question limit.

## Fidelity Requirements

The output **MUST match the Figma design 100%** across both desktop and mobile. The following are non-negotiable — no exceptions, no "close enough", no defaulting:

- **Coverage** — every visible element in the Figma frame must appear in the rendered output, and every element in the rendered output must correspond to something in Figma. Spec-match alone is not enough; partial coverage is the most common failure mode (entire sub-headings, badges, and helper strips have been skipped in past sessions). See Step 2 for how to build the enumerated list, Step 8 for how to verify coverage visually.
- **Spacing** — margins, paddings, and gaps must be pixel-exact to Figma.
- **Sizes** — widths, heights, max-widths, and any fixed dimensions must match exactly.
- **Typography** — font family, weight, size, line-height, letter-spacing, and text color must all be pulled directly from Figma. No assumptions, no theme-default fallbacks unless Figma explicitly uses the theme's token.
- **Colors** — backgrounds, borders, text, icons, overlays, gradients, and shadows must match exactly.
- **Icons** — use the exact icons in the Figma design.
- **Layout & components** — structure must mirror Figma exactly.
- **Responsive** — desktop styles apply at the theme's correct breakpoint; mobile styles must match the mobile frame exactly. No breakpoint or value should be guessed.

### Hard rule: Figma MCP is the only source of truth

All specs (hex codes, font sizes, line-heights, gaps, paddings, breakpoint values, dimensions) **must** be extracted via the Figma MCP (`mcp__plugin_figma_figma__get_design_context` and `mcp__plugin_figma_figma__get_metadata`). Do not eyeball values from screenshots, infer them from theme defaults, or default to round-number placeholders.

### DO NOT — red flags

- **DO NOT** eyeball spacing, font size, or color from a Figma screenshot. Always pull via MCP.
- **DO NOT** default to "close enough" hex codes (e.g., `#000`, `#fff`, theme-token fallbacks) when Figma specifies a literal hex.
- **DO NOT** introduce a new responsive breakpoint to make a layout work — match the theme's existing breakpoint.
- **DO NOT** mark the task complete without re-checking every fidelity item against **both** the desktop and mobile Figma frames.
- **DO NOT** assume a value because it "looks reasonable" — if the MCP didn't return it, ask the user or re-call the MCP with a more specific node ID.
- **DO NOT** declare the build complete based solely on schema/JSON/Liquid validation or mental specs-match against MCP data. Visual side-by-side comparison (rendered screenshot vs Figma frame) is the authoritative check. In a recent session, an entire sub-heading and per-card badges were missed because verification was specs-only — fixing them required user-provided screenshots to surface the gaps.
- **DO NOT** add CSS properties Figma doesn't specify (negative spreads on shadows, transitions, hover transforms, easing curves, filter effects). If Figma's spec is `drop-shadow(0 20px 12.5px rgba(0,0,0,0.1))`, the equivalent box-shadow is `0 20px 12.5px 0 rgba(0,0,0,0.1)` — same values, no embellishments. "Improving" on Figma is a fidelity violation. In a recent session, a `-5px` negative spread was silently added to a popular-card shadow, shrinking it vs Figma's pure drop-shadow — caught only on user-provided screenshot comparison.
- **DO NOT** ship generic placeholder SVGs as schema defaults when Figma shows a specific icon style. If Figma shows a simple checkmark, ship a simple checkmark SVG — not a circle-check, not a stylized variant. For bespoke brand assets you can't recreate (custom logos, illustrative icons), check `shopify://shop_images/` for an existing asset (see Step 1 prior-art search) OR escalate to the user BEFORE declaring done. Generic placeholders look like bugs to merchants and break the 100%-Figma-fidelity rule. Rationalizing "the merchant will swap this" leaves a non-Figma-faithful section in the meantime.

## Workflow

Follow these steps in order. Don't skip orientation — theme conventions differ, and skipping it produces files that feel bolted-on.

### Step 1: Orient to the theme (read-only)

- **List directories**: `sections/`, `blocks/`, `snippets/`, `templates/`, `locales/`, `config/`.
- **Deep-scan every parent schema** (blocks only — skip for sections): `grep -lE '"blocks":\\s*\\[' sections/*.liquid blocks/*.liquid`. This list becomes the multi-select checklist in the placement interview. Save it — you'll reference it again in Step 5 when registering the block.
- **Read reference files** based on build type:
  - **Section**: 2 recent custom sections (e.g., `sections/testimonial-carousel.liquid`, `sections/about-us.liquid`).
  - **Block**: 2 recent custom blocks (e.g., `blocks/button.liquid`, `blocks/text.liquid`, `blocks/group.liquid`). Pay attention to the `{% doc %}` header and schema differences from sections.
- **Read `locales/en.default.schema.json`** top-level keys for `t:` translation keys you can reuse.
- **Read candidate snippets** to reuse: `snippets/product-card.liquid`, `snippets/responsive-image.liquid`, `snippets/button.liquid`, `snippets/icon.liquid`.
- **Read the target template JSON** or parent section file, depending on placement target.
- **Search for prior art across templates and sections (MANDATORY).** Before building, grep for any existing implementation of the Figma elements you're about to render. Existing renderings often reveal pre-uploaded assets (`shopify://shop_images/<filename>`), established link conventions (where "Learn More" / "Get Started" routes go), real product handles, and naming patterns:

  ```bash
  grep -rE "<keyword-from-figma>" templates/ sections/ blocks/ | head -20
  grep -nE "shopify://shop_images/[^\"']+" templates/*.json sections/*.liquid | head
  ```

  Concrete example: building the membership-pricing section in this codebase, a grep for "green-e" surfaced `shopify://shop_images/1_percent_green_e.png` (an existing Green-e logo asset) AND the convention that "Green-e Certified" text links to `https://www.green-e.org/`. Both were sitting in `ai_gen_block_33f0c1c` referenced from `templates/page.residential.json` — but the initial build missed them because only the target template was read, not siblings. Reusing pre-existing patterns avoids generic placeholders, leverages assets the merchant has already uploaded, and matches what the merchant already knows.

### Step 2: Fetch both Figma designs

Call `mcp__plugin_figma_figma__get_design_context` twice — once for desktop, once for mobile. Extract:

- Layout mechanism (nested flex vs CSS grid vs absolute positioning) — **match this exactly**.
- Outer alignment (`items-start` vs `stretch` vs `center`).
- Gap values, colors, typography, aspect ratios.
- Nested components — map each to an existing snippet or sub-block if possible.

Per the **Fidelity Requirements** section above, the MCP is the *only* source of spec values — no eyeballing from screenshots, no defaulting to round-number placeholders. Pull every spec listed in the fidelity checklist (spacing, sizes, typography, colors, icons, layout, responsive) directly from these two MCP calls.

**Then build an enumerated component list (MANDATORY before writing any Liquid).**

After fetching, walk the Figma metadata top-to-bottom and build a numbered list of EVERY visible element in the frame. Include:

- Headers and sub-headings (including small ones like "Step 2: ..." that look like section dividers)
- Trust pills, badges (e.g. "Green-e Certified", "Most Popular")
- Cards / blocks — name each one
- Bottom strips, helper text, link-buttons
- Decorative elements with content (logos, icons in line with text)

Format the list as one item per visible element with its Figma frame ID and a short description. Example:

```
1. [6065:1626] Section heading — "Want to make a bigger impact?"
2. [6065:1630] Top trust-pill row — 3 pills (Month-to-month / Cancel anytime / Independently verified)
3. [6129:369] Step sub-heading — "Step 2: Choose your energy type" + description
4. [6129:374] Card 1 (HydroWind) — icon + heading + tagline + price + bullets + best-for
5. [6129:588] Card 2 (SolarWind, "Most Popular") — same structure + Green-e badge
6. [6129:798] Card 3 (AllSolar) — same structure + Green-e badge
7. [6065:2253] Bottom strip — 2 trust pills + orange CTA button
8. [6065:2267] Helper strip — text + blue "Get My Energy Profile" button
```

This list is the source-of-truth for "what must be rendered." It anchors Step 4.7 (coverage check) and Step 7a (visual verification). Without it, partial coverage misses entire elements — the most common failure mode.

**Sparse-metadata caveat.** When the MCP responds with "the design was too large to fit into context," it returns a sparse tree of frame names + dimensions + text content. The sparse tree IS exhaustive for *what visible elements exist* — every frame is listed by name. Use it to build the enumerated list, even if you defer drilling into every sub-frame for full styles. Don't skip elements just because the response said "too large."

### Step 3: Interview the user — placement FIRST, then design

**Split into two `AskUserQuestion` calls to respect the 4-question limit.**

#### 3a. Placement interview (ALWAYS, before any code generation)

For **blocks**:

- **Schema placement (multi-select checklist)** — present the full list from Step 1's deep-scan (`grep -lE '"blocks":\\s*\\[' sections/*.liquid blocks/*.liquid`). Include an `ALL` option. User ticks one or more. Every ticked parent gets the new block type added to its `"blocks":` array in Step 5.
- **Wire target** — template or section-group JSON + exact position where to insert a live instance (or `Register only`).

For **sections**:

- **Template + position** — which JSON file + position in the `order` array. (`Required inputs` already requires this, but re-confirm if there's ambiguity.)

Do not skip or shortcut this. In a prior run, skipping the schema-placement question caused a block to be invisible in the `sections/footer.liquid` editor — the user had to flag it after deploy.

#### 3b. Design interview (max 4 questions in a single `AskUserQuestion` call)

- **File name** (kebab-case, matches filename and schema `"name"`).
- **Dynamic data sources** — product picker, collection picker, metaobject, link_list (for navigation), or hardcoded fields?
- **Color customization** — expose `color_mode` (inherit | custom) with Figma hex as defaults (recommended), or hardcode?
- **Typography** — use theme's font tokens or introduce a new family?
- **For blocks specifically**: should this block accept nested blocks (via `{% content_for 'blocks' %}` + `"blocks": [{ "type": "@theme" }]`)? What schema categories (for Shopify's block picker UI)?

Flag **deviations** when user preferences conflict with technical constraints. Classic example: a "button variant selector" for the nested Add-to-Cart button won't work because `snippets/add-to-cart.liquid` styles with CSS variables, not `button.liquid` variants — replace with color overrides and note the deviation.

#### 3c. Data Source interview (REQUIRED before any code generation)

**This step is mandatory.** Every significant field in a new section/block needs an explicit data source decision — otherwise you guess, and guessing generates rework.

If the user provided `Data Source: Settings | Metafield | Mix` in their invocation, honor that and move on. If NOT provided, ask via `AskUserQuestion`:

```
Question: "Where should each field in this section/block pull its content from?"

Options:
[ ] Settings schema — static, editable per instance in the theme editor.
    Best when content is the same across all products/pages, or merchant will
    configure once per section placement.

[ ] Metafield / Metaobject — dynamic, pulled from Shopify custom data.
    Best when content varies per product/collection/page, or the same content
    needs to appear on many product pages without duplication.

[ ] Mix — headings/padding/colors from settings, content from metafields.
    Typical for PDP sections where the layout is configurable but the actual
    product content (descriptions, specs, colors, features) lives per-product.
```

**If the user selects Metafield or Mix**, before writing ANY metafield-reading Liquid:

1. **Invoke `shopify-plugin:shopify-custom-data`** via the Skill tool. This is the Shopify-maintained plugin skill that surfaces current metafield/metaobject admin UX and the corresponding Liquid patterns. **Do not skip** — assumptions about metafield Liquid syntax go stale, and the plugin reflects current Shopify behavior.
2. **Invoke `shopify-plugin:shopify-liquid`** for Liquid-specific details (filters, drops, rendering).
3. **For broader docs questions**, invoke `shopify-plugin:shopify-dev`.
4. **Confirm output method per field type** using the "Metafield / Metaobject Liquid patterns" section below — especially rich_text, which must use `| metafield_tag`, NOT `.value`. Rendering `.value` for a rich_text field prints the raw JSON AST as a visible string — a previously shipped bug in this codebase.

### Step 4: Build the `.liquid` file — BRANCH BY TYPE

#### If section — create `sections/<kebab-name>.liquid`

Structural template:

```liquid
{%- comment -%}
  <Display Name>
  - <Structural summary matching Figma>
{%- endcomment -%}

{%- liquid
  assign section_id = section.id
-%}

{%- style -%}
  /* Dynamic CSS — scoped to #<section-slug>-{{ section_id }} for higher specificity
     than snippet-embedded #id rules. All setting-driven values live here. */
  #<section-slug>-{{ section_id }} { /* ... */ }

  /* Overrides targeting nested snippets — scoped to beat their #id selectors */
  #<section-slug>-{{ section_id }} .<descendant> { /* ... */ }

  @media (min-width: 64rem) {
    #<section-slug>-{{ section_id }} { /* Desktop overrides */ }
  }
{%- endstyle -%}

<section id="<section-slug>-{{ section_id }}" class="<section-slug>">
  <div class="<section-slug>__wrapper">
    <div {% if section.settings.width == 'default' %}class="shopify-page-width"{% endif %}>
      <!-- HTML mirroring Figma component tree 1:1 -->
    </div>
  </div>
</section>

{% stylesheet %}
  /* Static layout CSS — no Liquid interpolation */
{% endstylesheet %}

{% schema %}
{
  "name": "<Display Name>",
  "tag": "section",
  "settings": [ /* grouped by header — see conventions below */ ],
  "presets": [{ "name": "<Display Name>" }]
}
{% endschema %}
```

Schema must validate against `schemas/section.json`. Always include `width` (full | default) and `color_mode` (inherit | custom) settings — they're table stakes for merchant flexibility.

#### If block — create `blocks/<kebab-name>.liquid`

Structural template (note the required `{% doc %}` header and different schema shape):

```liquid
{% doc %}
  Renders a <Display Name> block.

  @param <if used statically, document any params from {% content_for 'block', ... %}>

  @example
  {% content_for 'block', type: '<kebab-name>', id: '<static-id>' %}
{% enddoc %}

{%- liquid
  assign block_id = block.id
-%}

{%- style -%}
  /* Dynamic CSS scoped to #<block-slug>-{{ block_id }}.
     Blocks get a unique id per instance — scope to that id to avoid bleed across
     multiple instances of the same block type on one page. */
  #<block-slug>-{{ block_id }} { /* ... */ }

  @media (min-width: 64rem) {
    #<block-slug>-{{ block_id }} { /* Desktop overrides */ }
  }
{%- endstyle -%}

<div
  id="<block-slug>-{{ block_id }}"
  class="<block-slug>"
  {{ block.shopify_attributes }}
>
  <!-- HTML mirroring Figma component tree 1:1 -->
  <!-- If this block accepts nested blocks, include: -->
  {% comment %}{% content_for 'blocks' %}{% endcomment %}
</div>

{% stylesheet %}
  /* Static layout CSS */
{% endstylesheet %}

{% schema %}
{
  "name": "<Display Name>",
  "settings": [ /* grouped by header */ ],
  "blocks": [
    { "type": "@theme" }
  ],
  "presets": [
    { "name": "<Display Name>" }
  ]
}
{% endschema %}
```

Schema must validate against `schemas/theme_block.json`. Key differences from sections:

- **No `"tag"` at top level** — blocks don't render a wrapping tag like sections do.
- **`{% doc %}` header is required** for static rendering (via `{% content_for 'block', type: 'x', id: 'y' %}`). Include it even if the block starts off as merchant-draggable only — future devs may want to render it statically.
- **`{{ block.shopify_attributes }}`** must be present on the block's root element for the theme editor to wire drag handles and selection highlights correctly.
- **`"blocks": [{ "type": "@theme" }]`** opens the block to nesting any other theme block (drop this key if the block should not accept children). Specific block types can be listed instead of `@theme` to restrict.
- **Use `block.settings` and `block.id`** instead of `section.settings` and `section.id`.
- **`"presets"` is different** — presets for blocks describe default child-block configurations when a merchant drops the block into a section.

### Schema header grouping (both sections and blocks)

Group settings under `{ "type": "header", "content": "<t: key or plain text>" }` in this order:

1. **Content** — data pickers, headings, body text, CTAs.
2. **t:image.name** — image_picker settings, aspect-ratio selects.
3. **t:appearance.content** — `width` (sections only) and `color_mode`.
4. **t:colors.name** (with `visible_if: "{{ <section|block>.settings.color_mode == 'custom' }}"`).
5. **t:button.content** — button color overrides.
6. **t:typography.name** — font sizes, weights, line heights.
7. **t:size.desktop.content** — paired `desktop_padding_*` ranges.
8. **t:size.mobile.content** — paired `mobile_padding_*` ranges.

### Hard-won lessons (apply to both sections and blocks)

**1. Match Figma's layout mechanism, not just values.** Nested flex vs CSS Grid matters. If Figma is `flex-col` containing `flex` rows, use nested flex. Mismatching produces subtle sizing bugs.

**2. Outer `align-items` mirrors Figma exactly.** Default flex is `stretch`. If Figma uses `items-start`, set `align-items: flex-start`.

**3. Scope CSS via `#<slug>-{{ section.id }}` (or `{{ block.id }}`) for higher specificity.** Snippets like `responsive-image` style themselves with `#responsive-image-XXX` (specificity 100). Scoped descendant selectors give you 111 — wins cleanly, no `!important` needed.

**4. Restyle nested snippet buttons via CSS-variable overrides.** `snippets/add-to-cart.liquid` uses `--color-add-to-cart-*` CSS vars, not `snippets/button.liquid` variants. Redeclare those vars inside your scoped rule rather than forking the snippet.

**5. Mobile-first with one breakpoint.** Base = mobile, `@media (min-width: 64rem)` for desktop. Match the theme's breakpoint.

**6. Paired `mobile_*` / `desktop_*` settings for padding.** Mirror `testimonial-carousel.liquid`. Hardcode gaps that Figma fixes.

**7. Hardcode Figma-fixed values.** If Figma has fixed aspect-ratios, hardcode them; don't expose a merchant dropdown.

**8. Reuse translation keys.** Check `locales/en.default.schema.json` before inventing labels. Plain English defaults for design-specific labels (tagline, image slot positions).

**9. Blocks use `block.id` for scoping, not `section.id`.** Each instance gets a unique id — scope your CSS to that for safe multi-instance rendering.

**10. Blocks must include `{{ block.shopify_attributes }}`** on the root element. Without it, the theme editor's drag handles and click-to-select don't work properly.

### Step 4.5: Register the block as a theme block type (BLOCKS ONLY)

Skip this step for sections — sections are auto-discovered by Shopify from the `sections/` directory and don't need registration. For blocks, two registrations are required before the block is discoverable and usable anywhere in the editor. Do both, in order.

#### 4.5a. Add name + category to `locales/en.default.schema.json`

Block editor translations live in **`en.default.schema.json`** (NOT `en.default.json` — that file holds storefront user-facing strings like cart/checkout labels). Under the top-level `"block": { ... }` map, add an entry keyed by the new block's name (follow the surrounding naming convention — most entries use snake_case even though the block filename is kebab-case; e.g., filename `scrapbook-collage.liquid` → key `scrapbook_collage`):

```json
"block": {
  ...existing entries...,
  "<snake_name>": {
    "name": "<Display Name>",
    "category": "<Layout | Text | Button | Link | Media>"
  }
}
```

- The **`name`** field is required and maps to `"t:block.<snake_name>.name"` in the block's own schema.
- The **`category`** field is optional — include it when the block fits an existing category (look at neighboring entries: `group`→Layout, `text`→Text, `button`→Button, `link`→Link, `media`→Media). If no existing category fits, omit `category` — many existing entries (e.g., `accordion.item`, `dialog`, `newsletter_form`) have no category.
- For blocks with their own **child-block types**, nest them: e.g., `"accordion": { "name": "Accordion", "category": "Layout", "item": { "name": "Accordion Item" } }`.
- For blocks with named **presets**, add `"presets": { "<preset-key>": "<Preset Label>" }` — see existing `group`, `button`, `tabs` for the pattern.

**Canonical reference:** read `locales/en.default.schema.json` lines ~94–307. Ordering groups related blocks (header items, product-page items, article-page items) together. Match the surrounding style — don't force strict alphabetical if the file uses thematic grouping.

#### 4.5b. Add the new block type to every parent that accepts blocks

A block needs to appear in each parent's schema `"blocks":` array to be draggable into that parent in the theme editor. Deep-scan both directories — this theme has 18 sections and 13 blocks with `"blocks":` schema settings (31 parents total):

```bash
grep -lE '"blocks":\s*\[' sections/*.liquid blocks/*.liquid
```

For each parent, classify:

- **Permissive parent** — long, diverse list (sometimes includes `"@app"` or `"@theme"`). Examples in this theme: `sections/section.liquid` (~25 block types), `blocks/group.liquid` (~25 block types), `blocks/layout-carousel.liquid`. **Add the new block type to these automatically**, inserted to match the existing order. Current convention is *alphabetical by block type*, with `@app`/`@theme` first if present.
- **Narrow-scope parent** — short, curated list. Examples: `blocks/accordion-item.liquid` (6 types: text/button/icon/link/divider/media), `blocks/tabs.liquid` (only `tab`), `blocks/product-hotspots.liquid` (likely `product-point` only), `blocks/dialog.liquid`. **Adding here is a semantic decision — ASK the user** before modifying: "Should this new block be valid inside accordion items / as a tab / inside hotspots?". Only add if they confirm.

The insertion touches only the `"blocks":` array — do not reorder or modify unrelated settings in the parent's schema.

**Canonical examples to mirror:**
- **Section-level** (permissive): `sections/section.liquid`, look at `"blocks":` around line 195. Alphabetical list of block types, `@app` first.
- **Block-level** (permissive): `blocks/group.liquid`, look at `"blocks":` around line 278. Same pattern as `section.liquid` — a block that acts as a layout container.
- **Block-level** (narrow): `blocks/accordion-item.liquid`, `"blocks":` at line 21. Six curated types — don't auto-add here.

The skill must cover both directories because blocks themselves can be parents. Skipping `blocks/` means nested-block compositions (e.g., putting your new block inside a `group` or `accordion-item`) won't work in the theme editor.

### Step 4.7: Coverage check (re-read enumerated list against generated markup)

Re-open the enumerated component list from Step 2. For each numbered item, confirm a corresponding block of Liquid markup exists in your output file. Walk top-to-bottom; check off each item.

If an item has NO corresponding markup:

- **If forgotten**: add it. Re-pull from MCP if you need exact specs.
- **If intentionally omitted** (e.g., user said "skip the helper strip"): document it in your final report as a deviation, with a one-line justification.
- **If unsure whether it should be rendered**: ask the user before moving on. Don't silently drop.

This step takes 60–90 seconds and prevents the most common Figma-build failure: shipping a section that looks 80% right but is missing entire elements the merchant will notice immediately. Specs-match passing on every block is necessary but not sufficient — coverage is what distinguishes a 100% match from an 80% one.

### Step 5: Wire into the template — BRANCH BY TYPE

#### If section

Read `templates/<template>.json`. Structure:

```json
{
  "sections": {
    "section_abc123": { "type": "hero", "settings": { ... } },
    "section_def456": { "type": "testimonial-carousel" }
  },
  "order": ["section_abc123", "section_def456"]
}
```

1. Generate a unique section key (`section_` + 6-8 random chars). Verify no collision.
2. Add an entry to `"sections"`: `"type": "<kebab-name>"` matching the new file.
3. Insert the key into `"order"` at the specified position.

#### If block

Blocks can be wired in two ways — pick based on the user's "Parent section" input.

**(a) Insert instance inside a specific section in the template JSON.** The section's entry looks like:

```json
"section_abc123": {
  "type": "hero",
  "settings": { ... },
  "blocks": {
    "block_xyz789": { "type": "existing-block", "settings": { ... } }
  },
  "block_order": ["block_xyz789"]
}
```

1. Generate a unique block key (`block_` + 6-8 random chars).
2. Add an entry to the section's `"blocks"` with `"type": "<kebab-name>"`.
3. Insert the key into the section's `"block_order"` at the specified position.

**(b) Add as a block type to a section's schema.** Open `sections/<section-slug>.liquid`, find the `"blocks"` array in the `{% schema %}`:

```json
"blocks": [
  { "type": "@theme" },
  { "type": "<kebab-name>" }  // add this
]
```

This makes the new block type available in the theme editor for that section, without placing an instance. No template JSON change.

**(c) Register only.** No wiring — just create `blocks/<kebab-name>.liquid`. The block becomes a standalone reusable type; merchants discover it via the theme editor's block picker for any section that accepts `{ "type": "@theme" }`.

### Step 6: Full Shopify Validation (HARD GATE — must pass before commit)

**This is non-negotiable.** The theme repo is connected to the Shopify theme editor via GitHub. Every push auto-syncs. If Liquid, JSON, or schema rules are violated, Shopify rejects the file — the section/block fails to appear, OR Shopify silently rolls back the JSON template change in an "Update from Shopify" commit. Merchants then see broken admin UX with no error message.

Run every applicable check below in order. Any failure = fix before commit, not after. **Run even if `shopify theme check` passes** — it is necessary but not sufficient.

#### 6a. Invoke the Shopify plugin skills for rule research (when touching metafields, new block types, or non-trivial schema)

Before validating, invoke the relevant Shopify plugin skills via the Skill tool:

- `shopify-plugin:shopify-liquid` — surfaces current Liquid syntax rules and best practices for theme files.
- `shopify-plugin:shopify-custom-data` — MANDATORY when the section reads metafields or metaobjects. Verifies the access + render patterns match current Shopify behavior.
- `shopify-plugin:shopify-dev` — general Shopify docs search for edge cases not covered by the API-specific skills.

These plugin skills reflect current Shopify platform state. Training-data assumptions about schema rules and Liquid filters go stale.

#### 6b. Liquid syntax + theme check — final pass (run ONCE, after all edits)

Run this at the END of Step 6 — after every `.liquid` file is written, every parent schema registered, every template JSON wired, every locale entry added. There is no separate "final pass" step (this used to be Step 7, now consolidated here).

```bash
shopify theme check --path <theme-root> -C theme-check:all --fail-level=warning \
  -x AssetSizeCSS \
  -x AssetSizeJavaScript \
  -x AssetSizeAppBlockCSS \
  -x AssetSizeAppBlockJavaScript \
  -x RemoteAsset
```

The five excluded checks (`AssetSize*` and `RemoteAsset`) verify deploy-weight budgets and external-asset reachability — orthogonal to the Liquid/schema/JSON correctness this skill validates. On themes with 150+ assets, leaving them enabled inflates wall-time to 20+ minutes per run while surfacing offenses that aren't actionable in the context of this skill's edits. Every other rule in `theme-check:all` (Liquid syntax, schema validity, translation completeness, deprecated tags, parser-blocking scripts, etc.) remains active. If you separately need asset-weight verification before deploy, run `shopify theme check --path <theme-root> -C theme-check:all --fail-level=warning` (without `-x` flags) on its own.

Run with **`-C theme-check:all`** (the full check set, not the default `:recommended`) and **`--fail-level=warning`** (so warnings are reported, not just errors). Theme-check's default fail-level is `error`, which silences warnings — use this stricter invocation for ship-verification.

- Zero NEW offenses on files you created or edited.
- Pre-existing offenses in unrelated files unchanged (list them in your final report, marked out-of-scope).

Common Liquid failure modes theme-check catches:

- **Inline filter in `{% for %}` iterator** — `{% for col in 'a,b,c' | split: ',' %}` is rejected by Shopify's parser (`Expected end_of_string but found pipe`). Fix: pre-assign with `{% assign cols = 'a,b,c' | split: ',' %}` then `{% for col in cols %}`.
- **`{% doc %}` header not at the very top** of a block file — required for `{% content_for 'block' %}` static rendering. No blank lines or other Liquid before it.
- **Missing `{{ block.shopify_attributes }}`** on the block's root element — editor drag handles break silently.
- **`"tag"` key present in a block's `{% schema %}`** — blocks don't accept a top-level `tag`, only sections do.
- **Unknown filters** (e.g. `| push` — Liquid has no `push` filter; use for-loop iteration over a fixed range with conditional assignment instead).

#### 6c. Schema JSON validity (every file with `{% schema %}`)

Parse the schema body as JSON:

```bash
python -c "
import json
p = '<path/to/file>.liquid'
d = open(p, encoding='utf-8').read()
s = d.index('{% schema %}') + len('{% schema %}')
e = d.index('{% endschema %}')
json.loads(d[s:e])
print('OK', p)
"
```

Run for every `.liquid` file you created or edited (including parent schemas you registered the block type in).

#### 6d. Schema paragraph 500-character limit (CRITICAL — not caught by theme-check)

**Shopify enforces a hard 500-character limit on `paragraph` setting content.** Exceeding it triggers `FileSaveError: Invalid schema: setting with type="paragraph" content is too long (max 500 characters)` at push time — the file is rejected and does not sync.

`shopify theme check` does NOT catch this. Validate with a custom script:

```bash
python -c "
import json, glob
files = glob.glob('sections/*.liquid') + glob.glob('blocks/*.liquid')
fail = False
for f in files:
    d = open(f, encoding='utf-8').read()
    if '{% schema %}' not in d: continue
    s = d.index('{% schema %}') + len('{% schema %}')
    e = d.index('{% endschema %}')
    try:
        schema = json.loads(d[s:e])
    except Exception: continue
    def walk(node):
        if isinstance(node, dict):
            if node.get('type') == 'paragraph' and isinstance(node.get('content'), str) and len(node['content']) > 500:
                print(f'FAIL {f}: paragraph len={len(node[\"content\"])}: {node[\"content\"][:80]!r}')
                return True
            return any(walk(v) for v in node.values())
        if isinstance(node, list):
            return any(walk(v) for v in node)
        return False
    if walk(schema): fail = True
print('OK' if not fail else 'FAIL — fix paragraphs above')
"
```

If a walkthrough step needs more than ~450 chars to explain, split it across multiple consecutive `paragraph` settings. The admin renders them as separate paragraphs visually — continuity is preserved.

#### 6d2. Schema empty-string `default` values (CRITICAL — not caught by theme-check)

**Shopify rejects any setting that declares `"default": ""`** (an empty string). At push/sync time it raises `FileSaveError: Invalid <section|block> '<name>': setting with id="<id>" default can't be blank`, and the file is rejected — the section/block fails to save and does not sync. If a `default` key is present it MUST be non-blank; for a field that should start empty (common for optional `text`/`textarea`/`html` settings), **omit the `default` key entirely** — do NOT set it to `""`, a space, or a placeholder.

This bites most when block settings are added with `"default": ""` scaffolding. `shopify theme check` does NOT catch it — it only surfaces server-side on save/sync (a Liquid formatter will happily keep an empty default). Validate with:

```bash
python -c "
import json, glob, re
fail = False
for f in glob.glob('sections/*.liquid') + glob.glob('blocks/*.liquid'):
    d = open(f, encoding='utf-8').read()
    m = re.search(r'{%-?\s*schema\s*-?%}(.*?){%-?\s*endschema\s*-?%}', d, re.S)
    if not m: continue
    try: schema = json.loads(m.group(1))
    except Exception: continue
    def walk(node):
        global fail
        if isinstance(node, dict):
            if 'default' in node and node['default'] == '':
                print(f'FAIL {f}: setting id={node.get(\"id\")!r} has empty-string default — omit the default key')
                fail = True
            for v in node.values(): walk(v)
        elif isinstance(node, list):
            for v in node: walk(v)
    walk(schema)
print('OK' if not fail else 'FAIL — remove the empty default keys above')
"
```

Fix: delete the `"default": ""` key from each flagged setting. Note the regex schema-extractor above also handles the trimmed `{%- schema -%}` tag form — prefer it over `d.index('{% schema %}')` (used in 6c/6d), which silently skips files that use trimmed schema tags.

#### 6e. Schema label & setting ID length sanity

Shopify enforces limits on setting IDs (no spaces, must be valid Liquid-safe identifier) and generally recommends labels under ~50 chars for sidebar readability. Verify:

- Setting `id` values are `snake_case`, no spaces, no hyphens, no special chars.
- Setting `label` values are concise (ideally ≤50 chars, hard-cap observed at 255).
- Section/block `name` at the top of schema is ≤50 chars.

Enforce a `VariableName` naming discipline (theme-check has a warning for this) — settings keys should be `snake_case`.

#### 6f. Block type naming convention

Block `type` values in schema and template JSON must:
- Match the block's filename (minus `.liquid`) — e.g. `blocks/product-card.liquid` → `"type": "product-card"`.
- Use `kebab-case` for multi-word types.
- Match exactly when referenced across files (parent schema `"blocks"` array, template JSON `"blocks"` entries, `content_for 'block'` type argument).

#### 6g. Required schema fields

Verify the schema has all required top-level keys for its file type:

- **Sections**: `name` (required), `tag` (recommended — `"section"`), `settings`, `presets`. `enabled_on` is optional but recommended for template-specific sections.
- **Blocks**: `name` (required), `settings`, `presets`. **No `tag`** at top level. `blocks` array if accepting nested blocks.

#### 6h. Template JSON + section-group JSON (every `templates/*.json` and `sections/*-group.json` you modified)

These files have a leading `/* ... */` comment that standard JSON parsers reject — skip past it:

```bash
python -c "
import json
for p in ['sections/footer-group.json', 'templates/index.json']:  # substitute modified files
    d = open(p, encoding='utf-8').read()
    obj = json.loads(d[d.index('{'):])
    if 'sections' in obj:
        missing = set(obj.get('order', [])) - set(obj['sections'])
        assert not missing, 'order references unknown sections: ' + str(missing)
    print('OK', p, '—', len(obj.get('sections', obj)), 'top-level keys')
"
```

The orphan-reference check catches adding a key to `order` / `block_order` without adding a matching entry in `sections` / `blocks`.

#### 6i. Locales JSON (if you edited `locales/*.json` or `locales/*.schema.json`)

```bash
python -c "
import json
for p in ['locales/en.default.json', 'locales/en.default.schema.json']:
    d = open(p, encoding='utf-8').read()
    json.loads(d[d.index('{'):])
    print('OK', p)
"
```

Verify every `t:` key referenced in the new schema has a matching entry in `locales/en.default.schema.json` (for editor-time translations). Verify every `{{ 'key' | t }}` in the Liquid body has a matching entry in `locales/en.default.json` (for storefront-time translations). These are two different files — easy to confuse.

#### 6j. Metafield output-type matching (when Data Source = Metafield or Mix)

If the section reads metafields, confirm each reference in the Liquid uses the correct pattern for its field type (see the "Metafield / Metaobject Liquid patterns" section above). Most dangerous mistake: rendering `rich_text_field.value` — outputs the raw JSON AST as visible garbage. `shopify theme check` does NOT catch this. Grep your file:

```bash
grep -nE "\{\{ [^}]*\.value \}\}" sections/<new-file>.liquid
```

For each match, verify the underlying field type isn't `rich_text_field`. If it is, switch to `{{ field | metafield_tag }}` and drop the trailing `.value` on the assign.

**Only commit if every check 6a–6j prints OK.** A failed validation means Shopify will reject the push and the section/block won't render — do not commit.

### Step 7: Fidelity verification against Figma (final pass — TWO sub-steps)

This step is MANDATORY and has two distinct sub-steps. Both must complete. Specs-match alone has shipped sections missing entire elements; visual comparison is the safety net.

#### 7a. Visual side-by-side comparison (FIRST — catches coverage misses)

Render the section on a real page and compare visually with the Figma frame. Two paths:

**Path A — Self-verify via Chrome MCP (preferred).**

If `shopify theme dev` is running and Chrome MCP is available:

1. Navigate to the page hosting the section:
   - `mcp__claude-in-chrome__navigate` (or `mcp__chrome-devtools-mcp__navigate_page`)
2. Take a desktop screenshot at ~1440px viewport:
   - `mcp__claude-in-chrome__resize_window` to 1440×900, then `mcp__claude-in-chrome__take_screenshot` (or `mcp__chrome-devtools-mcp__resize_page` + `take_screenshot`)
3. Take a mobile screenshot at ~390px viewport (iPhone SE-ish):
   - resize to 390×844, screenshot
4. Take Figma screenshots for both frames:
   - `mcp__plugin_figma_figma__get_screenshot` for desktop nodeId
   - `mcp__plugin_figma_figma__get_screenshot` for mobile nodeId
5. Compare each pair side-by-side. List every visual delta — focus first on COVERAGE deltas (elements present in one but not the other), then on quality deltas (spacing/typography/colors).

**Path B — Request user-provided screenshots (when Chrome MCP isn't available).**

If the dev server isn't accessible to MCP, or Chrome MCP tools are unavailable, ASK the user to provide:

- A screenshot of the rendered page at desktop width (~1440px)
- A screenshot of the rendered page at mobile width (~390px)

Compare side-by-side with the Figma frames. Don't proceed to 7b without this comparison — specs-match-only verification has shipped missing-element bugs that only screenshot comparison surfaces.

For each visual delta found in 7a:

- **Coverage delta** (element missing from one side): refer back to your enumerated list (Step 2). If the missing element is in Figma but not the output, add it. If it's in the output but not Figma, ask the user before removing — they may want it.
- **Quality delta** (element exists but wrong specs): re-pull from MCP for the exact value, fix, and re-verify.

#### 7b. Spec checklist (SECOND — confirms visual fixes are correct)

After 7a is clean, walk the spec checklist for both desktop and mobile frames:

1. **Spacing** — every margin, padding, and gap matches Figma exactly. No eyeballed values.
2. **Sizes** — every width, height, and max-width matches Figma exactly.
3. **Typography** — font family, weight, size, line-height, letter-spacing, and color all match Figma. Theme-default fallbacks ONLY where Figma explicitly uses the theme token.
4. **Colors** — backgrounds, borders, text, icons, overlays, gradients, and shadows match Figma exactly.
5. **Icons** — every icon in the rendered output matches the icon used in Figma (same library, same name, same fill/stroke/size).
6. **Layout & components** — structural tree of the rendered HTML mirrors Figma's component tree (no missing children, no extra wrappers).
7. **Responsive** — desktop styles apply at the theme's correct breakpoint; mobile styles match the mobile frame exactly. No new breakpoint introduced.

If any item fails: fix it, re-pull the spec from MCP if needed, and re-verify both 7a and 7b. Do not proceed to Step 8 until both sub-steps pass for both viewports.

#### 7c. Post-deploy verification (REQUIRED — local-dev render ≠ live-deployed render)

After committing and pushing, Shopify's GitHub integration validates the change before deploying. It can silently:
- Strip unknown schema keys from template JSON (when schema deploy lags JSON deploy in the same commit)
- Roll back invalid block references
- Drop unknown `t:` translation keys
- Reject `paragraph` settings over 500 chars
- Reject settings that declare an empty-string `default` (`"default": ""`) — see 6d2

Local `shopify theme dev` reads your committed files directly — what you see is what you committed. The live theme renders only what survived Shopify's deploy validation. They diverge silently.

Before declaring done:

1. After `git push`, watch for the next commit on `origin/main`. If it's an `Update from Shopify for theme <name>` commit that touches files you just edited, that's a silent rollback. Investigate immediately:
   ```bash
   git log -1 --stat origin/main          # see what the bot commit changed
   git diff HEAD~1 HEAD -- templates/<file>.json   # see which keys got stripped
   ```
2. Re-take a screenshot of the LIVE theme (via Shopify admin's "View" or "Preview" link, NOT `shopify theme dev`).
3. Compare the live screenshot to Figma per Step 7a. If anything Figma-mandated is missing on the live site but present in your local file, you've hit silent rollback. Common fix per the "Shopify git-integration gotchas" section: make a small follow-up edit to the same template JSON to force re-processing against the now-deployed schema.

Concrete: in a recent session, `show_greene_badge: true` was committed but stripped by Shopify's bot on deploy. The badges rendered locally but not on the live site — only caught when the user observed the live site personally. A post-deploy check would have caught it before the user did.

### Step 8: Report — commit only if asked

Return a summary:

- **Files created** (section or block).
- **Files modified** (template JSON or parent section schema, or neither for register-only blocks).
- **Reused** — snippets, translation keys, CSS variables.
- **New settings introduced** — each with reason.
- **Deviations** — where user preferences were adjusted for technical reasons.
- **Theme check result** — offense count before vs after.

When committing, match the project's existing style. Examples:

- New section: `Add "<Display Name>" section between <X> and <Y>`.
- New block: `Add "<Display Name>" block to <Section>` or `Register "<Display Name>" block type`.

## Metafield / Metaobject Liquid patterns (REQUIRED reading when Data Source = Metafield or Mix)

When the Data Source interview (Step 3c) selects Metafield or Mix, BEFORE writing any metafield-reading Liquid you MUST:

1. **Invoke `shopify-plugin:shopify-custom-data`** via the Skill tool. This is Shopify's maintained knowledge skill for metafields and metaobjects. It reflects current admin UX and Liquid patterns — assumptions from training data go stale. Never skip.
2. **Invoke `shopify-plugin:shopify-liquid`** for Liquid filter/drop/rendering details.
3. **Use `shopify-plugin:shopify-dev`** for broader docs questions not covered by the API-specific skills.

### Output method per metafield / metaobject field type

Every reference in your Liquid must use the correct pattern for its field type. Mis-rendered output (e.g. raw JSON AST instead of HTML) is a silent failure — `shopify theme check` does NOT catch it.

| Field type | Access pattern | Render pattern | Notes |
|---|---|---|---|
| `single_line_text_field` | `field.value` | `{{ field.value }}` | Plain string |
| `multi_line_text_field` | `field.value` | `{{ field.value \| newline_to_br }}` | Convert newlines to `<br>` |
| `rich_text_field` | `field` (NO trailing `.value`) | `{{ field \| metafield_tag }}` | `.value` returns the AST drop — rendering it outputs raw JSON. **See the rich_text pitfall below.** |
| `file_reference` (image) | `field.value` | `{% render 'responsive-image', image: field.value %}` | Pass to responsive-image snippet |
| `file_reference` (generic) | `field.value` | `{{ field.value.url }}` | Get the asset URL |
| `product_reference` | `field.value` | Access `.title`, `.url`, `.featured_image` | Returns product drop |
| `collection_reference` | `field.value` | Access `.title`, `.url`, `.products` | Returns collection drop |
| `metaobject_reference` | `field.value` | Access nested fields on the returned drop | Chain with `.subfield.value` per sub-field |
| `list.metaobject_reference` | `field.value` | `{% for item in field.value %}...{% endfor %}` | Iterable list; NEVER index with `[n]` |
| `list.single_line_text_field` | `field.value` | `{% for item in field.value %}...{% endfor %}` | Iterable list of strings |
| `number_integer` / `number_decimal` | `field.value` | `{{ field.value }}` | Returns number |
| `boolean` | `field.value` | `{% if field.value %}...{% endif %}` | true/false |
| `color` | `field.value` | `{{ field.value }}` or as CSS value | Hex string |
| `url` | `field.value` | `{{ field.value }}` | URL string |

### The rich_text pitfall (critical — previously shipped bug)

**Rendering `{{ rich_text_field.value }}` prints the raw JSON AST**, not HTML. Output looks like:

```
{"type"=>"root", "children"=>[{"listType"=>"unordered", "type"=>"list", "children"=>[...]}]}
```

This is because `.value` on a rich_text field returns a Liquid drop whose `to_s` serialises the parsed structure as a visible string. This exact bug shipped to a production theme editor in April 2026 — surface it explicitly so future sessions avoid it.

**Correct pattern for a direct metafield:**
```liquid
{{ product.metafields.custom.body | metafield_tag }}
```

**Correct pattern for a metaobject sub-field:**
```liquid
{%- liquid
  assign content_field = product_tabs.details.value.content   # field object — drop trailing .value
-%}

{%- if content_field.value != blank -%}                        {# .value used for blank-check only #}
  <div class="rte">{{ content_field | metafield_tag }}</div>   {# render via filter #}
{%- endif -%}
```

**Two patterns coexist in the same file:**
- **Rich_text fields** — assign the field object (no trailing `.value`), check `.value != blank` for presence, render with `| metafield_tag`.
- **List metaobject_reference fields** — use `.value` to get the iterable list, iterate with `{% for ... %}`.

Don't uniformly append `.value` — field type dictates the pattern.

### Conventions for metaobject definitions (theme-wide, this codebase)

When generating Data Source instructions in the `{% schema %}` paragraph blocks:

- The first field of every metaobject is named **"Label"** (Single line text), described in the walkthrough as "set as the Display Name, used only to identify the entry in the admin." Don't call the field itself "Display Name" — that's Shopify's configuration for the field, not the field name.
- For nested metaobject aggregators (one parent metaobject referencing child metaobjects), the parent pattern the codebase has established is `Product Tabs` — a single metaobject with fields like `details` (reference to Product Details), `materials` (reference to Product Materials), `colors` (reference to Product Colors). This gives one metafield attachment per product instead of N.
- Schema `paragraph` settings are hard-capped at **500 characters** server-side by Shopify. Split long walkthrough steps across multiple consecutive paragraphs. `shopify theme check` does NOT enforce this — validate with the paragraph-length script in Step 6g.

## Anti-patterns (both types)

- **Forking snippets to restyle them.** Use scoped CSS-variable overrides.
- **Inventing translation keys when existing ones fit.** Grep `locales/en.default.schema.json` first.
- **Using CSS Grid to reproduce a nested-flex Figma layout.** Grid auto-stretches rows under a stretched flex parent.
- **Merchant settings for Figma-fixed values.** Hardcode them.
- **Skipping orientation.** Theme conventions differ.
- **Committing without user approval.**
- **Introducing a new breakpoint.** Reuse the theme's existing one.

## Anti-patterns (block-specific)

- **Omitting `{{ block.shopify_attributes }}`.** The theme editor breaks without it.
- **Omitting the `{% doc %}` header.** Required for static rendering via `{% content_for 'block', type: 'X', id: 'Y' %}`. Include it even if the block is initially only merchant-draggable.
- **Using `section.id` instead of `block.id` for scoping.** Breaks when the block is instantiated multiple times on a page.
- **Putting `"tag"` in a block's `{% schema %}`.** Sections have tags; blocks don't.
- **Forgetting to add the new block type to the parent section's schema `"blocks"` array** when the user chose option (b). The block won't appear in the editor otherwise.
- **Skipping Step 4.5a (locales registration).** The block will render, but its display name in the theme editor will show as the raw translation key (`t:block.my_block.name`) instead of a proper name. This is a common "looks broken in the admin UI" bug.
- **Scanning only `sections/` and missing parent blocks.** Block files can themselves be parents (e.g., `group`, `accordion-item`, `tabs`). A new block that should be nestable inside `group` but isn't added to `blocks/group.liquid`'s `"blocks":` array will be undraggable there — a subtle regression that's only caught by end-user testing.
- **Auto-adding to a narrow-scope parent without asking.** Adding a `leather-care-card` block into `accordion-item.liquid`'s blocks list would make it draggable inside accordion panels, which may be semantically wrong. Always confirm with the user for narrow-scope parents.
- **Using `en.default.json` instead of `en.default.schema.json` for block translations.** They're different files: `.json` is storefront strings, `.schema.json` is theme-editor strings. Block names belong in the latter.
- **Inline filter in a `{% for %}` iterator.** `{% for col in 'a,b,c' | split: ',' %}` fails with `Expected end_of_string but found pipe`. Shopify's parser doesn't accept filters on the iterator expression. Pre-assign: `{% assign cols = 'a,b,c' | split: ',' %}{% for col in cols %}`.
- **Skipping the placement interview.** Generating the `.liquid` file before asking which parent schemas to register in — or which template to wire into — guarantees a rework cycle. Always interview first.

## Shopify git-integration gotchas (deployment)

These are things that look like "the code is broken" but are actually sync behaviors of Shopify's git integration. Save the user a debugging spiral by knowing them up front.

- **Silent JSON rollback on invalid block.** If a template JSON (e.g., `sections/footer-group.json`) references a block type whose `.liquid` file has a Liquid syntax error OR whose type isn't registered in the parent's schema, Shopify commits an "Update from Shopify" commit back to the repo that REMOVES the invalid block reference. The block disappears from the editor with no error surfaced. Fix the underlying file, then re-add the JSON reference in a follow-up commit.
- **Incremental sync only processes changed files.** When you push a commit that fixes a `.liquid` file but doesn't touch the template JSON, Shopify deploys the block fix but does NOT re-process the JSON — so a previously-rolled-back JSON reference stays rolled back. Workaround: make a second commit that also touches the template JSON (even trivially) so Shopify re-processes it alongside the now-valid block. For `sections/*-group.json` files, adding the missing `settings` keys to an instance (e.g., `shop_menu: ""`) is a clean way to create a meaningful JSON diff.
- **`shopify theme check` is authoritative for Liquid/JSON validity, but not for registration completeness.** Theme check won't warn about a block type missing from a parent's `"blocks":` array — it only catches syntax errors. Registration coverage is the skill's job, not the linter's.
