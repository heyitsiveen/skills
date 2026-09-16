# Metaobject mode — walking the chain to where the text actually lives

Reached from Phase 3, 4 and 5 of `SKILL.md` whenever a Mapping target carries a `path`.

A metaobject reference metafield holds no text. It points at an **entry**, and the entry's own fields hold the words — sometimes after another hop. So the write is not "set a metafield"; it is "walk to a leaf field and set that".

There is **no bulk editor for metaobject entries**. The entries list's entire bulk menu is one Delete button. Every entry is opened and saved one at a time, which makes this the most expensive part of any Run — 155 entry saves on the first real catalogue, for 52 products.

## The chain, drawn

```
product page
 └─ chip: Product Tabs ──────────► popover (shows the linked entry, plus Change / Clear)
     └─ click the entry ─────────► modal — type: Product Tabs
         ├─ row: Details ────────► modal — type: Product Details   → field Content (rich text)
         └─ row: Materials ──────► modal — type: Product Materials → field Content (rich text)

product page
 └─ chip: Testimonial ──────────► popover
     └─ click the entry ────────► modal — type: Testimonial
                                   fields: Quote (rich text) + Author (single line text)
```

The Mapping's `path` is this drawing in data. Its last step names the leaf — the definition and the field that actually receives the value:

```json
"path": [{"definition": "product_tabs",    "field": "details"},
         {"definition": "product_details", "field": "content",
          "type": "rich_text_field"}]
```

`Product Tabs` itself holds no copy at all. Writing into it is always wrong.

## Finding the product

There is no grid here, so the route is per product:

1. Take the handle from the row — resolved by visiting, per Phase 1.
2. Navigate to `/products?query=<handle>`.
3. **Shopify's search is fuzzy and often returns several products.** Open the one whose title best matches the sheet's product name.
4. **Confirm before touching anything:** `find` the "Search engine listing URL" and check the displayed handle equals the sheet's. A custom storefront domain differing from the store slug is normal and is not a mismatch.
5. Still ambiguous → stop and ask. Never choose between two similar products.

Allow 5–8 seconds after navigating; the admin renders skeleton placeholders first. Settings pages take longer — 15–25 seconds — and `get_page_text` returns nothing on them, so read `document.body.innerText` instead.

Reach the metafield card with `find` for `Edit <name> metafield` and scroll to the returned ref. Do not scroll blindly: in a narrow window Shopify stacks to one column and the card is not at the bottom of the page.

## Two traps that open the wrong entry

**Rows render as raw GIDs before their labels resolve.** A reference row shows `gid://shopify/Metaobject/216706187335` for a moment, then becomes a label. **Row positions shift as the labels load.** Clicking while a row still shows a GID opens a different entry than the one you aimed at. Wait for the labels, or close and reopen the modal.

**Modals stack, and the Close button moves.** Opening an inner modal changes the outer Close button's position. Re-screenshot immediately before every Close click, and never reuse a coordinate across steps. Close inner before outer, then confirm you are back on the product page.

## Never Clear, never Change

Both buttons sit on the reference row and neither edits the entry. `Clear` unlinks the reference. `Change` re-points it at a different entry. The goal is always to edit the content of the entry already linked, so neither is ever the right button.

## Writing into the editor

The rich-text field in an entry is a **Slate `contenteditable`**, not a textarea.

**JavaScript cannot write it.** Setting `innerHTML`, or dispatching synthetic input events, does not update Slate's internal state: the change appears on screen and then saves as empty or corrupt. This is the single most expensive mistake available here, because it looks like it worked.

Write by clipboard, as in `browser-mode.md`:

```js
await navigator.clipboard.write([new ClipboardItem({
  'text/html':  new Blob([html],  {type: 'text/html'}),
  'text/plain': new Blob([plain], {type: 'text/plain'})
})]);
```

then click into the editor, select all, confirm it is empty, and paste.

Keyboard fallback, when the clipboard is unavailable: click the unordered-list button to start a list, type each item and press Enter, and press Enter on an empty item to leave the list. `shift+Enter` makes a soft break inside a paragraph. `cmd+B` toggles bold — never `ctrl+B`.

**Never type the `•` character.** The editor generates its own bullet, so a typed one renders doubled. The converter already strips the glyph from the source; do not put it back.

Save the entry from inside its own modal before closing it.

## Before writing any entry, check it is not shared

Shopify's own description of metaobjects is that one entry can be referenced by many products, and updating it updates all of them. That is the feature. It is also, for a per-product Run, the way to damage products that are not in the sheet.

The entries list carries a **References** column, and every entry page shows a References card naming what points at it.

**Require References == 1 before writing.** On the first real catalogue every `product_tabs`, `product_details`, `product_materials` and `testimonial` entry had exactly one reference — but the same store's `features_highlight` has **one entry referenced by 40+ products**. Nothing in the schema prevents the same arrangement appearing in a definition this Run does write to.

An entry with more than one reference is reported and skipped, never written.

## When a product has no entry

Create a new entry and link it. **Never re-point the field at an entry belonging to another product** — that silently makes two products share one entry, which is the failure above, caused by the fix.

This is a deliberate exception to the skill's refusal to create things. A metafield *definition* is schema, and creating one changes what an Undo means. An *entry* is content: a product with no entry has nothing to overwrite, so creating one is additive, and undoing it means deleting what the Run made.

This case is live — one product on the first real catalogue has all five metaobject fields empty.

## Backup and Undo

Matrixify is **not** available for this half. Its metaobject export may or may not emit a row for an empty field, and nobody has written down which; if it omits the row, a replay cannot remove a field the Run created, and it reports success while doing nothing. See ADR-0006 and section 16 of the findings.

So metaobject entries are backed up the way Browser mode backs up metafields: **a capture pass through the same editor the write uses.** Open each entry, read each mapped field in full, record it. The symmetry argument holds exactly as it does for metafields — if the browser can write the value, it can write the prior value back, and whatever fidelity the write path has, the restore path has the same.

Record one entry per product per leaf field:

```json
{"handle": "leather-bag", "key": "custom.product_tabs",
 "path": [{"definition": "product_tabs", "field": "details"},
          {"definition": "product_details", "field": "content"}],
 "value": "<p>Features</p><ul><li>Top zipper</li></ul>"}
```

A field holding nothing is recorded as `null`, and an entry the Run *created* is recorded as having not existed, so the Undo deletes it rather than blanking it.

## Cost, and reading it back

`convert.py` reports the cost before anything is written:

```
entry saves: 155  {"product_details": 52, "product_materials": 52, "testimonial": 51}
```

Two fields of one entry — a split `quote` and `author` — are one save, not two.

Verification reads the rendered storefront, as in Phase 5. The entry editor's own display is not evidence: the same reasons that make the admin unreliable for metafields apply here, and a Slate editor that silently refused a write looks identical to one that accepted it.
