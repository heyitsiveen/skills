---
name: shopify-add-section-or-preset-from-figma
description: Use when the user wants to add a new Shopify theme section to a JSON template (index.json, product.json, collection.json, page.*.json) OR append a new preset to a section's {% schema %} presets array (sections/*.liquid), matching a Figma design for BOTH desktop and mobile, composed strictly from the theme's existing sections and blocks (no new .liquid files, no schema changes). Triggers on phrases like "add this Figma as a section", "insert a new row on the homepage from Figma", "turn this Figma design into a Shopify section", "add a new preset to sections/section.liquid", "append this Figma as a preset", "create a preset from Figma", or any request supplying a Figma URL and either a Shopify template or a section .liquid file.
user-invocable: true
---

# Shopify Add Section or Preset From Figma

Compose a new section in a Shopify JSON template **or** append a new preset to a section's `{% schema %}` block from a Figma design, using only the theme's existing primitives. No new `.liquid` files, no new schema — JSON edits only.

This skill covers two related workflows:
- **Template mode** (original) — insert a new section into `templates/*.json`. Use when the user provides a `Template: <template>.json` target.
- **Preset mode** — append a new preset to the `presets` array inside a section's `{% schema %}...{% endschema %}` block. Use when the user provides a `Section: <section-file>.liquid` target. See the "Creating new presets" section below.

The Figma parsing, block-primitive mapping (Phase 3 table), non-obvious learnings, and responsive breakpoint apply to both modes.

## Required inputs (ask if missing, never guess)

The user must provide four inputs. The first input determines which mode is active — ask about any missing input in a single `AskUserQuestion` call before proceeding.

**Template mode inputs:**

1. **Template** — e.g. `index.json`, `product.json`. File in `templates/`. (Presence of this input → template mode.)
2. **Position** — natural language. Any of:
   - `After "Hero - Split"` (insert immediately after the named section)
   - `Before "Collection Grid"` (insert immediately before the named section)
   - `Order #3` or `At index 3` (explicit position in the `order` array — confirm with the user whether 0-indexed or 1-indexed if ambiguous)
3. **Desktop** — `figma.com/design/{fileKey}/...?node-id={a}-{b}` URL for the desktop design
4. **Mobile** — `figma.com/design/{fileKey}/...?node-id={a}-{b}` URL for the mobile design

**Preset mode inputs:**

1. **Section** — e.g. `sections/section.liquid`. The `.liquid` file whose `{% schema %}` presets array you will extend. (Presence of this input → preset mode; jump to the "Creating new presets" section below.)
2. **Position** — `After "FAQs"`, `Before "Newsletter"`, or `At the end`
3. **Desktop** Figma URL
4. **Mobile** Figma URL

If the user provides a Figma URL and a placement hint but hasn't indicated which mode (no `Template:` or `Section:` prefix), ask them whether they're adding the section to a JSON template or appending a preset to a section's schema. Do not guess — the edit target differs significantly.

## The rule

**Use ONLY existing sections and blocks.** Scan `sections/` and `blocks/` to inventory primitives; compose from those. If a Figma element cannot be reproduced with the existing set, surface it in "Known caveats" — do not invent new schema.

**Match BOTH breakpoints.** Every layout and typography decision must specify `desktop_*` AND `mobile_*` settings. A Figma design that provides only one breakpoint is a red flag — ask.

**Clone the nearest sibling.** The existing template almost always contains a structurally similar section. Cloning its skeleton (outer section settings, group nesting, mobile reorder pattern) is safer than authoring from scratch.

**Cover every visible element.** Every visible element in the Figma frame must be represented by a section/block instance in the composed JSON, and every section/block instance in your composition must correspond to something in Figma. Mapping each Figma frame to an existing primitive is the core composition task — partial coverage is the most common failure mode (entire sub-headings, badges, and helper strips have been silently skipped in past runs because they got glossed over during orient). The "Enumerate Figma elements" step (below) makes coverage explicit; the "Coverage and visual verification" gate (before Full Shopify Validation) verifies it side-by-side with Figma before commit.

## DO NOT — red flags

