# Rebuy Widget Customization — Reference

Everything here was verified against Rebuy's published default Bundle Builder template
and Rebuy's decompiled production JS (`ViewBundleBuilder.js`, cdn.rebuyengine.com).
When in doubt, the saved default template in `.dev/` outranks this file — re-grep it.

## 1. Sources of truth (in order)

1. **The default template** embedded at
   <https://developers.rebuyengine.com/reference/custom-template> — the complete
   (~1,179-line) Vue template, and the only enumeration of methods/data that exists.
   The same page documents per-widget vs per-type targeting and recommends the
   snippet-rendered-from-theme integration.
2. **Decompiled production JS** — only when a method's *behaviour* is ambiguous from
   its name (this is how the View-dependent collapse behaviour below was confirmed).
3. There is **no prose API reference**. A method not in the template does not exist.

## 2. Data model (Bundle Builder)

| Data | Meaning |
|---|---|
| `id` | this widget instance's id (use for unique element ids) |
| `products` (top-level) | **EMPTY for Bundle Builder** — never gate on it. Price methods still take it as an argument by signature. |
| `config.steps` | array of bundle steps — iterate this |
| `step.products` | the selectable products for a step |
| `step.title` / `step.description` | admin-controlled copy |
| `product.type === 'placeholder'` | an empty/filler option — skip in pickers |
| `product.selected_variant` / `.selected_variant_id` | the variant to add/compare |
| `bundleProducts` | the chosen items. Entry is a **placeholder** (`classification === 'placeholder'`) or a **real selection** (falsy `classification`) |
| `selected_purchase_type` | `'subscription'` \| `'one-time'` — exact strings; `v-model`-able |
| `selected_interval` / `selling_plan_interval_list` | subscription delivery interval — the default renders it **raw** (bare `{{ interval }}`, no label text); display copy like "Delivery every …" must be composed as static template text around the binding (whitespace caution: EXAMPLES.md §1) |

Spine expression: `bundleProducts.some(p => !p.classification)` ⟺ "customer has made
a real selection" — drives accordion-open, checkbox-checked, etc.

## 3. Method glossary

Exact spelling matters — Vue fails silently on a wrong name.

**Bundle structure & selection**
- `addProductToBundle(product, step, step_index)` — add an item.
- `handleRemovingProductFromBundle(index)` — remove by index into `bundleProducts`.
- `foundStepProductInBundleHolder(selected_variant_id, step_index)` — is this variant
  currently chosen for the step (default uses it for button-vs-stepper; works equally
  as a selected/checked indicator — a ✓ checkmark via `v-if`, or a radio button via a
  toggled `is-active` class; see EXAMPLES.md §1 for both renderings).
- `variantAvailable(variant)` — purchasable / in stock.
- `showVariantTitle(product)` — show the variant subtitle?

**Collapse / step rendering** *(Collapsible View only — see §4.1)*
- `shouldRenderBundleStep(step_index)` — should the step body render.
- `handleCollapsingBundleStep(step_index)` — toggle the step's collapse state.
- `isBundleBuilderCollapsibleLayout()` — admin View == "Collapsible".

