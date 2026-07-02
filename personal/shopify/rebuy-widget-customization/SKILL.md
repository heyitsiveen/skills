---
name: rebuy-widget-customization
description: Override Rebuy (Shopify app) widget UIs by replacing their Vue 2 templates from theme snippets — custom Bundle Builder layouts, restyles, accordion/picker UIs — while keeping Rebuy's engine, discounts, and subscriptions intact. Use when working with the Rebuy app on a Shopify store - customizing or restyling a Rebuy widget, editing rebuy-templates-*.liquid snippets, debugging Rebuy discounts/selling plans, or fixing Rebuy CSS conflicts.
---

# Rebuy Widget Customization (Shopify)

Replace a Rebuy widget's entire markup with custom Vue 2 markup while Rebuy's engine
(data, methods, discounts, subscriptions) keeps running underneath. You supply the
*shape* (HTML + CSS) and the *wiring* (which Rebuy method fires on which event) — never
your own state or your own cart calls.

## The one rule

**Build ONLY against Rebuy's published default template — never from memory.**
Rebuy has NO prose API reference. The API is learned by reading their default template:
<https://developers.rebuyengine.com/reference/custom-template> (the page embeds the
complete default Bundle Builder Vue template). Fetch it, save it verbatim to
`.dev/rebuy-default-bundle-template.html`, grep it for every binding. Never invent a
method name — Vue fails **silently** on wrong names.

## How the override works

1. Rebuy's app-embed JS scans the page for mount points: `<div data-rebuy-id="WIDGET_ID">`.
2. If the DOM contains `<script type="text/template" id="rebuy-widget-WIDGET_ID">`,
   Rebuy uses its innerHTML as that widget's Vue template instead of the default.
   (`id="rebuy-bundle-builder-template"` instead targets ALL widgets of that type.)
3. `type="text/template"` is inert — safe to render site-wide from `<head>`.
4. Vue 2 runtime+compiler with `with(this)` scoping: write `bundleProducts`,
   `addProductToBundle(...)` directly, no `this.`. Arrow functions, regex literals,
   ternaries, `.split/.map/.filter` all work inside expressions.

## Workflow

### Phase 1 — Research (no code yet)
- [ ] Get the widget's numeric ID from the Rebuy admin.
- [ ] Fetch the custom-template docs page; save the full default template to `.dev/`.
      If a prior copy exists, diff to spot renamed bindings.
- [ ] From that file, enumerate the data model + every method needed (selection,
      pricing, collapse, subscription, labels, cart) **with line numbers**.
- [ ] Capture admin settings (View/layout, subscription, discount %, data source,
      metafields) — they change which methods even function.
- [ ] Read existing `snippets/rebuy-templates-*.liquid` for the include pattern and
      for leaked global CSS you must counter.

### Phase 2 — Build
- [ ] Create `snippets/rebuy-templates-<name>.liquid`: scoped `<style>` block + the
      `<script type="text/template" id="rebuy-widget-<ID>">` template.
- [ ] Obey every hard constraint below. Skeleton in [EXAMPLES.md](EXAMPLES.md).

### Phase 3 — Integrate
- [ ] `{% render 'rebuy-templates-<name>' %}` in `layout/theme.liquid` before `</head>`
      (match the existing rebuy-templates include block).
- [ ] Ensure `<div data-rebuy-id="<ID>" data-rebuy-shopify-product-ids="{{ product.id }}">`
      exists on the target template (custom_liquid block in the section JSON).
- [ ] **Disable Rebuy's app block for the same widget** — otherwise it double-renders.

### Phase 4 — Verify (adversarial: assume broken)
- [ ] Grep the saved default template for every binding used — all must exist there.
      Novel UX is fine, but only as *compositions* of existing methods.
- [ ] Live QA: widget renders; discount applies on cart-add; selling plan attaches;
      UI survives Rebuy re-renders; mobile; out-of-stock option; no console errors.
- [ ] Report admin-setting changes (labels, default purchase type, metafields, **CTA mode** —
      add-to-cart vs accelerated-checkout is admin-gated; the add-to-cart + open-cart-drawer
      recipe is REFERENCE §5, incl. which drawer actually opens — Smart Cart vs theme) separately
      from code — half the design usually lives in admin.

## Hard constraints (each one a paid-for bug)

1. **Only binding names found in the saved default template.** Can't find it → say so,
   don't improvise.
2. **Liquid eats `{{ }}` server-side.** The default template is full of Vue `{{ }}` —
   pasted into a `.liquid` snippet they vanish before the browser sees them. Convert
   every `{{ x }}` to `v-text`/`v-html` (text) or `v-bind:` (attrs), or wrap the whole
   template in `{% raw %} … {% endraw %}`.
3. **Never gate the root on `products.length`.** Top-level `products[]` is EMPTY for a
   Bundle Builder (items live in `config.steps[].products`) — gating it hides the
   entire widget.
4. **Route every cart-add through Rebuy's own methods** (`addSelectedProductsToCart()`
   / `addSelectedProductsToCheckout()`). The discount is a Rebuy Shopify Function keyed
   off line-item properties (`_source: "Rebuy"`, `_attribution`, `_widget_id`) injected
   only by those methods. A hand-rolled `/cart/add` silently kills the discount.
5. **Zero external JavaScript.** Derive all UI state from Rebuy's reactive data
   (e.g. accordion-open ⟺ `bundleProducts.some(p => !p.classification)`). Rebuy
   re-renders wipe any external-JS state; reading their data means nothing to re-sync.
   State Rebuy doesn't hold (a search query, a UI toggle): `$set` it onto a Rebuy
   reactive object — the `$set` trick in [EXAMPLES.md](EXAMPLES.md) §1 — never real JS.
6. **Scope ALL CSS under one unique prefix** and add scoped, **higher-specificity**
   `!important` counter-rules. Styles leak in from three places, **none in your file**:
   sibling rebuy-templates snippets leak unscoped `!important` money CSS site-wide; Rebuy's
   core stylesheet colours titles brand-blue **and imposes box metrics via the shared
   `.rebuy-*` classes** (sizes form controls, pads the root ~30px); and the **host theme**
   leaks **inherited** properties (a centered theme block gave every text node
   `text-align:center`, drifting short titles off the left edge). So when a style won't take,
   **inspect the live widget**, don't hunt in your snippet. Fix by mechanism: a rule that
   *matches* your element → out-*specify* it (`!important` alone only ties Rebuy's
   `!important`); an *inherited* value (no matching rule) → set it explicitly **once at your
   widget root** and let it cascade. Detail: REFERENCE §4.4.
7. **The admin View setting is load-bearing.** Step-collapse state
   (`shouldRenderBundleStep` / `handleCollapsingBundleStep`) only exists in
   **Collapsible** view; in Default view it's always-true/no-op. Name the required
   View in the snippet's comment header.
8. **Exact spellings matter** — e.g. `hasBundleBuilderAccelerateCheckout()` (no "d").
   Copy-paste names from the saved template, never retype.

## Going deeper

- [REFERENCE.md](REFERENCE.md) — data model, full method glossary, load-bearing
  gotchas in detail, admin-settings interplay, vendor-update maintenance loop.
- [EXAMPLES.md](EXAMPLES.md) — battle-tested Vue expressions, snippet skeleton, and
  the worked example (nested-accordion bundle picker built from six unmodified
  Rebuy methods).
