# Rebuy Widget Customization — Examples

## 1. Battle-tested Vue expressions

All pure Vue inside the template — the runtime compiler + `with(this)` allow arrow
functions, regex literals, ternaries, and array methods. Also useful: `v-model` for
two-way binding to Rebuy reactive props (`v-model="selected_purchase_type"`), and
`v-on:click.stop` to stop bubbling inside nested controls.

**"Has the customer selected something?"** (the spine — drives accordion-open,
checkbox-checked, body-visible):

```html
v-if="bundleProducts.some(p => !p.classification)"
```

**Checkbox toggles bundle membership both ways in one expression** (no external state):

```html
v-on:change="bundleProducts.some(p => !p.classification)
  ? handleRemovingProductFromBundle(0)
  : addProductToBundle(step.products.filter(p => p.type !== 'placeholder')[0], step, step_index)"
```

**Single-select swap** (replace the current pick, then close the dropdown):

```html
v-on:click="handleRemovingProductFromBundle(0);
            addProductToBundle(product, step, step_index);
            handleCollapsingBundleStep(step_index)"
```

**Selected/checked indicator on the currently-chosen option** (same method the default
uses for its qty stepper). Two renderings of the same boolean — a **✓ checkmark** shown
via `v-if`:

```html
<span v-if="foundStepProductInBundleHolder(product.selected_variant_id, step_index)">✓ (svg)</span>
```

…or a **radio button**: bind the class instead and let CSS draw the filled radio on the
active row:

```html
v-bind:class="{ 'is-active': foundStepProductInBundleHolder(product.selected_variant_id, step_index) }"
<!-- CSS: an absolutely-positioned circle span; .is-active → ring + centered dot -->
```

> **Hiding the underlying native input** (under either the checkmark or the radio
> rendering): Rebuy core CSS sizes form controls, so a plain `width:0;height:0` loses and
> the native box reappears as a gap. Force the hide — `!important` + 3-class specificity +
> `appearance:none` (REFERENCE §4.4).

**Admin description → bullet lines** (admin copy carries a `|` delimiter, fallback `. `):

```html
v-for="line in text(step.description).split(step.description.includes('|') ? '|' : '. ')
         .map(s => s.trim()).filter(s => s)"
```

