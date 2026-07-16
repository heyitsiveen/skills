---
name: shopify-update-content-from-figma
description: >-
  Replace the TEXT/COPY (and matching icons) of EXISTING Shopify section instances in a
  template JSON so they match Figma frames — given a template plus one or more
  "Section Name: Figma URL" pairs. Use this whenever the user points at a `templates/*.json`
  and lists existing sections to update from Figma URLs (the "Section: URL" pattern), or says
  things like "update all the content on every section from these Figma frames", "replace the
  copy of the Lab Verified / How It Works / Comparison sections from Figma", "sync this
  section's text to the Figma design", or "this template has leftover copy from another product
  — fix it from Figma". It edits ONLY `settings`/`block` VALUES on sections that ALREADY EXIST —
  it never adds, removes, or restructures sections/blocks, never edits `.liquid`, and never
  fabricates images. It swaps an icon reference only when a matching already-uploaded asset
  exists, and otherwise flags images/icons for manual upload. Prefer this over
  `shopify-add-section-or-preset-from-figma` (composes NEW sections from primitives),
  `shopify-build-section-or-block-from-figma` (writes NEW `.liquid`), `shopify-sync-page-from-figma`
  (whole-page visual/LAYOUT sync needing desktop+mobile), and `shopify-update-existing-section-from-figma`
  (edits `.liquid` code) whenever the task is purely swapping the COPY of existing JSON section instances.
---

# Shopify — Update Section Content From Figma

Make the **copy** of sections that already exist in a Shopify template JSON match their Figma
designs. This is a **content-replacement** task: you change the *values* of `settings` and
block keys (headings, body, labels, cell text, card titles/descriptions) — and swap icon
references when a matching asset already exists — but you never touch structure, layout, or
`.liquid` files.

The canonical real-world case: a template was **duplicated** from a sibling product (e.g. a
Marri product template copied from the Jarrah one) and still carries the wrong copy. The Figma
frames are the source of truth for the corrected text. Most of the job is fixing those
leftovers — and often several strings already match, so "replace" frequently means "leave it."

## When to use vs. the sibling skills

Pick this skill when the user gives a **template + "Section: URL" pairs** and wants existing
copy updated. Route elsewhere when:

- They want a **new** section composed from existing blocks → `shopify-add-section-or-preset-from-figma`
- They want a **new `.liquid`** section/block authored → `shopify-build-section-or-block-from-figma`
- They want a **whole page's visual layout** synced (spacing/sizes/added+removed sections, needs desktop+mobile) → `shopify-sync-page-from-figma`
- They want to edit a section's **`.liquid` code** to match Figma → `shopify-update-existing-section-from-figma`
- They want to **copy sections between** templates → `shopify-copy-template-content`

If the user asks for structural changes (add/remove cards, change layout) on top of copy, say
so and offer to escalate to the layout/sync or build skills — don't quietly restructure here.

## Required inputs

