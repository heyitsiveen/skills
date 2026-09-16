---
name: sheet-to-shopify-metafields
description: Use when the user wants product copy pushed from a Google Sheet into Shopify product metafields through the browser, with no Shopify API. Triggers on "update product metafields from this sheet", "push the PDP copy to Shopify", "bulk fill metafields from a spreadsheet", "write the sheet columns into the metafields", a structured prompt carrying `Sheet:`, `Store:`, `Mapping:` or `Matrixify:`, and on "undo the metafield run" / "put the old metafield values back" for reversing a previous Run. Also use when asked to audit such a sheet before writing anything. For building a section from Figma use `figma-shopify-builder`.
user-invocable: true
---

# Sheet to Shopify Metafields

Push product copy from a **Source sheet** into Shopify product metafields, through the browser, for any client store. One **Run** is one sheet, one store, one **Mapping**.

This skill exists because the obvious approach destroys data silently. Shopify's rich-text metafield editor keeps exactly what maps onto its seven node types and discards everything else **including the whitespace around what it discarded**. Paste a definition list in and every term is glued to its value with no separator — `Best forEspressoOrigins…`. That is **Welding**. It saves without an error, and the admin's collapsed preview flattens a list onto one line anyway, so the admin shows the same thing for a correct value and a welded one. Only the storefront tells them apart, and the pairing cannot be recovered.

So the conversion happens in a program, before the browser is opened, and its output is inspectable before anything is written. Metafields have no version history and no undo, and on a typical Run every target field is already populated — the job is an overwrite, not a fill.

Read `../../../CONTEXT.md` for the vocabulary, and `docs/adr/0006`, `0007` and `0008` for why the Backup, the conversion shape, and the storefront read-back are what they are.

## Required inputs (parse from the user's message; ask for any that are missing)

| Input | Meaning | Default |
|---|---|---|
| `Sheet:` | URL of the Source sheet, including the tab | — |
| `Store:` | Shopify admin URL | — |
| `Mapping:` | which column feeds which metafield | — |
| `Matrixify:` | `true` or `false` — whether the store has the Matrixify app | ask |
| `Mode:` | `verify-first` reports every difference and writes nothing; `write` applies them | `verify-first` |
| `Formatting:` | who wins where the store and the sheet disagree on styling | `sheet` |

**`Mode: verify-first` is the default and should usually stay it.** It is Phase 5 run in place of Phase 4: read what is there, compare it to what the Run intends, print the table, change nothing. Being wrong then costs nothing.

**`Formatting:`** has three answers, and the choice applies to every row:

- **`sheet`** — the sheet is authoritative. Whatever the store carries that the sheet does not — bolded headings, a hyperlink someone added by hand — is replaced. Pre-flight reports exactly how much styling this removes before anything is written.
- **`store`** — keep the store's styling, take the wording from the sheet: re-apply bolding on heading lines, and keep any existing hyperlink whose anchor text still appears in the new copy.
- **`house`** — bold the first line of each section, keep links, everything else plain.

State the answer in the closing report, whichever it was.

Ask for the Mapping rather than inferring it. A column header and a metafield display name differ more often than not (`Details (HTML)` → `Revamp Details`), and a metafield key does not have to follow its own naming convention — one real store has `Revamp Product Benefits` living at `custom.product_benefits` with no `revamp` in it.

Ask for `Matrixify:` when it is absent, before any other work. It decides both how the Backup is taken and how the write happens, so it cannot be deferred.

Write the Mapping to `.agent/sheet-to-shopify-metafields/mapping.json` in this shape, and use it for every script call:

```json
{
  "handle_column": "Handle",
  "targets": [
    {"key": "custom.revamp_details", "type": "rich_text_field",
     "columns": ["Details (HTML)"]},
    {"key": "custom.product_benefits", "type": "list.single_line_text_field",
     "columns": ["Bullet 1", "Bullet 2", "Bullet 3"]}
  ]
}
```

Several columns feeding one list metafield is normal — they become that metafield's values, in the order listed. So does one column whose cell holds several bulleted lines; both compose, so three bullet columns and one bulleted cell reach the same place.

Some sheets have no handle column at all and identify a product only by its URL. Derive it:

```json
"handle_column": {"from_url": "Product URL"}
```

A derived handle is a **guess** until the URL has been visited, and Phase 1 will refuse to go on until it has been. See *Resolve the handles* below.

## The workflow

Five phases. Phases 1 and 2 write nothing anywhere and can be run alone to audit a sheet.

### Phase 1 — Pre-flight

**Read the Source sheet through the clipboard, as HTML.** In the sheet, click the **Name Box**, type the full range (`A1:I53` for nine columns and 52 rows), press Enter, then `cmd+c`. Selecting by range touches no cell contents.

