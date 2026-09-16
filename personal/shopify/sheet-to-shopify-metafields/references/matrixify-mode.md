# Matrixify mode — one export is the Backup, one import is the write

Reached from Phase 3 and Phase 4 of `SKILL.md` when the store has the Matrixify app.

This mode is faster and safer than Browser mode on both halves of the job. No editor, no clipboard, no popover focus, no positional grid — so none of Browser mode's hazards apply. Where Matrixify exists, prefer it.

## Check the plan first, in Pre-flight

Matrixify's per-job cap is by product count: the free Demo tier processes **10 products per job**, Basic **5,000**. Cloud sourcing, scheduling and metafield support are on every tier including free, so the cap is the only thing that binds.

A catalogue over ten products needs the paid tier **before the Backup can be taken**. Establish this during Phase 1, not after the Backup was supposed to have happened.

## The Backup is an export

Matrixify → **New Export** → Products → columns: `Handle` plus the mapped metafield columns only. Run it, then download the file from **All Jobs**, where it stays available indefinitely.

Restricting the columns is what makes the file safe to re-import: **columns not present in an import are left untouched**, so a handle-plus-metafields file cannot reach prices, titles, inventory or media.

Two rules about the file itself, both silent when broken:

- **Never open the Backup in a spreadsheet program.** Excel truncates at 32,767 characters per cell, and re-saving a partially loaded file loses everything that was not loaded.
- **The exported file re-imports as exported.** That is what makes it a Backup rather than a record, and it is why it must not be edited.

Record the job and the downloaded file path, then hand the values to `convert.py backup-write` so the Run's Backup has the same shape in both modes.

## Why a blank cell is the whole point

Matrixify's metafield rule: *"If the value is empty, then this Metafield for that item will be deleted (not set to empty value, but deleted)"*, and a product with no metafield exports blank.

Read together, re-importing an untouched export restores **absent** correctly — the one thing a native Shopify CSV round-trip cannot do, because it writes a blank cell as an empty value instead.

It also means a blank cell in an import file is a deletion instruction. Never hand Matrixify a file with an unintended blank.

## The write is an import

Build the import file on disk from the Converted values — never by pointing Matrixify at the Source sheet. The Source sheet's columns are not Matrixify's columns, and the sheet stays read-only.

The file carries `Handle`, the mapped metafield columns, and a `Command` column.

- **`Command` stays `MERGE`.** `MERGE` finds the product and updates it. `REPLACE` deletes the product and recreates it from the file alone — it would destroy everything the file does not carry.
- Omit every column the Run is not writing.
- A field the Run is skipping gets no column at all, rather than a blank cell.

Matrixify → **New Import** → upload the file → run → watch the job in **All Jobs** until it reports complete, and read its result rather than assuming success.

## Do not schedule it

Matrixify can repeat an import on a schedule, and a URL-sourced job re-reads its source every run. Combined with the blank-cell rule, a schedule pointed at a live sheet is a **standing destructive write**: anyone clearing a cell deletes that metafield on the next tick, with no human in the loop.

One-shot imports only.

## Reading a sheet directly, and why this skill does not

Matrixify can read a Google Sheet by URL, which would remove the clipboard read entirely. It needs two sharing settings — "Anyone with the link can view" **and** the cogwheel's "Viewers and commenters can see the option to download, print, and copy", without which Google returns a 400 — and the tab is addressed by **name**, not by the `gid` in the URL.

This skill does not use it, because the Source sheet's columns are the client's working columns, not Matrixify's, and converting them in the sheet would mean writing to the sheet. The conversion belongs in `convert.py`, where it is tested.

## Undo

`convert.py backup-read` splits the Backup into `restore` and `delete`. In this mode both go back in one import: the `restore` entries carry their values, and the `delete` entries carry a blank cell, which Matrixify turns into a deletion.

That is the same file the export produced, so an Undo of a Run that has not been followed by another Run is simply: re-import the Backup, unedited, with `Command` set to `MERGE`.
