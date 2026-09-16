# The Claude-in-Chrome prompt

`sheet-to-shopify-metafields` runs in Claude Code, where `scripts/convert.py` does the conversion and the Backup lands on disk. Claude in Chrome has neither a filesystem nor Python, so the skill cannot run there.

This file holds a self-contained prompt for Chrome instead. Copy the fenced block below and paste it, filling in the four inputs at the top.

**It is weaker than the skill, in two ways worth knowing before you use it.**

The converter is ported to in-page JavaScript, so the same conversion rule now lives in two places and the copies can drift. The prompt makes the port prove itself: it carries the same fixtures as `test_convert.py` and runs them as a self-check before touching any product, stopping if one fails. `scripts/convert.py` remains authoritative — **when the conversion rule changes there, change the JavaScript here to match, and the fixtures with it.**

And there is nowhere to put a Backup. In Matrixify mode this costs nothing: the export lives in Matrixify's own All Jobs list. In Browser mode the agent prints the captured values and **you** save them. A Backup nobody saved is not a Backup.

Prefer Matrixify mode in Chrome for exactly that reason.

````
**Task: push product copy from a Google Sheet into Shopify product metafields, through the browser.**

Sheet: <sheet URL, including the tab>
Store: <admin URL>
Mapping: <sheet column → metafield name and type, one per line>
Matrixify installed: <true / false — if you do not know, ask me before doing anything>

Hard constraint: no Shopify API. No Admin API, no Storefront API, no GraphQL, no Shopify CLI. The Shopify admin and the storefront in this browser, and nothing else.

Work through the phases in order. Phases 1 and 2 write nothing anywhere. Stop where the phase says stop.

---

## Why this is careful

Shopify's rich-text metafield editor keeps only what maps onto its seven node types — root, paragraph, text, heading, link, list, list-item — and discards everything else **including the whitespace around what it discarded**.

Paste `<dl><dt>Best for</dt><dd>Espresso</dd></dl>` in and you get:

    Best forEspresso

No separator. It saves without an error. The admin's collapsed preview flattens a list onto one line anyway, so the admin looks identical whether the value is right or ruined. Only the storefront tells them apart, and the pairing cannot be recovered.

Metafields have no version history and no undo. Assume every target field already holds copy that matters.

---

## Phase 1 — Pre-flight. Write nothing.

**Read the sheet through the clipboard, as HTML.** Do not fetch it and do not use an export URL: a fetched read garbles the copy and miscounts rows, and an export URL starts a download you cannot read.

Select the range in Sheets using the Name Box, press cmd+C, then from a tab on the Shopify admin origin run:

```js
const items = await navigator.clipboard.read();
const html = await (await items[0].getType('text/html')).text();
html.length
```

**Take `text/html`, not `text/plain`.** A sheet's hyperlinks exist only as cell formatting — the plain flavour gives you the anchor text and silently drops every href. One real sheet carries 59 of them. Shopify rich text has a link node, so they survive, but only if your read sees them. The HTML flavour also makes line breaks and cell boundaries unambiguous, so there is no quote-aware TSV parsing to get wrong.

Parse it as a table. Each `<td>` is a cell: keep `<a href>` as it stands, turn `<br>` into a newline, and leave everything else as text.

Confirm the row count independently: in the sheet, press cmd+Down from A1 and read the Name Box. Report the number you parsed and the number the sheet says. If they disagree, stop and tell me.

If the sheet URL walls you with "Verify it's you", it is resolving against the wrong Google account. Use the `/spreadsheets/u/0/d/…` form — that is profile selection, not a login.

**If the sheet has no handle column, resolve the handles by visiting.**

The last path segment of a product URL is normally the handle, so deriving it usually works. But **a renamed product keeps its old URL working and redirects to the new handle.** The derived guess is then stale — it finds nothing, or it finds a different product and you write this row's copy onto it.

So for each distinct product URL in the sheet, open it and record two things:

- the **final URL after redirects** — its last path segment is the real handle
- the **exact product title** on the page

Report every row where the derived handle and the real one disagree, and stop if any URL does not resolve to a product. Keep the titles: Shopify's admin search works on titles, and the title is the human check that a row reached the product it was meant for.

Do not write anything against a handle you have not confirmed this way.