Then read the system clipboard from the shell:

```sh
osascript -e 'the clipboard as «class HTML»' \
  | perl -ne 's/^«data HTML//; s/»\s*$//; print pack "H*", $_' \
  > .agent/sheet-to-shopify-metafields/sheet.html
```

**Do not try to carry the HTML out through the browser.** Reading
`navigator.clipboard.read()` works, but the JavaScript tool's content filter
refuses to return the result — Google Sheets HTML trips its `key=value`
heuristic on the very first slice, and a gzip-plus-base64 workaround trips the
base64 heuristic instead. Posting it to a local receiver is blocked by the
admin's CSP. The shell route above avoids all three, and needs no browser tab
at all.

Check the file is not empty and holds one `<tr>` per row plus the header.

**Take `text/html`, not `text/plain`.** A sheet's hyperlinks exist only as cell formatting: the plain flavour returns the anchor text and drops every href. One real sheet carries 59 of them, and rich text has a link node, so they only survive if the read sees them. The HTML flavour also makes line breaks and cell boundaries unambiguous. `--tsv` still works for a sheet with no links, but prefer `--html`.

A fetched read garbles the copy and miscounts the rows — one run reported 100 rows, then 106, when the truth was 76. Export URLs start a download the session cannot read. Confirm the true row count independently: press `cmd+Down` from A1 in the sheet and read the Name Box.

If the sheet URL walls you with "Verify it's you", it is resolving against the wrong Google account. Navigate to the `/spreadsheets/u/0/d/…` form instead — that is profile selection, not a login.

**Audit it, and show the user the result:**

```sh
python3 scripts/convert.py inspect --html <sheet.html> --mapping <mapping.json>
```

It exits non-zero when a mapped column is missing from the sheet, an unsupported HTML element is present, or a cell fails to convert. It reports the exact header row, the row count, where the handle comes from, empty mapped cells, duplicate handles, which products share identical values, and — the part worth reading aloud to the user — **what each mapped column actually holds**: how many cells are plain text and how many are markup, how many span several lines, how many are bulleted, and how many carry links.

Most sheets are all text. A column reported as markup is the exception, and worth a second look.

**Resolve the handles, when they are derived from a URL.** Skip this when the sheet has its own handle column.

```sh
python3 scripts/convert.py urls --html <sheet.html> --mapping <mapping.json>
```

That is the worklist — distinct URLs, in sheet order. Visit each one and record two things: the **final URL after redirects**, and the **exact product title** from the page.

```json
{"https://shop.com/products/old-name": {"handle": "new-name",
                                        "title": "The New Name"}}
```

Write it to `.agent/sheet-to-shopify-metafields/resolved.json` and pass it as `--resolved` to `inspect` and `convert`.

The last path segment of a URL is normally the handle, so deriving it usually works — but **a renamed product keeps its old URL working and redirects to the new handle**. The derived guess is then stale: it finds nothing, or it finds a different product and writes this row's copy onto it. Visiting is what tells the two apart, and `inspect` reports every row where the derived handle and the real one disagree.

The title is worth having for its own sake: Shopify's admin search works on titles, and it is the human check that a row reached the product it was meant for.

`convert` refuses to run while any URL is unvisited, rather than writing against guesses.

**Read the notes column too.** When the sheet has a QA, notes or "needs input" column, read its contents and surface them, even when the Mapping says to ignore that column. Ignoring a column means not mapping it — its contents still bear on whether the Run is safe. One real sheet used it to record duplicate live products whose copy contradicted itself, which is a merchandising decision a human has to make before anything is overwritten.

A sheet can also carry signal that no text read recovers — one marks its problem rows by **cell fill colour** alone. Glance at the sheet as well as parsing it.

**Inspect the store.** Open Settings → Custom data → Products (`/settings/custom_data/product/metafields` — singular) and record each mapped metafield's real key and type. Then open one product and note how many target fields already hold values.

Stop and tell the user when a mapped metafield does not exist. Creating one is out of scope: it would make an Undo mean deleting a definition, which is a schema change with a much larger blast radius.

Report the mode the Run will use and what it will cost before going further.

### Phase 2 — Conversion

```sh
python3 scripts/convert.py convert --html <sheet.html> --mapping <mapping.json> \
  --resolved <resolved.json> \
  --out .agent/sheet-to-shopify-metafields/converted.json
```

Drop `--resolved` when the sheet has its own handle column.

Every mapped cell becomes a **Converted value**: a rich-text HTML fragment with its plain-text twin, or an ordered array for a list metafield.

A cell takes one of two paths, and the converter picks by looking at the cell rather than at the column:

**Text** — the common case, and what most sheets hold. Structure comes from line breaks and bullet glyphs. Consecutive bullet lines become one list; every other line becomes a paragraph; a blank line closes the list in progress, which is how a sheet separates one group of bullets from the next. Line endings are normalised and trailing blank lines dropped, so no empty paragraph reaches the store. Angle brackets in prose stay prose: `Size < 10cm` is a sentence, and `100% cotton <do not bleach>` is text, not a broken tag.

**Markup** — only when the cell carries a block-level tag the converter knows. A definition list becomes one unordered list with one item per pair, each item the plain text `Term: value`. A single-paragraph cell stays one paragraph.

Links survive either path, because rich text has a link node and the HTML read keeps the href.

The converter stops the Run rather than guessing: a real HTML element it cannot represent — `<table>`, `<span>`, `<br>` — a `<dt>` with no matching `<dd>`, a `<dd>` with no preceding `<dt>`. Take that to the user; do not work around it. Tag-shaped prose naming no element at all is reported by Pre-flight as `taglike_text` and passes through as text, because that is almost always what was meant.

Show the user the converted output for a handful of rows, including one of each cell shape present, before going on.

### Phase 3 — Backup

Nothing is written until a **Backup** exists that can restore. A record that can only be read by a human is not a Backup.

- **Matrixify mode** — one export is the Backup. See `references/matrixify-mode.md`.
- **Browser mode** — a capture pass through the same surface the write uses. See `references/browser-mode.md`.
- **Any target with a `path`** — a capture pass through the entry editor. See `references/metaobject-mode.md`. Matrixify is not available for this half, whichever mode the rest of the Run is in.

Both end at the same place:

```sh
python3 scripts/convert.py backup-write --store <store> \
  --entries <captured.json> --out .agent/sheet-to-shopify-metafields/backup-<store>-<date>.json
```

A field holding nothing is recorded as `null`, never as an empty string. That is what lets an Undo restore *absent* as absent.

**Then compare, before writing anything:**

```sh
python3 scripts/convert.py diff --converted <converted.json> --current <captured.json>
```

The capture pass has just read every current value, so the comparison is free. It reports, per field, `already correct` or `differs` — and for every difference, what writing it would **remove**: bold the store has and the sheet does not, italics, links.

Two things fall out of this and both matter.

**Fields already correct are not written.** A Run repeated after a partial pass, or against a sheet that has barely changed, does almost nothing. Never create a second metaobject entry for a product that already has one.

**`would_remove` is the `Formatting:` decision made visible.** Under `sheet`, a report of `{"bold": 41, "link(s)": 6}` means this Run strips bolding from 41 fields and six links. That is the policy working as chosen — but it is worth reading aloud before approving, because nobody pictures 41 when they choose "the sheet wins".

**In `verify-first` mode the Run ends here**, with that table. Phase 4 happens only after the user approves and switches to `write`.

**Stop here.** This is the point of no return, and it is a decision rather than a step.

### Phase 4 — Write

- **Matrixify mode** — `references/matrixify-mode.md`.
- **Browser mode** — `references/browser-mode.md`.
- **Any target with a `path`** — `references/metaobject-mode.md`. The text is not in the product metafield; that only points at an entry, and the words can be another hop beyond it. There is no bulk editor for entries, so this half is one entry at a time and is the bulk of the Run's cost.

Write the group with the most shared values first. The converter's `groups` report names products sharing identical values — on one catalogue 76 products shared 14 distinct brew blocks, so the work was 14 pieces rather than 76.

Stop after the first batch and show the user the result before continuing with the rest.

Record progress to `.agent/sheet-to-shopify-metafields/progress.json` as the Run proceeds, so a Run that breaks at product 40 resumes at 41. On resume, read the real state first — a batch that was started is not a batch that finished.

### Phase 5 — Verification

Load each product's rendered page on the storefront and compare what rendered against the Converted value. The admin cannot answer this: a metafield there is a collapsed button whose preview truncates, and a save confirmation says nothing about what was stored.

Compare **inside the page** and return only the mismatches. The tool that runs JavaScript caps its return at about 1000 characters and silently blocks payloads shaped like `key=value` or base64, so a pass that returns values instead of a verdict comes back empty or truncated.

Check at least one product per template and per content variant. A value can be written correctly and still not appear, because the template pulls something else — that happened on a real run, three fields of four. Report that as its own category, separate from a write fault.

Close with a report naming: products completed, fields per product, what was verified and how, anything written but not rendering, source-data problems found along the way, and anything still outstanding. State an unconfirmed Backup explicitly rather than leaving it implied.

## Undo