**Pricing** *(all take `products` as arg by signature, even though it's empty)*
- `getBundleSubtotal(products)` — plain subtotal.
- `getBundleDiscountedSubtotal(products)` — one-time discounted subtotal.
- `getSubBundleDiscountedSubtotal(products)` — subscription discounted subtotal.
- `getSubBundleSubtotalSavingPercent(products)` — **preformatted string** like
  `"15.00%"`, not a number.
- `bundleHasEligibleDiscount(products)` — discount in effect?
- `bundleVariantPrice(product, variant)` / `bundleVariantCompareAtPrice(product, variant)`
- `bundleVariantOnSale(product, variant, true)` — 3rd boolean = "holder context"
  (selected-item card), so the on-sale check matches the chosen variant.
- `formatMoney(cents)` — store money format.
- `shouldDisableAddBundleToCart(products)` — disable the CTA.

**Subscription**
- `hasSelectedEnabledBundleSubscription()` — show purchase-type radios at all.
- `hasSellingPlansIntervalList()` — selling-plan intervals exist (gates the radio).
- `hasBundleBuilderSubscriptionOnlyEnabled()` — hide the one-time option.
- `handleSubscriptionIntervalChange($event)` — apply interval change.

**Filtering & sorting** *(faceted ONLY — Rebuy has NO free-text product search)*
- `hasBundleFiltering()` / `hasBundleBuilderSorting()` — the admin-gated panels exist at all.
- `toggleBundleFilterSection()` + `is_filter_visible` (data) — open/close the filter panel.
- `mapped_aggregated_filters` (data) — the facet groups to render (empty → no filters).
- `handleBundleFilterUpdate('product-tags' | 'vendor' | 'availability' | 'product-type', value)`
- `handleBundlePriceFilterChange('min' | 'max', $event)`
- `hasBundleFiltersActive()` / `getSelectedBundleFilterItems()` / `clearBundleFilters()`
- `selected_sorting_option` — `v-model`-able sort choice.
- A free-text search must be **composed**: store the query with the `$set` trick
  (EXAMPLES.md §1) and filter the picker `v-for` on `product.title` +
  `text(product.body_html)`.

**Labels / copy**
- `getBundleConfigLabel('switch_to_subscription_title' | 'switch_to_subscription_description' | 'save_label' | 'one_time_title' | 'one_time_description')`
- `buttonWidgetLabel()` — add-to-cart label.
- `getBundleBuilderCTAButtonLabel('checkout')` — accelerated-checkout label.

**CTA**
- `hasBundleBuilderAddToCartButton()` — render the ATC button?
- `hasBundleBuilderAccelerateCheckout()` — render accelerated checkout?
  *(spelling: "Accelerate", no "d")*
- `addSelectedProductsToCart()` — THE cart add; carries the discount (§4.3).
- `addSelectedProductsToCheckout()` — straight to checkout with the bundle.

**Misc**
- `itemImage(product, variant, '200x200')` — image URL at size.
- `text(html)` — sanitize/extract text from an HTML string.

## 4. Load-bearing gotchas

1. **Admin View dictates collapse behaviour** (confirmed in decompiled JS):
   - Tabs → `shouldRenderBundleStep` returns `active_step_index === i`
   - **Collapsible → returns `steps_expanded_map[i]`** (the only stateful one)
   - Default → returns unconditional `true`; `handleCollapsingBundleStep` is a no-op.
   Any open/close UX built on these requires **View = Collapsible**; otherwise the
   panel is permanently open and the toggle dead.
2. **`products.length` gating hides the whole widget** (top-level array empty — §2).
3. **Discount mechanism**: a Rebuy-generated **Shopify Function** matches line-item
   properties (`_source: "Rebuy"`, `_attribution`, `_widget_id`) that only Rebuy's own
   add-to-cart methods inject. Custom `/cart/add` → properties missing → no discount,
   no attribution, possibly no selling plan.
4. **CSS leaks both ways**:
   - Other rebuy-templates snippets may ship **unscoped** `!important` rules site-wide
     (e.g. `.rebuy-money{color:#535353!important}`,
     `.rebuy-money.compare-at{display:none!important}`). Counter with *scoped*
     `!important` rules under your prefix — specificity wins.
   - Rebuy's core stylesheet colours product titles brand-blue; force your title
     classes to the design colour with scoped `!important`.
   - Rebuy core CSS also **sizes native form controls**. If you hide the real
     `<input type="checkbox">`/radio to style a sibling span (EXAMPLES §1, §3), a plain
     `width:0;height:0` **loses** and the native box reappears (~18px) as a gap beside your
     custom control. Force the hide three ways at once: `!important`, a higher-specificity
     selector (beat Rebuy's `.rebuy-widget input[type="checkbox"]` — ~2-class+tag — with
     **3 classes**), and `appearance:none` (strip the native widget so the zero size
     actually sticks); `position:absolute` as a flow backstop. (Hit on maiama widget
     271897's bar checkbox — symptom was a white gap on the left of the collapsed bar.)
   - Rebuy core CSS also **pads the widget ROOT** (~30px top/bottom, via `.rebuy-widget` /
     `.rebuy-bundle-builder`). Your override sets none, so it is **invisible in your snippet** —
     don't hunt for the rule there. In DevTools it shows as green padding bands wrapping the
     *entire* widget on `#rebuy-widget-<id>`. Zero it by stacking the root's own classes:
     `.<prefix>.rebuy-widget.rebuy-bundle-builder { padding-top:0 !important; padding-bottom:0
     !important }` (3 classes + `!important` beats Rebuy's 1-class rule). Set only the sides you
     mean (top/bottom), not the `padding` shorthand, so any horizontal padding survives. (Hit on
     maiama 271897 — symptom was a ~30px gap above and below the whole widget.)
   - The **host theme** (not Rebuy) can leak **inherited** properties in. On maiama the widget
     sits inside a centered theme block, so `text-align: center` inherited into every text
     node; the short non-flex spans (product title, the `__choice-title` "Abo & Sparen") drifted
     right off the left edge, while their flex-row siblings (price, check-/bullet-lists) stayed
     put — `text-align` doesn't move flex items, `justify-content` does. Because it's *inherited*,
     **no rule matches your element**, so out-specifying has nothing to target: set an explicit
     value **once at the widget root** (`.<prefix> { text-align:left }`) and the whole subtree
     inherits it; elements that truly want centering set their own. Tell: a style hits some text
     but not the *adjacent* text and the unaffected ones are flex containers → it's inherited from
     an ancestor (the theme), not Rebuy. (Hit on maiama 271897 — two titles didn't line up with
     the text below them.)
5. **`getSubBundleSubtotalSavingPercent` returns `"15.00%"` (string)**. Trim whole-number
   decimals with `String(...).replace(/[.,]00(?=\s*%)/, '')`; leave `"12.50%"` intact.
6. **Placeholders are real entries.** `bundleProducts` pre-fills with
   `classification: 'placeholder'` slots; `step.products` can contain
   `type === 'placeholder'` items. Filter both in pickers and counts.

## 5. Admin settings that interact with code

- **View** (Default/Tabs/Collapsible) — load-bearing, see §4.1.
- **Switch To Subscription** + its title/description labels — gates the radios and
  feeds `getBundleConfigLabel`.
- **Step descriptions** — a delimiter convention (e.g. `|`) lets the template split
  admin copy into bullet lines; document the convention for the client.
- **Accelerated Checkout + "Remove Add to Cart Button" — the CTA recipe.** These two
  admin toggles (not code) decide which CTA your template renders, gated by
  `hasBundleBuilderAddToCartButton()` / `hasBundleBuilderAccelerateCheckout()`:
  - **Goal "add to cart + open the cart drawer" (the usual ask):**
    **uncheck "Remove Add to Cart Button"** (→ the ATC button renders, calls
    `addSelectedProductsToCart()`, carries the discount) **and** turn **"Accelerated
    Checkout" OFF** (→ the `addSelectedProductsToCheckout()` button, which jumps straight
    to checkout, does not render). One button: adds the discounted bundle, stays on page.
  - **Broken combos:** Remove-ATC *checked* + Accelerated *on* → only the checkout-redirect
    button (mislabelled "add to cart"); Remove-ATC *checked* + Accelerated *off* → no CTA at all.
  - **Which drawer opens depends on Rebuy Smart Cart — verify live, don't assume.** If the store
    runs **Smart Cart** (tell-tale: `<body class="… smart-cart--enabled">`), Rebuy intercepts every
    cart-add and opens **its own** flyout `.rebuy-cart__flyout` (its root `.rebuy-cart` flips
    `aria-hidden:true→false` + class `is-visible`; `<body>` gains `rebuy-cart-visible`) — the host
    theme's drawer stays shut. So you need **no bridge** (verified on maiama 271897, where the client
    *assumed* it was the theme drawer but it's Smart Cart's). Confirm which drawer actually moves
    (watch the panel's transform/`aria-hidden`) before documenting it — two drawers can coexist and
    the theme one is easily mistaken for the opener.
  - **If Smart Cart is OFF**, the add may not auto-open anything and you might need to bridge to the
    theme drawer — but beware the theme may gate its open behind a **private in-bundle event bus**
    (maiama: `theme.js` internal `r$1`/`c` emitter), unreachable by a DOM
    `CustomEvent('quick-cart:open')`; the DOM-reachable app hook (e.g. `apps:product-added-to-cart`)
    typically only *refreshes*. Bridge = fire that refresh hook + click the header cart toggle to
    open. **Never** hand-roll `/cart/add` (strips the discount props — §4.3).
- **Metafields toggle on the data source** — off means descriptions fall back to
  clamped `body_html`.
- **Bundle min/max, Subtotal Discounted From, discount %** — shape pricing methods'
  outputs.

## 6. Support & maintenance

- **Rebuy excludes custom templates/CSS/JS from support.** Anything broken after a
  Rebuy update is yours to fix.
- **Vendor-update loop** (run when Rebuy ships template changes or the widget breaks):
  1. Re-fetch the default template; overwrite the `.dev/` copy.
  2. Diff against the previous copy — renamed/removed methods and data.
  3. Grep your override snippet(s) for every changed binding; update.
  4. Re-run Phase 4 verification before deploying.
- Keep overrides **dependency-free**: if you're adding real JS to "fix" state, you've
  stopped reading Rebuy's reactive data — go back to deriving from it.
