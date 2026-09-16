# Browser mode — capture and write through the bulk editor

Reached from Phase 3 and Phase 4 of `SKILL.md` when the store has no Matrixify.

Both the Backup capture and the write go through the admin's **bulk editor**, not through product pages. A product page shows each metafield as a collapsed button whose preview truncates, so reading 300 values there means opening 300 editors. The bulk editor handles fifty products at a time and takes both rich text and list metafields.

Every mechanic below was established by doing it. Where one exists only because something silently misbehaves, the reason is stated — those are the ones not to optimise away.

## Pin the order before anything else

The product list's default sort is **`Created` / `Newest first`**. The sort control is not a button of its own — it lives in the list-settings popover behind the columns icon at the right of the search-and-filter bar.

Skip the UI. **The sort is settable directly in the URL**, and that is what to use:

```
/store/<store>/products?order=title+asc
```

The parameter is `order`, the value `<field> <asc|desc>`, the space encoding as `+`. Observed field keys: `title`, `inventory_total`, `product_type`, `vendor`, `created_at`, `updated_at`, `publishing_error`.

**Use `title+asc`. Never `updated_at`.** Saving a batch of metafields changes each product's updated time, so a list sorted that way **reorders itself underneath the pass** — the same corruption as a mid-pass window resize, from a cause that looks like nothing happening. A title sort is unaffected by anything this skill writes.

## Opening the grid

1. Products list at the pinned sort → select the page → **Bulk edit**. Fifty at a time.
2. **Columns** → the `SEO` group holds `URL handle (SEO)`. Tick it. Default columns are five, and `Product title` cannot be unticked.
3. Widen the handle column; narrow the title column.

**The sort carries into the bulk editor, and its URL carries it too.** The bulk-edit URL holds both `order=` and an `ids=` list — and `ids=` is in *selection* order, not display order, so `order` is what actually drives the rows. Changing `order=title+desc` by hand reverses the grid, which means the row order is deterministic and settable rather than something to be discovered.

Ticking the handle column appends `handle` to the `edit=` parameter, so the whole grid can be opened in one known state.

The header counts up as rows load — "Editing 15 products" then "Editing 18 products". **Wait for it to stop rising** before reading anything.

## Never count rows. Read the handle.

**A grid row is not a product.** A product with variants expands into extra rows — one real product with 260 variants becomes 260 extra rows — and on every one of those the product-level fields, including the handle, are **blank**.

So row position and product position are different numbers, and the difference is invisible unless you look for it.

The rule that follows is short: **identify every row by the handle in its handle column.** A row with a blank handle is a variant row; skip it. A row whose handle is not in the write plan is a product the sheet does not cover; leave it completely alone.

Collapsing variants is still worth doing — fewer rows, less scrolling. Click every `button[aria-expanded="true"]` except those labelled `Columns` or starting with `Status`, scroll, repeat until the header count settles. But collapsing is an optimisation, not the safety mechanism. The handle is the safety mechanism.

**Work strictly top-down.** Collapse state resets when virtualised rows recycle, so scrolling back up mid-pass silently re-expands what was collapsed.

**If the browser window changes size mid-pass, stop** and re-read the grid before continuing.

## Matching the sheet to the grid

The sheet's order and the admin's order have no reason to agree, and nothing is ever written by sheet position.

```sh
python3 scripts/convert.py match --converted <converted.json> --admin <admin-handles.json>
```

`admin-handles.json` is the list of product handles in admin list order, read off the pinned-sort product list. The plan comes back per page: which handles to write, which fields each needs, and where each sits in the **product list** — `list_position`, a number for a human to sanity-check against, never a grid row to count to.

It fails when a sheet handle is not in the admin at all, naming each one, rather than quietly updating 51 of 52.

`untouched_admin_products` says how many products the sheet does not cover. Those are never opened.

## Selection

The header checkbox selects the page, and the dropdown then offers `Select all N on page` and `Unselect all`. No store-wide "select all across your store" affordance was found on a single-page store, and page size is not URL-settable — `limit` is ignored. **On a store with more than fifty products this is unconfirmed**; check what the selection dropdown offers before assuming a whole catalogue can be taken in one go.

## Capturing the Backup

Same grid, one pass, before any write. For each mapped field of each product in view, open the value and read it in full — the collapsed preview truncates, so it cannot be the source.

Record one entry per product per field:

```json
{"handle": "blonde", "key": "custom.revamp_details",
 "type": "rich_text_field", "value": "<ul><li>Best for: Espresso</li></ul>"}
```

A field holding nothing is recorded with `"value": null`, never `""`. That distinction is what lets an Undo delete rather than blank.

Hand the captured entries to `convert.py backup-write`. The capture pass finishes completely before the first write begins.

## Writing a rich-text metafield

Put both clipboard flavours in place first, from the Converted value:

```js
await navigator.clipboard.write([new ClipboardItem({
  'text/html':  new Blob([html],  {type: 'text/html'}),
  'text/plain': new Blob([plain], {type: 'text/plain'})
})]);
```

Then, per cell:

1. Click the cell, press `Return` to open the editor, and wait about 2 seconds.
2. Focus the editor **with JavaScript**, not with a click:
   ```js
   document.querySelector('[contenteditable="true"]').focus()
   ```
   The popover anchors above, below or to the left depending on the space available, so a coordinate click misses and dismisses it.
3. Select the existing content and confirm the field is empty before pasting. `cmd+a` intermittently does nothing at all, and a paste onto a non-empty field appends rather than replaces. Where `cmd+a` fails, use the editor's own `Clear` link or a Selection API range.
4. Paste, then `Escape`.

A rendered `<ul><li>…</li></ul>` round-trips byte-exactly this way — re-pasting the same content over a saved value greys out the Save button, which is the app confirming the match.

Save every twenty products or so. A large unsaved session turns one dropped batch into a lost pass.

**Saving an empty editor deletes the metafield.** It fires `DeleteTheseMetafields`, with no value in the payload. That is the mechanism an Undo uses deliberately; during a write it is the accident to avoid.

## Writing a list metafield

Values are separate rows, each a plain `<input type="text">`.

**The add control is invisible to an ordinary query.** Shopify admin uses web components, so `querySelectorAll('button')` does not find it. Locate it by scanning for an element with no children whose text is exactly `Add item`.

**Never type into these fields.** Focus stays on `Add item` after it is clicked, so every space character in typed text presses it again — one run produced nine phantom empty rows this way. Pasting newline-separated text is no better: an `<input>` collapses the newlines and produces one value, not three.

Set values directly instead:

```js
const setter = Object.getOwnPropertyDescriptor(
  HTMLInputElement.prototype, 'value').set;
setter.call(input, value);
input.dispatchEvent(new Event('input',  {bubbles: true}));
input.dispatchEvent(new Event('change', {bubbles: true}));
```

Order matters: click `Add item` as many times as the value count needs **first**, then set every value, then read the inputs back to confirm the count and the order. A phantom row caught in the same pass costs nothing; one discovered later costs a re-run.

## The editor's ceiling, for reference

Six controls, and that is all: a Paragraph dropdown (Paragraph, Heading 1–6), Bold, Italic, Insert link, Unordered List, Ordered List. No underline, no source view, no table, no alignment.

`cmd+B` toggles bold. There is no markdown autoformatting — `- `, `* `, `# ` and `1. ` all stay literal. `Return` makes a new block; inside a list, a new item. `shift+Return` makes a soft break inside the current item, which is rarely what is wanted.

The product **Description** editor on the same page is a different and much richer component, with a `</>` source view. None of that is available on a metafield.