Reversing a Run means replaying its Backup:

```sh
python3 scripts/convert.py backup-read --file <backup.json>
```

That returns two sets. `restore` holds fields that had a value — write those back the same way the Run wrote. `delete` holds fields that held nothing — clear those, which removes the metafield. Clearing in the admin fires a delete rather than storing an empty value, so absent really does come back as absent.

Name the Backup file and ask the user to confirm before replaying it. Tell them plainly when a later Run has touched the same products, because the Backup then restores stale values over newer ones.

To undo one product, cut the other entries out of the Backup file. That needs no extra machinery.

## Behavior rules

- **Convert before the browser opens.** Every guard in this skill exists to keep Welding from reaching a live catalogue.
- **Take the Backup before the first write.** A Run that writes before it captures has an unrecoverable failure mode.
- **An empty source cell means skip that field.** Leave what is there untouched. Writing an empty value into a rich-text metafield deletes it.
- **Save an editor only when it holds the value you intend.** Saving an empty one deletes the metafield.
- **Use `cmd`, not `ctrl`.** The editor's tooltips read `⌃B`, and on macOS `ctrl+B` moves the cursor instead of bolding.
- **Copy the value exactly.** No rewording, no retrimming, no recapitalising. The copy that lands is the copy that was approved.
- **Read values back from the rendered page**, never from a save confirmation.
- **Keep the Source sheet read-only.** Never write to it, not even to add a tab. Generated files go under `.agent/sheet-to-shopify-metafields/`.
- **Use the Shopify admin and the storefront only.** No Admin API, no Storefront API, no Shopify CLI, no Matrixify MCP server — including where one would be faster (ADR-0008).

## Edge cases worth knowing

**Two Chrome permissions.** A Run needs `admin.shopify.com` and `docs.google.com` granted in the Chrome extension. Choose "Always allow actions on this site" once each. Tell the user up front rather than being interrupted mid-pass.

**The sheet link may point at the wrong Google account.** A link carrying `authuser=2` resolves against that account and can hit a verification wall. When the sheet will not open, this is the first thing to check.

**A tab is addressed by name, not by `gid`.** Matrixify and the `gviz` endpoint both want the tab's label, so read it off the sheet once rather than deriving it from the URL.

**Handles disambiguate, titles do not.** Two products can share a title. Always work from the handle column.

**A resize invalidates row positions.** In Browser mode the grid's rows are positional. If the window changes size mid-pass, stop and re-derive every position before continuing.

**Batches drop.** The browser extension loses one occasionally with no error. Screenshot and read the real state rather than assuming a started batch finished. A half-completed batch often leaves an editor popover open over the next row.

**Never retype content from earlier tool output.** It may have been truncated at 1000 characters. Take values from `converted.json`.

## What this skill does NOT do

- **Create or alter metafield definitions.** A missing one stops the Run.
- **Change a metafield's type** — for instance to multi-line text, which would store the source HTML losslessly. That is a store decision that affects the theme.
- **Use any Shopify API**, even where one is measurably cheaper.
- **Touch anything but product metafields** — not variants, collections, customers, titles or descriptions.
- **Resolve the source data's own conflicts.** It surfaces them; a human decides.
- **Create scheduled or repeating imports.** A repeat against a live sheet is a standing destructive write, because a cleared cell deletes a metafield on the next tick.
- **Reach draft or unpublished products** in Phase 5, which reads rendered pages.

## Working on the converter

```sh
python3 -m unittest discover -s scripts
```

36 tests, stdlib only, nothing to install. The fixtures are real cells from a real catalogue, including the row whose source carries a hand-escaped `&amp;`. Invented fixtures would not have found Welding.

`scripts/convert.py` owns everything between the sheet and the browser: TSV parsing, conversion, list values, and the Backup format in both directions. Keep it that way — logic that leaks out of it stops being testable, and this is the one place where a silent bug reaches a live catalogue.

## Running the job in Claude in Chrome instead

Chrome has no filesystem and no Python, so this skill cannot run there. `references/claude-in-chrome-prompt.md` holds a self-contained prompt for it, with the converter ported to in-page JavaScript.

That port is a second copy of the conversion rule, so **a change here is a change there** — the JavaScript and the `CASES` fixtures inside that prompt, as well as `scripts/test_convert.py`. `convert.py` stays authoritative; the port carries the same fixtures and runs them as a self-check before it touches a product, which is the nearest thing to a test that a page can offer.

The Chrome route is weaker in one way that has nothing to do with the converter: there is nowhere to put a Backup. Matrixify mode is unaffected, because the export lives in Matrixify's own job list. Browser mode has to print the capture and rely on a human to save it, so prefer Matrixify mode there.