- **DO NOT** declare the composition complete based solely on JSON validation (orphan-reference check, parse success) or mental Figma-mapping against MCP data. Visual side-by-side comparison — rendered screenshot vs Figma frame — is the authoritative check. In a recent session, an entire sub-heading and per-card badges were missed because verification was JSON-only; fixing them required user-provided screenshots to surface the gaps. The "Coverage and visual verification" section below is mandatory before the Full Shopify Validation hard gate.
- **DO NOT** silently drop a Figma element that doesn't have a clean existing-primitive mapping. Surface it as a "Known caveat" in the plan and ask the user whether to omit, approximate, or escalate to `shopify-build-section-or-block-from-figma` (which can author a new `.liquid` file).
- **DO NOT** trust Figma frame names blindly when enumerating elements. "Frame 73" or "Container" tells you nothing about the role; verify by content — heading text, primary label, or position-relative-to-siblings.
- **DO NOT** invent or override CSS properties through `custom_css` or per-instance schema settings to add spreads, transitions, hover transforms, or filter effects Figma doesn't specify. The composing-from-existing-primitives skill is meant to use whatever the existing primitive exposes — if Figma's spec requires a property the primitive doesn't expose, surface as a "Known caveat" and escalate to `shopify-build-section-or-block-from-figma`. Don't bolt on CSS in `custom_css` to bridge the gap; that's a fidelity violation that's invisible to the merchant.
- **DO NOT** ship a composition where the existing primitives' built-in icons don't match Figma's icon style. If a `button` block's icon variant doesn't match Figma's icon shape, do NOT rationalize "merchant can swap" — surface in "Known caveats" and escalate to BUILD if the gap is large. Composing from primitives means accepting their visual constraints; if the constraints break Figma fidelity, that's a routing problem (wrong skill), not a "fix in JSON" problem.

## Enumerate Figma elements (MANDATORY first step for both modes)

After Phase 1 (template mode) or Phase 2 (preset mode) returns the Figma `get_design_context` response, walk the metadata top-to-bottom and build a numbered list of EVERY visible element in the frame. This list anchors the design-match mapping (template Phase 3 / preset Phase 4), the Coverage check (after execute), and the Visual verification (before validation).

Include:

- Headers and sub-headings (including small ones like "Step 2: ..." that look like section dividers)
- Trust pills, badges, eyebrow text, certification labels (e.g. "Green-e Certified", "Most Popular")
- Cards, columns, repeating tiles — name each one (e.g. "Card 1 (HydroWind)", "Card 2 (SolarWind)")
- Bottom strips, helper text, link-buttons, secondary CTAs
- Decorative elements with content (logos, inline icons, divider lines)

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

This list is the source-of-truth for "what must be composed." Each item maps to one or more existing primitives via the design-match mapping table. Items without a clear primitive go in "Known caveats" — do not invent schema; surface the gap and ask the user whether to escalate to the BUILD skill.

**Sparse-metadata caveat.** When the MCP responds with "the design was too large to fit into context," it returns a sparse tree of frame names + dimensions + text content. The sparse tree IS exhaustive for *what visible elements exist* — every frame is listed by name. Use it to build the enumerated list, even if you defer drilling into every sub-frame for full styles. Don't skip elements just because the response said "too large."

**Then search existing templates for prior art (MANDATORY before mapping to primitives).**

Before mapping each enumerated Figma element to a primitive in Phase 3 (template mode) / Phase 4 (preset mode), grep the rest of the theme for existing renderings of the same element. Reusing existing patterns reveals image references, link conventions, and primitive choices that have ALREADY been tested:

```bash
grep -rE "<keyword>" templates/ sections/ blocks/ | head -20
grep -nE "shopify://shop_images/[^\"']+" templates/*.json | head
```

Concrete: the membership-pricing section in this codebase needed a Green-e Certified badge. A grep for "green-e" across templates surfaced `shopify://shop_images/1_percent_green_e.png` (existing Green-e PNG asset) AND the convention that the badge text links to `https://www.green-e.org/` — both inside `ai_gen_block_33f0c1c` referenced from `templates/page.residential.json` and `templates/page.more-information.json`. Without this cross-template grep, the build would have authored a placeholder SVG and shipped a generic-looking section.

For ADD specifically, prior art is even more useful than for BUILD because the existing block instance shows you exactly which primitive (`media`, `button`, `highlight-text`, etc.) the merchant has already approved for that element type. Reuse the same primitive choice — not the closest-equivalent-you-can-think-of.

## Workflow

### Phase 1 — Orient (parallel tool calls)

In ONE message, call in parallel:

- `Read` first ~300 lines of `templates/{template}`
- `Bash: ls sections/` and `ls blocks/`
- `mcp__plugin_figma_figma__get_design_context` for the desktop URL
- `mcp__plugin_figma_figma__get_design_context` for the mobile URL

For Figma: parse `figma.com/design/{fileKey}/{name}?node-id={a}-{b}` → `fileKey={fileKey}`, `nodeId="{a}:{b}"` (convert `-` to `:`). If the URL contains `/branch/{branchKey}/`, use `branchKey` as `fileKey`.

### Phase 2 — Deep scan (1–2 Explore subagents in parallel)

**Agent A (schemas)**: ask for full documented schemas of `sections/section.liquid`, `blocks/group.liquid`, `blocks/text.liquid`, `blocks/highlight-text.liquid`, `blocks/media.liquid`, `blocks/button.liquid`, `blocks/divider.liquid`. Request desktop-vs-mobile setting split for each. Demand actual setting keys, not paraphrases.

