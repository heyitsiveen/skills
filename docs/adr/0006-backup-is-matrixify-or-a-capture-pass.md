# The Backup is a Matrixify export where Matrixify exists, and a capture pass where it does not

Shopify metafields have no version history and no undo. A Run overwrites live product copy — on the first target catalogue, 304 values across 76 products, every one already populated. Losing them is permanent.

Shopify's own product CSV export carries 26 metafield types and neither of the two that matter here: `rich_text_field` and `list.single_line_text_field`. So the platform cannot produce the Backup. The admin bulk editor can display the values but exports nothing, its collapsed previews truncate, and no Shopify surface exports metafield *values* at all. There is no product timeline, no activity-log value, no version history.

Matrixify can, and one documented rule is what makes its export a Backup rather than a record: a blank cell on import **deletes** the metafield — "not set to empty value, but deleted" — and a product that has no metafield exports blank. So re-importing an untouched export restores *absent* correctly, which a native CSV round-trip structurally cannot do. Its own docs state the file is re-importable as exported, and omitted columns are left untouched, so a `Handle`-plus-metafields file cannot damage prices, titles or media.

Where Matrixify is not installed, the Backup is a capture pass through the same surface the write uses, and an Undo is that capture replayed. This is sound for a reason particular to this design: if the browser can write a value, it can write the prior value back. Whatever fidelity the write path has, the restore path has the same, because it is the same path. The admin also has no empty-but-present state — clearing a field fires a delete — so a Browser mode Undo can restore absent as absent too.

Matrixify is therefore not the secondary method the brief first described. It is the faster and safer of two paths, and where it exists the same export that is the Backup is also, inverted, the Undo.

## Consequences

`Matrixify: true/false` is a Run input. Where it is not supplied the skill asks before doing anything, because the answer changes both the Backup and the write, not just the speed.

Matrixify mode carries two guardrails that fall out of its own documentation, and both are silent when broken. The `Command` column stays `MERGE` — `REPLACE` deletes and recreates the product. The Backup file is never opened in a spreadsheet program, because Excel truncates at 32,767 characters per cell and re-saving loses everything not loaded.

The free Matrixify tier caps a job at 10 products, so a catalogue over ten needs the paid tier before a Backup can be taken at all. The skill establishes this during Pre-flight, not after the Backup fails.

Browser mode's Backup costs a full capture pass before the first write. That cost is not optional and is not traded away for speed: a Run that writes before it has captured is a Run whose failure is unrecoverable.