**Report before going further:**
- the exact header row, verbatim
- the row count
- any mapped column whose header differs from what my Mapping called it — flag it loudly, a suffix like `(HTML)` changes everything
- which mapped cells are empty
- duplicate handles
- every distinct HTML tag present in the mapped columns
- the contents of any notes, QA or "needs input" column — **read it even if my Mapping says to ignore that column.** Ignoring a column means not mapping it; its contents still bear on whether this is safe to run.

**Then inspect the store.** Open Settings → Custom data → Products — the path is singular, `/settings/custom_data/product/metafields`. Record each mapped metafield's real key and type. A display name and its key often disagree: one store has "Revamp Product Benefits" living at `custom.product_benefits`, with no `revamp` in it.

Stop and tell me if a mapped metafield does not exist. Do not create it.

Open one product and tell me how many of the target fields already hold values, so we both know whether this is a fill or an overwrite.

---

## Phase 2 — Conversion. Still writing nothing.

Run this in the page. It converts, and it checks itself first. **If the self-check fails, stop and show me — do not continue.**

```js
const BLOCK = ['dl','dt','dd','p','ul','ol','li'];
const KNOWN = new Set([...BLOCK, 'strong','b','em','i','a']);
// Real HTML elements this cannot represent. Tag-shaped text naming one of
// these stops the run. Tag-shaped text naming nothing here is prose.
const ELEMENTS = new Set(['html','head','body','table','thead','tbody','tfoot','tr','td','th',
 'caption','colgroup','col','div','span','br','hr','img','h1','h2','h3','h4','h5','h6',
 'blockquote','pre','code','sup','sub','u','s','strike','small','big','font','center',
 'section','article','aside','header','footer','nav','main','figure','figcaption','iframe',
 'script','style','link','meta','form','input','button','select','option','textarea','label',
 'video','audio','source','picture','svg','path','mark','abbr','cite','q','time','wbr']);

const BLOCK_RE   = new RegExp('</?\\s*(' + BLOCK.join('|') + ')\\b', 'i');
const TAGLIKE    = /<\/?\s*([a-zA-Z][a-zA-Z0-9]*)(?:\s[^<>]*)?\/?>/g;
const INLINE_RUN = /<\/?\s*(?:strong|b|em|i)\s*>|<\s*a\b[^<>]*>|<\/\s*a\s*>/gi;
const HREF       = /href\s*=\s*["']([^"']*)["']/i;
const BULLET     = /^\s*[•‣◦⁃∙*\-–—]\s+/;
const OUT        = {b:'strong', strong:'strong', i:'em', em:'em', a:'a'};

const ESC = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const UNESC = s => { const t = document.createElement('textarea'); t.innerHTML = s; return t.value; };

function unsupportedElements(raw) {
  const bad = []; let m; TAGLIKE.lastIndex = 0;
  while ((m = TAGLIKE.exec(raw)) !== null) {
    const n = m[1].toLowerCase();
    if (ELEMENTS.has(n) && !KNOWN.has(n)) bad.push(n);
  }
  return [...new Set(bad)];
}

function splitLines(raw) {
  const lines = (raw || '').replace(/\r\n?/g, '\n').split('\n').map(l => l.replace(/\s+$/, ''));
  while (lines.length && !lines[0].trim()) lines.shift();
  while (lines.length && !lines[lines.length-1].trim()) lines.pop();
  return lines;
}

// Only <a>, <strong>, <b>, <em>, <i> are markup here. Everything else is
// literal, so "Size < 10cm" stays a sentence.
function renderLine(s) {
  let html = '', plain = '', pos = 0, m; INLINE_RUN.lastIndex = 0;
  while ((m = INLINE_RUN.exec(s)) !== null) {
    const chunk = UNESC(s.slice(pos, m.index));
    html += ESC(chunk); plain += chunk;
    const tok = m[0], low = tok.toLowerCase();
    if (low.startsWith('</')) html += '</' + OUT[low.slice(2).replace(/[\s>]/g,'')] + '>';
    else if (low.startsWith('<a')) { const h = HREF.exec(tok); html += h ? '<a href="' + ESC(h[1]) + '">' : '<a>'; }
    else html += '<' + OUT[low.replace(/[<>\s]/g,'')] + '>';
    pos = m.index + tok.length;
  }
  const chunk = UNESC(s.slice(pos));
  html += ESC(chunk); plain += chunk;
  return [html, plain.trim()];
}

// Consecutive bullet lines make one list; a blank line closes it.
function linesToHtml(lines) {
  const htmlParts = [], plainParts = []; let buf = [];
  const flush = () => {
    if (buf.length) {
      htmlParts.push('<ul>' + buf.map(([h]) => '<li>' + h + '</li>').join('') + '</ul>');
      buf.forEach(([, p]) => plainParts.push(p));
      buf = [];
    }
  };
  for (const line of lines) {
    if (!line.trim()) { flush(); continue; }
    const m = BULLET.exec(line);
    if (m) { buf.push(renderLine(line.slice(m[0].length))); continue; }
    flush();
    const [h, p] = renderLine(line);
    if (p) { htmlParts.push('<p>' + h + '</p>'); plainParts.push(p); }
  }
  flush();
  return [htmlParts.join(''), plainParts.join('\n')];
}

function inlineOf(node) {
  let out = '';
  for (const n of node.childNodes) {
    if (n.nodeType === 3) { out += ESC(n.nodeValue); continue; }
    const t = n.tagName.toLowerCase();
    if (!KNOWN.has(t)) throw new Error('unsupported tag: ' + t);
    if (t === 'strong' || t === 'b') out += '<strong>' + inlineOf(n) + '</strong>';
    else if (t === 'em' || t === 'i') out += '<em>' + inlineOf(n) + '</em>';
    else if (t === 'a') out += '<a href="' + ESC(n.getAttribute('href') || '') + '">' + inlineOf(n) + '</a>';
    else throw new Error('unsupported tag: ' + t);
  }
  return out;
}

function convertCell(raw) {
  raw = (raw || '').trim();
  if (!raw) return null;

  if (BLOCK_RE.test(raw)) {                     // the markup path
    const doc = new DOMParser().parseFromString(raw, 'text/html');
    const blocks = [];
    for (const node of doc.body.childNodes) {
      if (node.nodeType === 3) {
        if (node.nodeValue.trim()) blocks.push({ul:false, items:[ESC(node.nodeValue.trim())]});
        continue;
      }
      const t = node.tagName.toLowerCase();
      if (!KNOWN.has(t)) throw new Error('unsupported tag: ' + t);
      if (t === 'dl') {
        const items = []; let term = null;
        for (const c of node.children) {
          const ct = c.tagName.toLowerCase();
          if (ct === 'dt') { if (term !== null) throw new Error('<dt> with no matching <dd>'); term = inlineOf(c); }
          else if (ct === 'dd') {
            if (term === null) throw new Error('<dd> with no preceding <dt>');
            items.push(term.replace(/\s*:\s*$/, '') + ': ' + inlineOf(c).replace(/^\s+/, ''));
            term = null;
          } else throw new Error('unsupported tag in <dl>: ' + ct);
        }
        if (term !== null) throw new Error('<dt> with no matching <dd>');
        blocks.push({ul:true, items});
      } else if (t === 'ul' || t === 'ol') {
        blocks.push({ul:true, items:[...node.children].map(li => inlineOf(li))});
      } else if (t === 'p') {
        const s = inlineOf(node); if (s.trim()) blocks.push({ul:false, items:[s]});
      } else throw new Error('unsupported tag: ' + t);
    }
    if (!blocks.length) return null;
    const html = blocks.map(b => b.ul
      ? '<ul>' + b.items.map(i => '<li>' + i + '</li>').join('') + '</ul>'
      : '<p>' + b.items[0] + '</p>').join('');
    const plain = blocks.flatMap(b => b.items)
      .map(s => UNESC(s.replace(/<[^>]+>/g, '')).trim()).join('\n');
    return {html, plain, kind: 'markup'};
  }

  const bad = unsupportedElements(raw);         // the text path
  if (bad.length) throw new Error('unsupported tag(s): ' + bad.join(', '));
  const [html, plain] = linesToHtml(splitLines(raw));
  if (!html) return null;
  return {html, plain, kind: 'text'};
}

function convertList(cells) {
  const values = [];
  for (const cell of cells) for (const line of splitLines(cell)) {
    if (!line.trim()) continue;
    const m = BULLET.exec(line);
    const [, p] = renderLine(m ? line.slice(m[0].length) : line);
    if (p) values.push(p);
  }
  return values.length ? {values} : null;
}

// --- self-check: the same fixtures the Python converter is tested against ---
const BU = '•';
const CASES = [
  // text path — what most sheets hold
  ['Features\n' + BU + ' Top zipper\n' + BU + ' Fits standard credit cards',
   '<p>Features</p><ul><li>Top zipper</li><li>Fits standard credit cards</li></ul>'],
  ['Leather\r\n' + BU + ' Soft.\r\n\r\nHardware\r\n' + BU + ' Strong.\r\n\r\n',
   '<p>Leather</p><ul><li>Soft.</li></ul><p>Hardware</p><ul><li>Strong.</li></ul>'],
  ['Size < 10cm and > 5cm', '<p>Size &lt; 10cm and &gt; 5cm</p>'],
  ['100% cotton <do not bleach>', '<p>100% cotton &lt;do not bleach&gt;</p>'],
  ['First line.\nSecond line.', '<p>First line.</p><p>Second line.</p>'],
  ['Use <a href="https://x.com/b">the balm</a>.',
   '<p>Use <a href="https://x.com/b">the balm</a>.</p>'],
  // markup path — the exception
  ['<dl><dt>Best for</dt><dd>Espresso</dd><dt>Origins</dt><dd>Central America and Africa</dd></dl>',
   '<ul><li>Best for: Espresso</li><li>Origins: Central America and Africa</li></ul>'],
  ['<dl><dt>Best for:</dt><dd>Espresso</dd></dl>', '<ul><li>Best for: Espresso</li></ul>'],
  ['<dl><dt>Origins</dt><dd>Brazil &amp; Peru</dd></dl>', '<ul><li>Origins: Brazil &amp; Peru</li></ul>'],
  ['<p>Grind fresh right before you brew.</p>', '<p>Grind fresh right before you brew.</p>'],
  ['<dl><dt>Best for</dt><dd>A <strong>sweet</strong> espresso</dd></dl>',
   '<ul><li>Best for: A <strong>sweet</strong> espresso</li></ul>'],
];
const failures = [];
for (const [input, expected] of CASES) {
  let got;
  try { got = convertCell(input).html; } catch (e) { got = 'THREW: ' + e.message; }
  if (got !== expected) failures.push({input, expected, got});
}
for (const bad of ['<table><tr><td>x</td></tr></table>', 'a <span>b</span> c',
                   '<dl><dt>Best for</dt><dd>Espresso</dd><dt>Origins</dt></dl>',
                   '<dl><dd>Espresso</dd></dl>']) {
  let threw = false;
  try { convertCell(bad); } catch (e) { threw = true; }
  if (!threw) failures.push({input: bad, expected: 'an error', got: 'no error'});
}
const listOk = JSON.stringify(convertList([BU + ' One\n' + BU + ' Two', 'Three']).values)
             === JSON.stringify(['One','Two','Three']);
const welded = convertCell(CASES[6][0]).html.includes('Best forEspresso');
JSON.stringify({selfCheckFailures: failures, listOk, welded}, null, 2)
```