1. **Template** — the `templates/*.json` to edit (e.g. `product.marri-honey-default.json`).
2. **One or more `Section Name: Figma URL` pairs.** The *name* is something findable in the
   template (a section `type`, a heading value, or an editor label); the *URL* is the Figma
   frame whose copy should win. Desktop URLs are normal here — copy is breakpoint-agnostic, so
   a mobile URL is usually unnecessary (ask only if a frame's text looks breakpoint-specific).

If a name can't be located or a URL is missing, ask — don't guess which section is meant.

## The rule

- **Edit values only, in place.** Change `settings`/block string values on sections that
  already exist. Never add/remove/reorder sections or blocks, never change `block_order`,
  never touch padding/colors/layout settings, never edit `.liquid`.
- **Figma is the source of truth for copy** — use its exact wording (this is a specific
  deployment, so real copy is correct, not placeholders).
- **Replace ≠ rewrite.** Many strings often already match Figma. A section can legitimately
  need *zero* edits (brand-level copy like a "Lab Verified" blurb is identical across products).
  Changing nothing is a valid, correct outcome — report it as a match.
- **Icons:** swap an icon reference only when a matching already-uploaded asset exists (see
  Step 5). Never invent or fabricate an asset path.
- **Images:** never fabricate. You cannot pull a photo out of Figma. Flag every image that
  likely needs a manual swap and let the merchant upload it.

## Workflow

### Step 1 — Locate each named section

Map each "Section Name" to a real top-level entry (key, `type`, line range). Grep for both
section types and distinctive heading text rather than reading the whole file:

```bash
grep -nE '^    "[A-Za-z0-9_]+": \{|^      "type":|^  "order"' templates/<file>.json
grep -nE '<heading words from the section names>' templates/<file>.json
```

Sections come in two shapes, and this determines how you find the copy:

- **Dedicated section types** (e.g. `how-it-works`, `lab-verified`, `comparison-v2`): content
  lives in named keys (`heading`, `intro_text`, `cell_3`, step `title`/`description`). Read the
  section's block directly — it's usually short (50–150 lines).
- **Generic `section` compositions**: content is scattered across dozens of nested
  `group`/`text`/`highlight-text` blocks and the section can be *thousands* of lines. Do NOT
  read it whole — see Step 3's grep technique.

### Step 2 — Fetch each Figma frame

Call `mcp__plugin_figma_figma__get_design_context` once per section (parse `node-id=a-b` →
`nodeId "a:b"`, `fileKey` from the URL). The returned screenshot + text are your target copy.
Walk the frame top-to-bottom and list every visible text string so nothing is missed.

### Step 3 — Inventory the current copy (grep-first for big sections)

For dedicated sections, read the block. For generic compositions, **grep the copy out** instead
of reading 1800 lines — this is the single biggest efficiency win:

```bash
grep -nE '"text":|"richtext":|"title":|"label":|"description":|"heading' templates/<file>.json
```

You get every string with its line number. Cross-reference against the section's line range
from Step 1, and you have the current copy without paging through the whole file.

### Step 4 — Build a per-section diff

For each section, produce a `current → Figma` table for every text field. Mark which already
match (no-op) and which differ. Show this to the user before editing — it's the proof of what
will change and lets them catch a wrong section mapping. Watch for near-misses that are easy to
gloss over (one word changed, a "TA35+" → "TA25+", "Does NOT crystallize" → "crystallizes
after some time").

### Step 5 — Icons (swap only when an asset already exists)

When Figma shows a different icon than the section currently uses, look for an already-uploaded
asset before changing anything:

```bash
grep -nE 'shopify://shop_images/[^"']+\.(svg|png|webp)' templates/*.json | grep -iE '<glyph>'
```

Sibling instances of the same section type (in other templates) are the best source — they
reveal which uploaded asset maps to which glyph, often with misleading filenames (a
`harvest_cycle_tree_*.svg` may actually draw a certificate or shield). If you find the right
asset, swap the reference. If not, **flag it** for manual upload — never fabricate a path.

### Step 6 — Images (flag, never fabricate)

List every image field on the touched sections and whether it likely needs a Marri/Jarrah-style
swap (compare the Figma frame's photo to the field's role). State the exact key + current asset
so the merchant knows what to replace in the editor. Generic/brand photos that already match
(e.g. a lab bench, decorative badges) need no change — say so.

### Step 7 — Apply targeted edits

Use `Edit` with a unique `old_string` per field. Two byte-level gotchas that cause silent
mismatches in Shopify JSON:

- **Curly apostrophes.** The files use `’` (U+2019), not `'` — e.g. `You’ll`, `Can’t`,
  `body’s`. Match and write the curly form.
- **Escaped newlines.** Multi-line cell values store `\n` literally (e.g.
  `"Ancient, pristine forests of\nWestern Australia"`). Include the `\n` in both old and new
  strings exactly as it appears.

Anchor on the `"key": "value"` pair (e.g. `"cell_2": "35+ / 2000+"`) — the value makes it
unique without needing surrounding indentation. Multiple `Edit` calls to the same file in one
turn apply sequentially; that's fine.

### Step 8 — Validate

1. **JSON parse.** These templates begin with a leading `/* ... */` comment, so strip it before
   parsing:
   ```powershell
   $raw = Get-Content -Raw 'templates/<file>.json'
   ($raw -replace '(?s)^\s*/\*.*?\*/\s*','') | ConvertFrom-Json   # throws if broken
   ```
2. **`shopify theme check`** — authoritative for JSON/Liquid validity. Filter output to the
   summary line. (It does NOT catch wrong copy or rolled-back references — that's your job.)
3. **Sweep for leftovers.** Grep the edited section ranges for the old product's name / rating
   (e.g. `Jarrah`, `TA35`) to confirm none survived inside the sections you were asked to fix.

### Step 9 — Report

- Per-section summary of what changed (and which sections were already matching → no-op).
- **Images to replace** — exact keys + current assets the merchant must upload.
- **Out-of-scope leftovers** — old-product copy you noticed *outside* the named sections (e.g.
  a leftover "Evening: Jarrah TA35+" in the product block or FAQ). Surface it and ask; don't
  silently edit beyond the requested scope.
- Note that on commit a `lint-staged`/prettier hook may reformat the whole file (large
  insertion/deletion counts that dwarf your few string edits are expected and harmless).

## Hard-won lessons

- **Grep before you read.** A generic `section` can be 1800+ lines; `grep "text":` gives you
  the whole copy inventory in one call. Reading the file whole wastes context and invites errors.
- **Dedicated vs generic is the key fork.** Named keys (read directly) vs scattered nested
  blocks (grep). Decide this in Step 1.
- **Most of the work is correcting a duplicated template.** Expect Jarrah-on-a-Marri-template
  style leftovers; the Figma frame tells you the right wording. Some brand-level copy is
  identical across products and needs no edit.
- **Byte-exact matching.** Curly `’` and literal `\n` are the two things that make an `Edit`
  silently fail to match. Copy them from the grep/read output verbatim.
- **Theme check is necessary but not sufficient.** It validates syntax, not whether the copy is
  right or complete — always do the visual/diff check and the leftover sweep yourself.

## Anti-patterns

- Restructuring blocks, changing `block_order`, or editing padding/colors/layout — out of scope;
  escalate to the sync/build skills instead.
- Editing a `.liquid` file — this skill is JSON-values only.
- Fabricating an image path or inventing an icon asset that isn't already uploaded.
- Rewriting copy that already matches Figma "just to be safe" — leave matches alone.
- Reading a multi-thousand-line section top to bottom instead of grepping its copy.
- Silently fixing leftovers outside the sections the user named — flag and ask.