**Trim preformatted `"15.00%"` → `"15%"`** (it's a string, not a number; keeps `"12.50%"`):

```html
v-html="String(getSubBundleSubtotalSavingPercent(products)).replace(/[.,]00(?=\s*%)/, '')"
```

**Static display copy composed around a binding — mind Vue's whitespace 'condense'.**
Rebuy renders some values raw with no label (e.g. the subscription interval is a bare
`{{ interval }}` in the default); the label is YOUR static template text:

```html
<span>Delivery every </span><span v-if="selling_plan_interval_list.length === 1" v-html="selected_interval"></span>
<select v-else v-on:change="handleSubscriptionIntervalChange($event)">…</select>
```

Two traps. Vue 2 compiles templates with whitespace `'condense'` — inter-tag whitespace
containing a newline is **deleted** — so label span and value span must share ONE source
line with the space inside the label's text node, or they render glued
("Delivery every30 Days"). And `v-if`/`v-else` elements must stay adjacent siblings —
the label goes *before* both, never between them. Composed copy is a live-QA item: the
runtime string is unknowable statically and may already contain your label.

**Reactive *local* state with NO external JS — the `$set` trick** (e.g. a free-text search box
to filter `step.products`, which Rebuy has no native binding for — it ships only faceted
tag/vendor/price filters). You can't add a reactive `data` property from a template override, and
`v-model="myVar"` on an undeclared field won't re-render (Vue 2 reactivity caveat). The escape
hatch is Vue's own `$set`, reachable in the template via `with(this)` scope. Store your state on a
Rebuy reactive object (`step`, `config`) under a namespaced key:

```html
<!-- write on input; $set makes the new key reactive AND triggers re-render -->
<input v-bind:value="step._myproj_query"
       v-on:input="$set(step, '_myproj_query', $event.target.value)"
       v-on:click.stop placeholder="Search…">

<!-- filter the v-for; guard so .toLowerCase() never runs on undefined -->
<button v-for="(product, i) in step.products"
        v-if="product.type !== 'placeholder' && (!step._myproj_query
              || (product.title || '').toLowerCase().indexOf(step._myproj_query.toLowerCase()) > -1
              || (product.body_html ? text(product.body_html).toLowerCase().indexOf(step._myproj_query.toLowerCase()) > -1 : false))">
```

Why it survives Rebuy's re-renders: `v-for="step in config.steps"` reads the array, so Vue's
`dependArray` subscribes the render watcher to each step's observer — `$set(step, …)` notifies it,
so even the first keystroke re-renders. Reset on selection with `$set(step, '_myproj_query', '')`.
Two cautions: never `v-html` the query back (XSS) — use `v-text`; and a full Rebuy teardown that
*replaces* the `step` object clears the field (acceptable for a search box).

## 2. Snippet skeleton

`snippets/rebuy-templates-<name>.liquid` — rendered from `layout/theme.liquid` head:

```liquid
{% comment %}
  Custom Rebuy template override — widget <ID> (<what it is>).
  Binding reference: .dev/rebuy-default-bundle-template.html — grep before adding any binding.
  ⚠ Admin View must stay "Collapsible" — collapse state only exists in that view.
  ⚠ No Liquid {{ }} below this line — Liquid eats them server-side; use v-text/v-html/v-bind.
{% endcomment %}

<style>
  /* All custom CSS under ONE prefix */
  .myproj-bundle { /* … */ }

  /* Scoped !important counter-rules — sibling rebuy-templates snippets leak
     unscoped !important money CSS; Rebuy core CSS colours titles brand-blue */
  .myproj-bundle .rebuy-money { color: #000 !important; font-weight: 400 !important; }
  .myproj-bundle .rebuy-money.compare-at { display: inline !important; }
  .myproj-bundle__product-title, .myproj-bundle__product-title * { color: #000 !important; }
</style>

<script type="text/template" id="rebuy-widget-WIDGET_ID">
  <div class="myproj-bundle" v-bind:id="'rebuy-widget-' + id">
    <template v-for="(step, step_index) in config.steps">
      <!-- markup here: only bindings that exist in the saved default template -->
      <span v-html="step.title"></span>
      <!-- … -->
    </template>

    <button v-if="hasBundleBuilderAddToCartButton()"
            v-bind:disabled="shouldDisableAddBundleToCart(products)"
            v-on:click="addSelectedProductsToCart()"
            v-html="buttonWidgetLabel()"></button>
  </div>
</script>
```

Integration (three places, all required):

1. `layout/theme.liquid`, before `</head>`: `{% render 'rebuy-templates-<name>' %}`
2. Target template JSON: a `custom_liquid` block containing
   `<div data-rebuy-id="WIDGET_ID" data-rebuy-shopify-product-ids="{{ product.id }}"></div>`
3. Same template JSON: Rebuy's app block for that widget set `"disabled": true`
   (else double render).

## 3. Worked example — nested-accordion single-select picker

The proof of how far composition goes: Rebuy's default Bundle Builder renders a flat,
always-visible multi-add product grid. It was rebuilt as a checkbox-gated outer
accordion containing a collapse-to-selection single-select picker — **zero new methods,
zero external JS**, purely rewiring six unmodified Rebuy methods:

| UI layer | Built from |
|---|---|
| Outer accordion (checkbox bar expands the card) | `addProductToBundle` / `handleRemovingProductFromBundle` + the `bundleProducts.some(...)` spine. Rebuy has no checkbox-gated step. |
| Inner accordion (selected-item summary ⇄ dropdown list) | The *step-collapse* machinery (`shouldRenderBundleStep` / `handleCollapsingBundleStep`) pointed at a dropdown instead of a whole step. Requires View = Collapsible. |
| Selected/checked indicator on the chosen option | `foundStepProductInBundleHolder` — the default uses it to switch button↔stepper; here it drives the active row's indicator. Render it as a **✓ checkmark** (`v-if` an icon) or a **filled radio button** (toggle an `is-active` class styled by CSS) — maiama shipped the ✓ first, then restyled to a left-side radio for Figma. |
| Single-select behaviour | remove(0) → add(new) → collapse, chained in one `v-on:click`. The default allows multi-add. |
| Free-text search inside the picker | Not a Rebuy feature (it ships faceted filters only) — composed: query stored on `step._myproj_query` via the `$set` trick (§1), the picker `v-for` filtered on `product.title` + `text(product.body_html)`, reset on selection. |

Live implementation (maiama project, widget 271897):
- `snippets/rebuy-templates-bundle.liquid` — the full template
- `.dev/rebuy-bundle-builder-documentation.md` — complete build documentation
- `.dev/rebuy-default-bundle-template.html` — the saved default template it was built against

Lesson: a UX absent from Rebuy's docs is still achievable — but only as a composition
of methods that exist in the default template. The engine doesn't know or care about
your markup; it just sees its own methods being called.
