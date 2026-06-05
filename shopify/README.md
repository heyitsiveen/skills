# Shopify Skills

## shopify-add-section-or-preset-from-figma

Use when the user wants to add a new Shopify theme section to a JSON template (index.json, product.json, collection.json, page.*.json) OR append a new preset to a section's `{% schema %}` presets array — matching a Figma design across desktop and mobile.

> Provide EITHER `Template:` OR `Section:` — the skill picks one mode per invocation.

**Template mode** (insert section into a JSON template):

```shell
# How to use:
/shopify-add-section-or-preset-from-figma
Template: @index.json
Position: After "X", before "Y" or "Order #3"/"At index 3"
Desktop: [figma URL]
Mobile: [figma URL]
```

**Preset mode** (append preset to a section's schema):

```shell
# How to use:
/shopify-add-section-or-preset-from-figma
Section: @sections/section.liquid
Position: After "X", before "Y" or "At the end"
Desktop: [figma URL]
Mobile: [figma URL]
```

---

## shopify-build-section-or-block-from-figma

Use when the user wants to BUILD a NEW Shopify theme section/block as a new .liquid file from Figma designs and wire it into a JSON template at a specific position.

```shell
# How to use:
/shopify-build-section-or-block-from-figma
Section:
Template: @index.json
Position: After "X", before "Y" or "Order #3"/"At index 3"
Desktop: [figma URL]
Mobile: [figma URL]

Block:
Template: @index.json
Position: After "X", before "Y" or "Order #3"/"At index 3"
Desktop: [figma URL]
Mobile: [figma URL]
```

---

## shopify-app-style-override-from-figma

Use when the user wants to OVERRIDE the visual styles of a third-party Shopify app widget (upsell bundles, review widgets, popup app blocks, deals embeds) to match a Figma design — purely CSS overrides, no app HTML/code changes.

```shell
# How to use:
/shopify-app-style-override-from-figma
Preview: [live preview URL where the widget renders]
Parent: @snippets/<file>.liquid
Desktop: [figma URL]
Mobile: [figma URL]
```

---

## shopify-update-content-from-figma

Use when the user wants to REPLACE the text/copy of EXISTING sections in a Shopify template JSON to match Figma frames — given a template plus one or more `Section Name: Figma URL` pairs. Values-only edits on sections that already exist: never adds/removes/restructures sections or blocks, never edits .liquid, never fabricates images. Swaps an icon reference only when a matching already-uploaded asset exists; otherwise flags images/icons for manual upload.

> Content/copy only — distinct from the sibling Figma skills: not composing new sections (add-section-or-preset), not building new .liquid (build-section-or-block), not whole-page layout sync (sync-page-from-figma), not editing .liquid code. The canonical case is fixing a duplicated template's leftover copy (e.g. a Marri product template still carrying Jarrah text) from the Figma source of truth. Find each section by name (grep types + headings), grep the copy out of big sections instead of reading them whole, diff current → Figma, and edit only what differs (some strings will already match).

```shell
# How to use:
/shopify-update-content-from-figma
Template: @templates/product.marri-honey-default.json
<Section Name from the template>: [figma URL]
<Section Name from the template>: [figma URL]   # one line per section to update
```

---

## shopify-copy-template-content

Use when the user wants to copy one or more SECTIONS or BLOCKS from a source Shopify template JSON file (e.g. `index.json`) into one or more sibling template JSON files (e.g. `product.json`, `product.in-stock.json`, `collection.json`, `page.*.json`) at a specified position. Never modifies the source. Skips items that already exist in a target (idempotent). Aborts before any write if a referenced name can't be resolved.

> Provide EITHER `Sections:` OR `Blocks:` — the skill picks one mode per invocation.

**Format A — Sections** (top-level sections in a JSON template):

```shell
# How to use:
/shopify-copy-template-content
From: @templates/index.json
Sections: "Scrolling text", "App wrapper"
From Position: After "Tabs FAQ"
To: @templates/product.json, @templates/product.in-stock.json
To Position: After "Tabs FAQ"
```

**Format B — Blocks** (nested under a specific section):

```shell
# How to use:
/shopify-copy-template-content
From: @templates/index.json
Blocks: "Promo banner", "Trust badge"
From Position: After "Hero"
To: @templates/product.json, @templates/product.in-stock.json
To Position: After "Hero"
```

---

## shopify-migrate-page-to-new-theme

Use when the user wants to migrate/recreate an EXISTING Shopify page (page, collection, or product template) from an OLD theme onto a NEW theme/codebase. Produces TWO deliverables — a comprehensive markdown spec doc AND a copy-paste handoff prompt for a fresh Claude Code session inside the new theme. Content is kept verbatim; the look is RESTYLED to the new theme's own design system — it scans the new theme's `config/settings_data.json` colors + fonts and adopts THOSE, never the old theme's.

> Two sources of truth: content/structure = OLD theme (verbatim, incl. typos); colors/fonts/components = NEW theme (scanned). The spec doc + reference screenshots are written into the new theme's `docs/`. Not for Figma builds/syncs, same-theme section copying, app-widget restyling, theme-settings edits, whole-store/Hydrogen migrations, or net-new pages.

```shell
# How to use:
/shopify-migrate-page-to-new-theme
Old template: @templates/page.30-days-of-wellness.json
Live URL: https://store.com/pages/<handle>   # optional — found via /sitemap.xml if omitted
New theme: C:\path\to\new-theme              # style source + where docs are written
```

---