**Agent B (template map)**: ask for an ordered list of every top-level entry in `templates/{template}['sections']` — section key, `type`, inferred human label, start/end line numbers. Request the `order` array verbatim. Identify the insertion point (after/before the named section or at the given index). Report the line number of the closing `}` before the insertion point.

If the task is isolated and you already know both, skip one.

### Phase 3 — Design match

From the Figma `get_design_context` responses, extract and map:

| Figma property | Mapped primitive / setting |
|---|---|
| Two-tone inline text (base color + highlighted segment) | `highlight-text` block → `text_color_mode: "custom"`, `text_color`, `highlight_color`, `text`, `highlight_text` |
| Short heading or paragraph, single color | `text` block, `text_style: "default"`, `text_tag: "h1".."h6"` or `"p"` |
| Short text with explicit line break | `text` block, `text_style: "default"`, embed `\n` in the `text` field — Shopify renders it via `newline_to_br` in `snippets/text.liquid` |
| Multi-paragraph prose (3+ paragraphs) | `text` block, `text_style: "richtext"`, fill `richtext` with `<p>...</p>` blocks |
| Image | `media` block, `media_type: "image"`, leave `image` key OMITTED so the merchant uploads via the editor. Use `desktop_custom_height: "{px}px"` + `mobile_custom_height: "{px}px"` (fixed pixel values — grep production themes; you will find zero uses of `"100%"` here) |
| Video | `media` block, `media_type: "video"`, set `video_autoplay/loop/mute` explicitly |
| CTA / button | `button` block — `label`, `url`, `variant`, `size`, `icon_mode` |
| Two-column layout desktop / single-column mobile | Top-level `section` with `desktop_grid_columns: 2`, `mobile_grid_columns: 1`, `desktop_gap`, `mobile_gap`, padding tuple |
| Flex container for 2+ children with alignment | `group` block, `display_type: "flex"`, `desktop_direction`, `desktop_column_align_items`, `desktop_gap`, etc. |
| Mobile reorder (image above text on mobile, side-by-side on desktop) | Wrap the text in a `group` that has `mobile_display_order: true` + `display_order: "2"` — the inverse sibling defaults to `"1"` |
| Divider line | `divider` block — `orientation`, `color_mode` |

### Phase 4 — Clarify (single batched AskUserQuestion, max 4 questions)

Only ask about genuinely ambiguous choices — never about routine settings.

Typical question set:
1. **Section display name** (the `name` field visible in the Shopify theme editor sidebar) — offer 2–3 options based on the content.
2. **CTA handling** — if Figma shows no button, ask whether to add one anyway or omit to match design.
3. **Image field** — confirm leave-empty-for-merchant-upload (usually yes); offer placeholder CDN path as alternative.
4. **Figma-parity compromises** — if any (see "Known compromises" below), surface them so the user can redirect.

**Respect the user's explicit dropdown selection.** If a typed note conflicts with the selection, flag the conflict and keep the dropdown value — do not silently override based on the note.

### Phase 5 — Plan (plan mode)

Write the plan file with these sections:

- **Context** — why, which Figma nodes, target template, intended outcome (include desktop and mobile summary)
- **Approach** — which sibling section you're cloning; a mapping table (sibling → new) showing which blocks replace which
- **Typography mapping** — Figma tokens → block settings, in a table
- **Block composition** — indented tree of the new section's block hierarchy
- **Primitive choices** — one line per non-obvious pick (e.g. "why `highlight-text` instead of `text`+richtext")
- **Files to modify** — the single template file; two edits (insert section + update order array)
- **Exact JSON to insert** — full block ready to paste
- **Exact `order` array edit** — before/after snippet
- **Reused primitives** — table of files NOT to modify
- **Verification** — concrete steps; include `python -c "import json; d=open('...').read(); json.loads(d[d.index('{'):])"` (the `d.index('{')` skip bypasses Shopify's leading `/* */` comment)
- **Known caveats** — Figma-parity compromises (see below)

Call `advisor()` before committing to the plan AND once more before declaring done (after executing). On plan approval, call `ExitPlanMode`.

### Phase 6 — Execute (after user approval)

1. `Read` 5–10 lines around the exact insertion point to capture indentation context
2. `Edit` — insert the new section JSON into `sections` using `old_string` that spans the unique boundary between the preceding section's closing `}` and the following section's opening key (always a unique string in the file)
3. `Edit` — insert the new section key into the `order` array at the right position (use a surrounding-neighbors `old_string` for uniqueness)
4. Validate with Python:
   ```bash
   python -c "import json; d=open('templates/{template}').read(); obj=json.loads(d[d.index('{'):]); assert set(obj['sections'].keys())==set(obj['order']), 'order/sections mismatch'; print('OK', len(obj['sections']), 'sections')"
   ```
5. Dump the new section's structure to confirm nesting — print `block_order`, padding tuple, and each leaf block's type + key settings

### Phase 7 — Report

End-of-turn summary (short):

- New section key + display name
- One-line role per block (what Figma element each renders)
- Responsive behavior: desktop layout + mobile stacking order
- User next steps: `shopify theme dev`, upload portrait/media in editor, tune fixed heights if whitespace appears

## Creating new presets (preset mode)

Use this variant when the user wants to add a **preset** to a section's `{% schema %}` block rather than insert a section into a JSON template.

### Recognizing preset mode

The user supplies `Section: <section-file>.liquid` (e.g. `sections/section.liquid`) as the target, or says things like "add a new preset to the section's schema", "append this Figma as a preset", "create a preset from Figma". The output is a new object appended to the `presets` array inside the target file's `{% schema %}...{% endschema %}` block.

The Figma parsing (Phase 1), block-primitive mapping (Phase 3 table), non-obvious learnings, known compromises, and responsive breakpoint all apply unchanged. The differences are: target file, pre-flight duplication check, placeholder-only content, and edit mechanics.

### Required inputs (ask if missing, never guess)

1. **Section file** — path to the `.liquid` file whose schema `presets` array you will extend (e.g. `sections/section.liquid`).
2. **Position** — where in the `presets` array:
   - `After "FAQs"` (directly after the named preset)
   - `Before "Newsletter"`
   - `At the end` (append last — the default)
3. **Desktop** Figma URL
4. **Mobile** Figma URL

Ask for missing inputs in a single `AskUserQuestion` call before proceeding.

### Mandatory constraints for preset mode

These reinforce the shared rules and add new ones specific to presets:

- **Use only existing blocks and settings.** No new `.liquid` files, no new schema keys. Every block `type` and every setting `id` used in the preset JSON must already exist in the theme.
- **Always check for duplicates first** (Phase 1 below). Presets are merchant-facing: a duplicate makes the sidebar confusing and wastes engineering effort. Pause and flag rather than silently adding.
- **Placeholder content only — never copy Figma's actual text.** The Figma design is for layout, typography, and styling reference. For every text-bearing setting (headings, body copy, subtitles, button labels, captions, accordion headings, link labels, email/phone values), use generic placeholders. Examples:
  | Setting role | Placeholder |
  |---|---|
  | Heading | `"Heading"`, `"Section title"`, `"Your headline here"` |
  | Body paragraph | `"Section body text. Replace this placeholder with..."`, `"Lorem ipsum..."` |
  | Subtitle / eyebrow | `"Section subtitle"`, `"Eyebrow text"` |
  | Button | `"Button label"`, `"Learn more"`, `"Shop now"` |
  | Accordion item | `"FAQ question 1"`, `"Question heading"` |
  | Accordion answer | `"Answer placeholder. Replace this with..."` |
  | Contact email | `"hello@example.com"` |
  | Contact phone | `"+1 555 000 0000"` |
  | Link URL | `""` (empty — merchant fills in) |
  | Image | key omitted (merchant uploads) |

  Rationale: merchants install presets expecting generic defaults they'll replace. Shipping Figma's actual copy leaks another brand's messaging into the theme and embarrasses everyone.
- **Preserve all existing presets.** Your edit appends a new object; it never overwrites, renames, or removes siblings.
- **Match existing preset naming and structure conventions.** Read nearby presets to learn the theme's naming patterns (e.g. `Hero - Split`, `Mission - Highlights`, `Newsletter - Split`), indentation (typically 4 spaces for the preset object), and key ordering (`name`, `category`, `settings`, `blocks`).

### Preset-mode workflow

#### Phase 1 — Duplication check (MUST run before any design work)

Inventory the target section's existing presets:

```bash
grep -n '"name"' sections/<file>.liquid
```

For each existing preset, compare against the Figma design on three axes:

- **Name** — is there a preset with the same or a near-identical display name?
- **Structural shape** — does an existing preset already compose the same top-level blocks (e.g. `section: 2 cols → group + accordion`)?
- **Block tree** — does an existing preset's hierarchy roughly match the Figma (same block types, same nesting depth, same approximate count)?

If any existing preset matches on any axis, **pause and flag it to the user via `AskUserQuestion`**. Offer:
1. Skip this preset entirely (recommended if it's truly a duplicate)
2. Replace the existing preset (only if the user explicitly wants to supersede it)
3. Add with a distinguishing name (`- Compact`, `- Dark`, etc.)
4. Proceed anyway (user's call — acknowledge the duplication in the plan's "Known caveats")

Do not silently add a duplicate. This phase exists because merchants see every preset side-by-side in the editor and can't tell two near-identical presets apart.

#### Phase 2 — Orient

In parallel:
- `Grep` the target file for `{% schema %}`, `{% endschema %}`, `"presets": [`, and `"name":` to locate schema boundaries, the presets array bounds, and every existing preset's start line.
- `Read` the existing presets in chunks to find the structurally closest sibling — that becomes your clone target. For two-column layouts, `Mission - Split` or `Newsletter - Split` are common choices.
- `Bash: ls blocks/` to inventory block primitives.
- `mcp__plugin_figma_figma__get_design_context` for the desktop URL.
- `mcp__plugin_figma_figma__get_design_context` for the mobile URL.

#### Phase 3 — Deep scan (1 Explore subagent)

Have the subagent return the FULL schemas (setting IDs, types, defaults, desktop/mobile split, `visible_if` conditions) of every block the design maps to. Common set: `group`, `text`, `highlight-text`, `contact-link`, `accordion`, `accordion-item`, `media`, `button`, `divider`, `icon`. Request actual setting keys — not paraphrases.

#### Phase 4 — Design match

Same as template mode's Phase 3 mapping table. The mapping from Figma primitives to block types + settings is identical.

#### Phase 5 — Clarify (batched AskUserQuestion, max 4 questions)

Typical questions for preset mode:
1. **Preset name** — 2–4 options following the theme's convention (e.g. `FAQs - Split`, `Contact & FAQs`, `FAQs - Get In Touch`). Merchant-facing, shown in the editor sidebar.
2. **Icon size / image field handling** — if Figma shows icons (`contact-link`) or hero images (`media`), confirm defaults (size, or leave empty for merchant upload).
3. **Item count** — accordion items, card counts, carousel slides — match Figma vs. match an existing preset pattern for consistency.
4. **Figma-parity compromises** — any trade-offs to surface (e.g. `contact-link` has no responsive typography split).

#### Phase 6 — Plan (plan mode)

Plan file sections:
- **Context** — why, Figma nodes, target section file, user-confirmed decisions
- **Duplication check result** — what you compared, why no duplicate exists
- **Approach** — which sibling preset you're cloning; mapping table (sibling → new)
- **Figma → block primitive mapping** — same structure as template mode
- **Block composition tree** — indented tree of the new preset's hierarchy
- **Primitive choices** — non-obvious picks with rationale
- **Exact JSON to insert** — full preset object ready to paste, indented to match siblings
- **Edit mechanics** — the exact `old_string` anchor and why it's unique (see Phase 7)
- **Reused primitives** — table of files NOT to modify
- **Verification** — Python JSON validation (preset-mode idiom, below)
- **Known caveats** — Figma-parity compromises

Call `advisor()` before committing to the plan. On approval, `ExitPlanMode`.

#### Phase 7 — Execute

1. `Read` 10–20 lines around the exact insertion point to lock indentation and comma placement.
2. `Edit` — insert the new preset. The `old_string` must be globally unique. A reliable anchor is the closing `]` of the previous preset's `blocks` array + the opening `{` and `"name": "<Next Preset>"` line of the following preset — the next preset's name disambiguates.

   If appending at the end, the anchor is the previous preset's closing `}` + the presets array's closing `]`. Add a comma to the previous preset's trailing `}` so the array stays valid.

3. Validate with Python (preset-mode idiom — different from template-mode because the JSON is inside `{% schema %}` tags, not a standalone file):

   ```bash
   python -c "d=open('sections/<file>.liquid').read(); s=d.index('{% schema %}')+len('{% schema %}'); e=d.index('{% endschema %}'); import json; obj=json.loads(d[s:e]); print('OK', len(obj['presets']), 'presets'); print([p.get('name') for p in obj['presets']])"
   ```

   Expected: preset count increased by 1, and the new name appears in the printed list at the correct position.

4. Dump the new preset's structure to confirm nesting: top-level block types, accordion item count, contact-link children, etc.

#### Phase 8 — Report

End-of-turn summary:
- New preset name + category
- Block composition (1 line per top-level block + leaf counts)
- Desktop vs mobile layout summary
- Merchant next steps: `shopify theme dev`, theme editor → Add section → category → pick the new preset, replace placeholder content with real copy

### Template mode vs preset mode — quick reference

| Aspect | Template mode | Preset mode |
|---|---|---|
| Target file | `templates/*.json` | `sections/*.liquid` (JSON inside `{% schema %}`) |
| Edits | 2 (sections map + order array) | 1 (append to presets array) |
| JSON boundary handling | Skip leading `/* */` comment (`d.index('{')`) | Skip `{% schema %}` / `{% endschema %}` tags |
| Content authoring | Actual copy is acceptable (specific deployment) | **Placeholders only** — merchants replace |
| Category & naming | Section gets a `name` | Preset gets a `name` + `category` (translation key) |
| Duplication risk | Low (each template entry is unique) | **High — always check first** |
| Typical plan length | Medium | Medium-to-long (full preset JSON is verbose) |

## Non-obvious learnings (load-bearing)

These are findings from real successful runs — internalize them, don't just follow them:

- **`snippets/text.liquid:76`** renders textarea text via `{{ text | newline_to_br }}` — so `\n` becomes `<br>`, `\n\n` becomes `<br><br>`. This enables line breaks in `text_style: "default"` without resorting to richtext.
- **`blocks/highlight-text.liquid:80-85`** renders as `<p>{{ text }}<span>{{ highlight_text }}</span></p>` with CSS scoping color to `p` (base text) and `span` (highlight) selectors. `text_color_mode: "custom"` is required to set both colors explicitly — `"inherit"` defaults the highlight to `var(--color-primary-background)` which is rarely the brand accent.
- **Shopify's richtext field strips inline styles.** If you try to render a two-tone eyebrow via `<p>WELCOME TO <span style="color: #757a2d">ANITA</span></p>` inside a `text` block's richtext, the inline style is removed at render time and both colors appear identical. This is why `highlight-text` exists. Do not use inline `<span style="">` as a shortcut.
- **Media `desktop_custom_height: "100%"` does not work** — grep any production theme's `templates/*.json` and you will find zero uses. Always use fixed pixel values. Heuristic: match the height of the text column (e.g. 600–750px for a multi-paragraph split section on desktop).
- **Empty `image` key is the canonical pattern** for merchant-uploaded images. Existing sections omit the key entirely rather than referencing a placeholder CDN path. Avoids broken-reference risk.
- **`mobile_display_order: true` + `display_order: "2"`** on an inner group is the idiomatic way to put the image above the text on mobile while keeping text-left / image-right on desktop. The sibling element defaults to `display_order: "1"`.
- **Duplicate section names are allowed** in the Shopify editor but make the sidebar confusing. Prefer distinct `name` values even when cloning a sibling section.

## Known compromises to flag up-front

Surface these in "Known caveats" in the plan so the user knows before approving:

- **Mobile text-wrap points** cannot be pinned. A `highlight-text` block's break between the base and highlighted segments is natural-wrap (container-width driven). If pixel-perfect mobile typography is required, split into two stacked `text` blocks with explicit line breaks.
- **Fixed image heights** are heuristic. If the merchant later shortens/lengthens the body copy, the image may leave whitespace or feel cramped. Tunable in the editor.
- **The template JSON file has a leading `/* */` comment** warning that Shopify admin may overwrite the file. Merchant edits in the admin before your PR is merged can generate conflicts.

## Coverage and visual verification (MANDATORY before validation — TWO sub-steps)

This shared verification gate applies to both modes (template + preset). JSON-validity-only verification has shipped compositions missing entire elements; the two-step process below is the safety net. Do not proceed to "Full Shopify Validation" until both sub-steps pass.

### Step A — Coverage check (re-read enumerated list against composed JSON)

Re-open the enumerated component list from Phase 1 (template) / Phase 2 (preset). For each numbered item, confirm a corresponding section/block instance exists in your composed JSON (template mode: in `templates/<file>.json`; preset mode: in the preset's `blocks` array within `{% schema %}`). Walk top-to-bottom; check off each item.

If an item has NO corresponding instance:

- **If forgotten**: add it. Re-pull from MCP for exact specs if needed. Refer back to the design-match table (template Phase 3 / preset Phase 4) for the right primitive.
- **If intentionally omitted** (e.g., user said "skip the helper strip"): document it in your final report as a deviation, with a one-line justification.
- **If unsure whether it should be composed**: ask the user before moving on. Don't silently drop.
- **If no existing primitive can render it**: surface in "Known caveats" — do not invent schema. Offer to escalate to `shopify-build-section-or-block-from-figma` if the user wants 100% Figma fidelity.

This step takes 30–60 seconds and prevents the most common Add-section/preset failure: composing a JSON that looks 80% right but is missing entire elements the merchant will notice immediately. JSON validation passing is necessary but not sufficient — coverage is what distinguishes a 100% match from an 80% one.

### Step B — Visual side-by-side comparison

Render the section (template mode) or preset (preset mode) on a real page and compare visually with the Figma frame. Two paths:

**Path A — Self-verify via Chrome MCP (preferred).**

If `shopify theme dev` is running and Chrome MCP is available:

1. Navigate to the page hosting the composed section (template mode) or to a preview of the preset (preset mode):
   - `mcp__claude-in-chrome__navigate` (or `mcp__chrome-devtools-mcp__navigate_page`)
2. Take a desktop screenshot at ~1440px viewport:
   - `mcp__claude-in-chrome__resize_window` to 1440×900, then `mcp__claude-in-chrome__take_screenshot` (or `mcp__chrome-devtools-mcp__resize_page` + `take_screenshot`)
3. Take a mobile screenshot at ~390px viewport (iPhone SE-ish):
   - resize to 390×844, screenshot
4. Take Figma screenshots for both frames:
   - `mcp__plugin_figma_figma__get_screenshot` for desktop nodeId
   - `mcp__plugin_figma_figma__get_screenshot` for mobile nodeId
5. Compare each pair side-by-side. List every visual delta — focus first on COVERAGE deltas (elements present in one but not the other), then on quality deltas (spacing/typography/colors that the existing primitive happens to expose via setting).

**Path B — Request user-provided screenshots (when Chrome MCP isn't available).**

If the dev server isn't accessible to MCP, or Chrome MCP tools are unavailable, ASK the user to provide:

- A screenshot of the rendered page at desktop width (~1440px)
- A screenshot of the rendered page at mobile width (~390px)

Compare side-by-side with the Figma frames. Don't proceed to "Full Shopify Validation" without this comparison — JSON-only verification has shipped missing-element bugs that only screenshot comparison surfaces.

For each visual delta found:

- **Coverage delta** (element missing from one side): refer back to your enumerated list (Phase 1/2). If the missing element is in Figma but not the rendered output, add the appropriate section/block instance to the composition. If it's in your composition but not Figma, ask the user before removing — they may want it.
- **Quality delta** (element exists but wrong specs): the gap is usually in a section/block setting that the merchant configures. Re-pull from MCP for the exact value, adjust the relevant setting in your JSON (e.g. `desktop_padding_top`, `text_color`, `image_ratio`), and re-verify. If the existing primitive doesn't expose a setting that matches Figma's spec, surface in "Known caveats" — `shopify-add-section-or-preset-from-figma` cannot add new schema settings; that's a BUILD-skill concern.

Do not proceed to "Full Shopify Validation" until all coverage deltas are resolved and all quality deltas are either fixed or documented in "Known caveats."

### Step C — Post-deploy verification (REQUIRED — local-dev render ≠ live-deployed render)

After commit and push, Shopify's GitHub integration validates the change before deploying. For composing-from-existing-primitives, the most common silent rollback is: a setting key on a section/block instance that's not registered in the parent's schema (because the schema was deployed in a separate, lagging commit) — Shopify strips the key and pushes back an `Update from Shopify...` commit.

Before declaring done:

1. After push, watch for the next commit on `origin/main`. If it's an `Update from Shopify for theme <name>` that touches the template you just composed into, investigate via `git log -1 --stat origin/main`. Diff the bot's changes against your commit to see which keys were stripped.
2. Re-screenshot the LIVE site, not local-dev render.
3. Run Step B Visual side-by-side against the live screenshot. Any Figma-element-missing-on-live-but-present-locally signals a silent rollback. Common fix: make a small follow-up edit to the template JSON to force Shopify to re-process the section against the now-deployed schema.

This applies to both template mode and preset mode. Preset mode rarely hits silent rollback (presets sit inside the section's own schema, deployed atomically with the schema change), but template mode hits it routinely when the composing JSON references settings whose schema arrived in the same commit. Concrete: in a recent membership-pricing build, `show_greene_badge: true` was committed but stripped by Shopify's bot on deploy — only caught when the user observed the live site personally.

## Full Shopify Validation (HARD GATE before commit)

**This is non-negotiable.** The theme repo is connected to the Shopify theme editor via GitHub — every push auto-syncs. Invalid JSON or broken Liquid causes Shopify to reject the file AND silently roll back changes in neighboring JSON templates, surfacing an `Update from Shopify` commit back to the repo that removes the invalid reference. Validation catches failures before they reach the deploy pipeline.

Run every check below that applies to your edit. Any failure = fix before commit, not after. **Run every applicable check even if the first one passes** — the local linter catches a subset; Shopify's server-side rules catch the rest.

### Step 1 — Invoke Shopify plugin skills for current-rules research

Before the automated validation steps, invoke the Shopify-maintained plugin skills that reflect current platform behavior:

- **`shopify-plugin:shopify-liquid`** — current Liquid syntax rules, filters, schema keys for sections/blocks.
- **`shopify-plugin:shopify-dev`** — general Shopify docs search for edge cases.

Training-data assumptions about Shopify schema rules go stale. These skills are the ground truth for current behavior and should be queried whenever you introduce a new schema key, new setting type, or non-trivial Liquid pattern.

### Step 2 — JSON validation (always applicable)

**Template mode** (edits to `templates/<template>.json`):

```bash
python -c "import json; d=open('templates/<template>').read(); obj=json.loads(d[d.index('{'):]); assert set(obj['sections'].keys())==set(obj['order']), 'order/sections mismatch'; print('OK', len(obj['sections']), 'sections')"
```

The `d.index('{')` skip handles the Shopify leading block comment. The `assert` catches orphan references between `sections` and `order` — the #1 cause of theme-editor "section is missing" bugs.

**Preset mode** (edits to `sections/<file>.liquid` schema):

```bash
python -c "
d = open('sections/<file>.liquid', encoding='utf-8').read()
s = d.index('{% schema %}') + len('{% schema %}')
e = d.index('{% endschema %}')
import json
obj = json.loads(d[s:e])
print('OK', len(obj['presets']), 'presets')
print([p.get('name') for p in obj['presets']])
"
```

Confirms the schema JSON parses AND the new preset's name appears at the expected position.

**Section-group JSON** (`sections/*-group.json`, e.g., footer/header layouts) — same as template mode; these files also have a leading `/* ... */` comment:

```bash
python -c "import json; d=open('sections/<file>-group.json').read(); json.loads(d[d.index('{'):]); print('OK')"
```

### Step 3 — Liquid validation (full rule set, all severities)

```bash
shopify theme check --path <theme-root> -C theme-check:all --fail-level=warning \
  -x AssetSizeCSS \
  -x AssetSizeJavaScript \
  -x AssetSizeAppBlockCSS \
  -x AssetSizeAppBlockJavaScript \
  -x RemoteAsset
```

The five excluded checks (`AssetSize*` and `RemoteAsset`) verify deploy-weight budgets and external-asset reachability — orthogonal to the Liquid/schema/JSON correctness this skill validates. On themes with 150+ assets, leaving them enabled inflates wall-time to 20+ minutes per run while surfacing offenses that aren't actionable in the context of this skill's edits. Every other rule in `theme-check:all` (Liquid syntax, schema validity, translation completeness, deprecated tags, parser-blocking scripts, etc.) remains active. If you separately need asset-weight verification before deploy, run `shopify theme check --path <theme-root> -C theme-check:all --fail-level=warning` (without `-x` flags) on its own.

Use `-C theme-check:all` (the full 60+ check set, stricter than the default `:recommended`) and `--fail-level=warning` (surfaces warnings, not just errors). The default invocation silences useful warnings — use this stricter form for ship-verification.

- Zero NEW offenses on the edited file.
- Pre-existing offenses in unrelated files unchanged (list them in your report, marked out-of-scope).

Even for preset mode — where you're only editing JSON inside `{% schema %}` — a malformed edit can break the surrounding Liquid (e.g., missing comma leaves the schema block unparseable, which turns the whole section into a parse error). Theme check catches this.

### Step 4 — Schema paragraph 500-character limit (CRITICAL — not caught by theme-check)

**Shopify enforces a hard 500-character limit on `paragraph` setting content.** Exceeding it triggers `FileSaveError: Invalid schema: setting with type="paragraph" content is too long (max 500 characters)` at push time — the file is rejected.

This only applies to preset mode (when editing `{% schema %}` inside a `.liquid` file) OR when a template-mode edit touches a section that has paragraph settings. Validate with:

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

Split any paragraph over the limit across multiple consecutive `paragraph` settings. `shopify theme check` does NOT catch this.

### Step 5 — Required schema fields + naming sanity

Confirm every schema block the edit touches (or creates) satisfies:

- **Sections**: `name`, `tag` (if present, `"section"`), `settings`, `presets`. `enabled_on` optional but recommended for template-specific sections.
- **Blocks**: `name`, `settings`, `presets`. No `tag` at top level.
- Setting `id` values are `snake_case` (no spaces, hyphens, or special chars). Theme-check's `VariableName` check flags violations at warning severity.
- Setting `label` values ≤ 50 chars for sidebar readability (hard-cap observed at 255).
- Block `type` values are `kebab-case` and match the `.liquid` filename exactly when referenced across schema + template JSON + `content_for 'block'`.

### Step 6 — Translation key cross-reference (when edits use `t:` keys)

Every `t:` key in a new/edited schema must have a matching entry in `locales/en.default.schema.json` (editor-time translations). Every `{{ 'key' | t }}` in Liquid body must have a matching entry in `locales/en.default.json` (storefront-time translations). These are two different files — easy to confuse.

Theme-check's `ValidSchemaTranslations` check catches schema-side misses. Storefront-side misses only surface when the section renders.

### What "fail" looks like

If any check errors out, do NOT commit. Common failures and fixes:

- `JSONDecodeError: Expecting ',' delimiter` — missing comma between preset objects in the array. The `old_string` anchor should have included the preceding preset's closing `}` so you could add `,` after it.
- `AssertionError: order/sections mismatch` — you added a key to `sections` but not `order`, or vice versa. Both edits must land together.
- `FileSaveError: ... paragraph content too long` — a `paragraph` setting exceeded 500 chars. Split it into multiple consecutive paragraphs.
- `ValidSchemaTranslations` theme-check offense — a `t:` key in schema has no matching entry in `locales/en.default.schema.json`.
- `shopify theme check` flags a new offense — inspect the reported line; most commonly a missing `{% endif %}`, stray `{% ... %}` tag, or unterminated string.

**Only commit after every applicable check prints `OK` and theme check is clean at `-C theme-check:all --fail-level=warning`.**

## Typical responsive breakpoint

`@media (width >= 64rem)` — 1024px. Desktop above, mobile below. Default to the same typography at both breakpoints unless Figma shows distinct sizes.
