# A definition list becomes a bulleted list

Both HTML columns of the first Source sheet are definition lists — 76 of 76 cells in `Details (HTML)`, and 52 of 76 in `Brew (HTML)`, using `<dl>`, `<dt>` and `<dd>`. Their destination is `rich_text_field`, whose schema has exactly seven node types: root, paragraph, text, heading, link, list and list-item. There is no definition-list node. The structure cannot be stored, so it must be re-expressed, and something is given up whichever way it goes.

Three shapes were written out in full — as JSON and as the HTML Liquid emits for each. A bulleted list with one item per pair wins on one argument: a definition list *is* a list of pairs, and listness is the single structural property `<dl>` and a candidate shape can share. That shape keeps the container, the pair grouping and the pair count. It gives up only the term/value element distinction, which no shape can keep, so that loss is the floor rather than a mark against it.

Headings per term were rejected as worse than lossy. They lose the container, the grouping and the distinction, then inject dozens of spurious `<h3>`s into the page outline across 76 products, disordering the document hierarchy for screen readers and crawlers. A `<dt>` is a term, not a heading.

Two independent lines of evidence then converged on the same target. The store's existing 76 values are already stored in exactly this shape — one unordered list, one item per pair, the plain string `Term: value`, unbolded — and the live theme renders it as real `<ul>`/`<li>`. Separately, the completed run that preceded this skill reached the identical rule on its own: `<dl><dt>X</dt><dd>Y</dd></dl>` → `<ul><li>X: Y</li></ul>`.

Choosing the variant already in the store means a Run writes documents identical in shape to what is there, so the write does not silently restyle a catalogue nobody asked to restyle. It also means nothing in the conversion depends on undocumented schema behaviour, because the bolded variant — term and value as sibling text nodes, term flagged `bold` — is reachable but unnecessary.

## Consequences

The 24 single-`<p>` cells map to a one-paragraph document. Mixed output across one metafield is correct, not an inconsistency: the two input populations map to their two nearest targets and stay distinguishable in the markup exactly as they are in the source.

The conversion happens before anything reaches the browser. This is not a preference. Pasting a definition list into the editor produces Welding — terms concatenated to values with no separator, saving cleanly and reading correctly in the admin. A skill built on the obvious approach would have destroyed the pairing on every product silently.

Bold is a one-line change if it is ever wanted, and the schema supports it, so this decision is cheap to revisit. What is not cheap to revisit is a Run that has already flattened 76 products into a shape nobody chose.
