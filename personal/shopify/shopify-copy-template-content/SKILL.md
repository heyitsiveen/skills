---
name: shopify-copy-template-content
description: Use when the user wants to copy one or more SECTIONS or BLOCKS from a source Shopify template JSON file (e.g. `index.json`) into one or more sibling template JSON files (e.g. `product.json`, `product.in-stock.json`, `collection.json`, `page.*.json`), inserting them at a specified position. Triggers on a structured prompt with the keys `From:`, `Sections:` or `Blocks:`, `From Position:`, `To:`, `To Position:` — and on natural-language variants like "copy the X section from index.json to product.json after Y", "mirror the scrolling text + app block from index onto the product template", "duplicate this section into another template after Tabs FAQ", "add the same hero block to product.json and product.in-stock.json", "the section is missing on product.json, copy it from index.json". Use whenever the user is moving named JSON-template content between Shopify theme template files at a specific insertion point — even if they don't use the exact key format.
user-invocable: true
---

# Shopify Copy Template Content

Copy named sections or blocks from a source Shopify JSON template into one or more target templates at a specified position, without breaking JSON validity, without touching the source file, and without silently duplicating content.

This skill exists because the workflow has subtle traps that bite hand-rolled edits: Shopify wraps templates in a `/* ... */` comment header that vanilla JSON parsers reject, the `order` array must stay in sync with the `sections` object, and comma management on inserts (last entry vs. mid-array) silently invalidates the JSON. The bundled script handles all of that.

## Required inputs (parse from the user's message; ask if missing)

The user provides five inputs. Accept the structured form below OR equivalent natural language — both must work.

**Format A — Sections (top-level sections in a JSON template):**

```
From: @templates/index.json
Sections: "Scrolling text", "App wrapper"
From Position: After "Tabs FAQ"
To: @templates/product.json, @templates/product.in-stock.json
To Position: After "Tabs FAQ"
```

**Format B — Blocks (nested under a specific section):**

```
From: @templates/index.json
Blocks: "Promo banner", "Trust badge"
From Position: After "Hero"
To: @templates/product.json, @templates/product.in-stock.json
To Position: After "Hero"
```

Field meanings:

- `From` — single source file (relative to repo root). Leading `@` is decoration; strip it.
- `Sections:` OR `Blocks:` — comma-separated, quoted names. The skill's mode is determined by which key is present (sections vs. blocks). Names are the human-readable `"name"` field on each section/block (or fall back to the type if no name).
- `From Position` — disambiguates which instance to copy when multiple sections/blocks share a name in the source. Format: `After "<anchor name>"` or `Before "<anchor name>"`. Optional if names are unique.
- `To` — one or more target files, comma-separated.
- `To Position` — where to insert in each target. Same syntax as `From Position`.

If a required input is missing, ask the user in one `AskUserQuestion` call before proceeding. Do not guess.

## The workflow

1. **Parse the user's invocation** into `--from`, `--to`, `--sections` or `--blocks`, `--from-position-after`, `--to-position-after`, and (for blocks mode) `--parent-section`.

2. **Invoke the bundled script** from this skill directory:

   ```bash
   python "<skill-dir>/scripts/copy_template_content.py" \
     --from <source-path> \
     --to <target1,target2,...> \
     [--sections "Name 1,Name 2" | --blocks "Name 1,Name 2" --parent-section "Section Name"] \
     --from-position-after "<anchor name>" \
     --to-position-after "<anchor name>"
   ```

   The script prints a JSON summary to stdout when it finishes (`{"modified": [...], "skipped": {...}, "warnings": [...]}`), and a non-zero exit code on abort.

3. **Read the script's stdout** and **report back to the user** a concise summary of what changed and what was skipped. Always mention skipped duplicates explicitly — they may indicate the user is re-running a command unnecessarily.

4. **After the script succeeds**, remind the user about the Shopify auto-sync race: if their theme is connected to GitHub two-way sync, push the commit promptly and avoid making admin-side edits to the same templates until the sync round-trips through Shopify — otherwise admin can overwrite the additions on the next serialize.

## Behavior rules (these are enforced by the script — do not work around them)

- **Never modify the source file.** The source is the canonical reference. The script opens it read-only.
- **Copy in the order listed.** If the user wrote `Sections: "A", "B"`, the inserted order in each target is A then B, regardless of how they appeared in the source.
- **Skip duplicates, don't overwrite.** If a section/block with the same key already exists in a target, the script logs a warning and leaves the existing entry alone. This makes re-running the command idempotent.
- **Abort BEFORE writing if any source name fails to resolve.** Partial writes across multiple targets are worse than no writes — the operation is atomic across the entire `--to` list.
- **Update both the container AND the order array.** For sections: insert into `sections` and `order`. For blocks: insert into the parent section's `blocks` and `block_order`. The script never updates one without the other.

## Edge cases worth knowing

- **Shopify's comment header** — every JSON template starts with `/* ... */` warning that the file is auto-generated. The script strips it for parsing and re-prepends it on write. Do not strip it manually.
- **Section keys are template-scoped.** Reusing the same key (e.g. `scrolling_text_DieGnQ`) across `index.json` and `product.json` is legal and is the correct "copy" semantic. The script preserves source keys.
- **The "name" field is what the user sees in admin** — it's how the skill maps the user's `"Scrolling text"` to a section key like `scrolling_text_DieGnQ`. If a section has no `name` field, the script falls back to matching by `type`.
- **Multiple matches on a name** — if two sections share a name (rare but possible), the script needs `From Position` to disambiguate. If still ambiguous, the script aborts with a clear error listing the candidates.

## Examples

**Example 1 — Sections at end of target:**

User: `Copy "Scrolling text" and "App wrapper" from index.json (they're right after "Tabs FAQ") into product.json and product.in-stock.json after each file's "Tabs FAQ" section.`

Script call:
```
python copy_template_content.py \
  --from templates/index.json \
  --to templates/product.json,templates/product.in-stock.json \
  --sections "Scrolling text,App wrapper" \
  --from-position-after "Tabs FAQ" \
  --to-position-after "Tabs FAQ"
```

**Example 2 — Block within a section:**

User: `Add the "Promo banner" and "Trust badge" blocks from the Hero section in index.json to the Hero section in product.json, after the existing "Headline" block.`

Script call:
```
python copy_template_content.py \
  --from templates/index.json \
  --to templates/product.json \
  --blocks "Promo banner,Trust badge" \
  --parent-section "Hero" \
  --from-position-after "Headline" \
  --to-position-after "Headline"
```

**Example 3 — Re-running the same copy (idempotency):**

If the user re-runs Example 1, the script reports both targets as already containing the keys and exits without modifying any file. The output looks like:

```json
{"modified": [], "skipped": {"templates/product.json": ["scrolling_text_DieGnQ already exists"], "templates/product.in-stock.json": ["scrolling_text_DieGnQ already exists"]}, "warnings": []}
```

Tell the user the work was already done — they don't need to do anything else.

## What this skill does NOT do

- It does not create new sections from scratch — for that, see `shopify-add-section-or-preset-from-figma` or `shopify-build-section-or-block-from-figma`.
- It does not modify the source template — duplicating *within* one file requires a separate approach (rename the keys, since template-scoped keys would conflict).
- It does not adjust section settings during the copy — the destination gets the source's settings verbatim. If the user wants per-target customization, they edit the target after the copy lands.
