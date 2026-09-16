# Browser mode — capture and write through the bulk editor

Reached from Phase 3 and Phase 4 of `SKILL.md` when the store has no Matrixify.

Both the Backup capture and the write go through the admin's **bulk editor**, not through product pages. A product page shows each metafield as a collapsed button whose preview truncates, so reading 300 values there means opening 300 editors. The bulk editor handles fifty products at a time and takes both rich text and list metafields.

Every mechanic below was established by doing it. Where one exists only because something silently misbehaves, the reason is stated — those are the ones not to optimise away.

## Opening the grid

1. Products list → select the **page** → **Bulk edit**. Store-wide "select all" does not carry into the bulk editor. Fifty at a time.
2. **Columns** → clear every default column, then check only the mapped metafields **and `URL handle (SEO)`**.
3. Widen the handle column; narrow the title column.

The handle column is not optional. Two products can share a title, and the grid is positional — the handle is the only thing tying a row to the product it belongs to.

## Settling the grid before touching it

The grid lazy-loads and arrives with every product's variants expanded, so row positions do not correspond to products until they are collapsed.

Collapse by clicking every `button[aria-expanded="true"]` except those labelled `Columns` or starting with `Status`. Scroll down, collapse again, and repeat until the header count stops rising.

**Work strictly top-down from then on.** Collapse state resets when virtualised rows recycle, so scrolling back up mid-pass silently re-expands what was collapsed and every row position below moves.

**If the browser window changes size mid-pass, stop.** Re-derive every row position before continuing. A resize shifts the whole grid, and the write lands on the wrong product with no error.

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