The self-check must report `selfCheckFailures: []`, `listOk: true` and `welded: false`. Anything else means the converter is wrong — stop.

Then convert every mapped cell. A cell takes one of two paths, chosen by looking at the cell, not the column:

- **Text** — the common case. Consecutive bullet lines become one list; every other line becomes a paragraph; a blank line closes the list in progress. Angle brackets in prose stay prose.
- **Markup** — only when the cell carries a block-level tag. A definition list becomes one bulleted list, one item per pair, `Term: value`, not bold.

Links survive either path.

- A list metafield takes its columns in order, and a cell holding several bulleted lines contributes one value per line. Both compose.
- An empty source cell means **skip that field**. Write nothing, erase nothing.
- The converter throws rather than guessing — a real HTML element it cannot represent, a `<dt>` with no `<dd>`. Bring me the error; do not work around it.
- Tell me which columns came out as text and which as markup. Most sheets are all text; a markup column is worth a second look.

Show me the converted output for a few rows, including one of each cell shape, before going on.

Group identical values and tell me the groups — set the clipboard once per group rather than once per product.

---

## Phase 3 — Backup. Nothing is written until this exists.

**If Matrixify is installed:** Matrixify → New Export → Products → columns: Handle plus the mapped metafield columns only. Run it, download the file from All Jobs, and do not open it in Excel — Excel truncates cells at 32,767 characters and re-saving loses what it did not load. Columns absent from an import are left untouched, so this file cannot reach prices, titles or media. Tell me the job is done.

