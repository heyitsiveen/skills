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