**If not:** capture every current value first, through the same editor you are about to write with. The collapsed preview truncates, so open each field to read it. Then **print the whole capture in the chat as JSON**, one entry per product per field:

```json
{"handle": "blonde", "key": "custom.revamp_details", "value": "<ul><li>Best for: Espresso</li></ul>"}
```

A field holding nothing gets `"value": null`, never `""`. That distinction is what lets an undo delete rather than blank.

You have no filesystem, so **I have to save this myself.** Say so plainly and wait for me to confirm I have saved it.

**Stop here either way.** This is the point of no return.

---

## Phase 4 — Write.

**Matrixify mode:** build the import file from the converted values. Keep the `Command` column as `MERGE` — `REPLACE` deletes the product and recreates it from the file alone. Include only the columns being written. Upload, run, and read the job result rather than assuming it worked. Do not schedule it: a repeating import against a live sheet deletes a metafield the moment someone clears a cell.

**Browser mode:** use the bulk editor, not product pages.

1. Products → select the page → Bulk edit. Store-wide "select all" does not carry into the bulk editor. Fifty at a time.
2. Columns → clear the defaults, check only the mapped metafields **and URL handle (SEO)**. The handle column is the only thing tying a row to its product — titles repeat.
3. Widen the handle column.
4. Collapse variants: click every `button[aria-expanded="true"]` except those labelled `Columns` or starting with `Status`. Scroll, collapse again, repeat until the header count stops rising.
5. Work strictly top-down. Collapse state resets when virtualised rows recycle, so scrolling back up silently re-expands and every row below moves.

For a rich-text field, put both clipboard flavours in place first:

```js
await navigator.clipboard.write([new ClipboardItem({
  'text/html':  new Blob([html],  {type: 'text/html'}),
  'text/plain': new Blob([plain], {type: 'text/plain'})
})]);
```

Then: click the cell → Return to open the editor → wait 2s → focus it **with JavaScript**, not a click:

```js
document.querySelector('[contenteditable="true"]').focus()
```

The popover anchors above, below or left depending on space, so a coordinate click misses and dismisses it. Confirm the field is empty before pasting — cmd+A intermittently does nothing, and a paste onto a non-empty field appends. Then paste, then Escape.

For a list field: the "Add item" control is **invisible to `querySelectorAll('button')`**, because the admin uses web components. Find it by scanning for an element with no children whose text is exactly `Add item`. **Never type into these fields** — focus stays on the button after clicking it, so every space in typed text presses it again and spawns empty rows. Set values directly:

```js
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(input, value);
input.dispatchEvent(new Event('input',  {bubbles: true}));
input.dispatchEvent(new Event('change', {bubbles: true}));
```

Click Add item as many times as the value count needs first, then set every value, then read them back to confirm the count and order.

Save every twenty products or so.

**Never save an empty editor.** It fires a delete, and the metafield is gone.

**Stop after the first batch** and show me the result before continuing.

---

## Phase 5 — Verify on the storefront.

The admin cannot answer this. A save confirmation says nothing about what was stored, and the collapsed preview truncates.

Load each product's page on the storefront and compare what rendered against what you converted. **Do the comparison inside the page and return only the mismatches** — the tool that runs JavaScript caps its return at about 1000 characters and silently blocks anything shaped like `key=value` or base64, so a pass that returns values comes back empty or truncated.

Check at least one product per template. A value can be written correctly and still not appear, because the template pulls something else — report that separately from a write fault.

---

## Traps, all of which have actually happened

- **A window resize mid-batch shifts every row.** Content lands on the wrong product, with no error. If the window changes size, stop and re-derive every row position.
- **The extension drops batches at random.** Never assume a batch finished because it started. Screenshot, read the real state, resume from there. A half-finished batch often leaves an editor popover open over the next row.
- **Never retype content from earlier output** — it may have been truncated at 1000 characters.
- **Use cmd, not ctrl.** The tooltips read ⌃B; on macOS ctrl+B moves the cursor instead.
- **Copy values exactly.** No rewording, retrimming or recapitalising.
- **Never write to my sheet**, not even to add a tab.

---

## Finish with a report

Products completed. Fields per product. What you verified and how. Anything written that is not rendering. Any source-data problems you noticed. Anything still outstanding — and say it plainly if the Backup was never confirmed saved.
````

## Keeping the two in step

The conversion rule lives in `scripts/convert.py` and, ported, in the block above. `convert.py` is authoritative and is the one with tests. A change to the rule is a change to both, plus the fixtures in `CASES` and in `scripts/test_convert.py`.

The fastest check that they still agree: run the `CASES` inputs through `python3 scripts/convert.py` and compare against the same expected strings.
