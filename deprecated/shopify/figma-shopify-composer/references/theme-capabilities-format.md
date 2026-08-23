# THEME-CAPABILITIES.md — format spec, format 1

The capability catalog's shape. Every skill that produces this doc reproduces the block below, so a consumer reads one shape whichever skill wrote it.

This file is duplicated byte-identical inside each producer skill. A change lands in every copy in the same commit. It repeats its sibling spec on the header, the version ladder, the gate, and sharding for the same reason: a skill that produces only one of the two docs ships only one of the two files, so each stands alone.

## Contents

- [The block to reproduce](#the-block-to-reproduce) — emit this, filled
- [Header fields](#header-fields) — what each line carries
- [Row schemas](#row-schemas) — what one row is, per section
- [Format version](#format-version) — which doc a producer regenerates, refreshes, or leaves alone
- [Incremental refresh](#incremental-refresh) — updating the entries that changed
- [Completeness gate](#completeness-gate) — the check every write and merge faces
- [Sharding](#sharding) — one definition, above 400 files

## The block to reproduce

Everything between the fences is the doc. Reproduce it top to bottom, replace every `<…>`, and keep each heading's exact text and order. Rows repeat; headings do not.

```markdown
---
format: 1
generated: <YYYY-MM-DD>
skill: <producing skill> (<agent role>)
theme: <theme name and version>
git: <branch> @ <short SHA>
scanned: sections <N> · blocks <N> · globals <N> · inheritance <N> · templates <N>
refresh: user says "refresh theme capabilities" → regenerate
updates:
---

# THEME CAPABILITIES — <Client> theme

## §Globals
| group | id | type | options / range | default | variable | paints |
|---|---|---|---|---|---|---|
| <group> | `<id>` | <type> | <options or range> | <declared default> | <`--var`, path:line> | <property + surface, path:line> |

## §Section catalog
| file | display name | settings | blocks | presets | responsive | per-instance CSS/Liquid |
|---|---|---|---|---|---|---|
| `sections/<name>.liquid` | <schema name> | <id:type=default · …> | <type(<ids>) · …> | <preset name · enabled_on> | <ids> | <ids> |

## §Theme blocks
| file | display name | settings | presets | responsive | per-instance CSS/Liquid |
|---|---|---|---|---|---|
| `blocks/<name>.liquid` | <schema name> | <id:type=default · …> | <preset name> | <ids> | <ids> |

## §Inheritance
| section/block | setting | binding | resolves to | evidence |
|---|---|---|---|---|
| `sections/<name>.liquid` | `<id>` | <global \| variable \| raw> | <global id, `--var`, or the literal> | <path:line> |

## §Conventions
| aspect | convention | evidence |
|---|---|---|
| <aspect> | <the convention, stated so a new file can follow it> | <path:line> |

## §Block architecture
| aspect | answer | evidence |
|---|---|---|
| <aspect> | <answer> | <path:line> |

## §Metafield patterns
| owner.namespace.key | type | read by | access pattern |
|---|---|---|---|
| <owner>.<namespace>.<key> | <type> | `sections/<name>.liquid` | <Liquid expression> (<path:line>) |

## §CSS load
| asset | loaded from | how | scope |
|---|---|---|---|
| `assets/<name>.css` | <path:line> | <the tag or render call> | <every page \| <template> \| <section>> |
```

Everything from here down explains that block. It is read, never emitted.

## Header fields

Both knowledge docs carry these eight fields in this order. `scanned:` and `refresh:` are the only two whose content differs between them.

| field | carries |
|---|---|
| `format:` | the integer this spec's title names. A producer writes the version it emits, which is the version it was written to. |
| `generated:` | the absolute date the doc was last written or refreshed, `YYYY-MM-DD`. |
| `skill:` | one producing skill and its agent role. One value — later runs record themselves in `updates:`. |
| `theme:` | the theme's name and version, from `config/settings_schema.json`'s `theme_info` group. |
| `git:` | the branch and short SHA the scan read, `<branch> @ <sha>`. |
| `scanned:` | five counts, taken at scan time: `sections/*.liquid` (the `.liquid` files only — section-group JSON is placement, and rows in §Conventions), `blocks/*.liquid`, setting ids in `config/settings_schema.json`, the colour, typography, radius and border settings §Inheritance owes a row each, and `templates/**/*.json` counted recursively. The gate recomputes all five counts; row counts reconcile the first four, while `templates` remains the scale context §Conventions reads. |
| `refresh:` | the phrase that forces a regenerate, verbatim: `user says "refresh theme capabilities" → regenerate`. |
| `updates:` | the home for dated append lines. Empty at generation. |

### `updates:` — where a later run records itself

A skill that adds a section, block, or setting appends its entry to the affected table and then adds one line here:

```
updates:
  - 2026-08-04 figma-shopify-builder — §Section catalog: added `sections/gw-hero.liquid`
  - 2026-08-05 figma-shopify-globals — §Globals: 7 defaults synced from the design
```

One line per run, newest last, each naming its date, its skill, and the section it touched. Every other field holds exactly one value, so the doc's history has one home and the header stays greppable.

## Row schemas

Every section is a table. A section with nothing to record carries exactly one row whose first cell reads `none — <reason>` and whose remaining cells are empty, so absence is stated rather than left to inference.

A literal pipe inside a cell is written `\|`, so the row keeps its cell count: a Liquid filter written `{{ settings.x \| default: 'y' }}` stays one cell, where a bare `|` splits the row and the row is lost.

### §Globals — one row per setting id

One row for every setting id in `config/settings_schema.json`, in schema order. This section answers *"is there already a global for this, and what does it paint?"*, which is the question the whole doc exists for.

A `color_scheme_group`'s roles are setting ids too, so each id inside its `definition` takes its own row: a theme whose colour lives in schemes rather than in flat settings keeps its real globals there, and a row per scheme group would hide every one of them.

| column | carries |
|---|---|
| group | the containing group's `name`, verbatim — a translation key stays a translation key |
| id | the setting id, backticked |
| type | the schema `type` |
| options / range | `select` and `radio` → every `value` joined by `\|`; `range` → `min..max/step<unit>`; other types → empty |
| default | the schema's declared `default`, verbatim; empty where the schema declares none |
| variable | the CSS custom property or Liquid assignment the setting becomes, with `path:line`; `none` where the setting never becomes one |
| paints | the rendered property and the surface it lands on, with `path:line`; `unreferenced` where nothing reads the setting |

`paints` is the consumer trace — found by searching the theme for `settings.<id>` and following it to the property it sets. Two worked rows:

```
| t:settings_schema.colors.name | `color_button_background` | color |  | #171717 | `--color-button-bg` (snippets/css-variables.liquid:24) | background of `.button--primary`, `.shopify-payment-button` (assets/base.css:412, :callout) |
| t:settings_schema.colors.name | `color_shadow` | color |  | #a8e8e2 | none | unreferenced |
```

The declared default is the schema's. Current values live in `config/settings_data.json`, which is merchant-volatile, so a consumer reads it live at the moment it needs a value.

### §Section catalog — one row per `sections/*.liquid`

| column | carries |
|---|---|
| file | the path, `sections/<name>.liquid`. A section group (`sections/*.json`) is placement rather than capability, so it appears in the §Conventions `settings usage` row instead |
| display name | the schema's `name`, verbatim, plus the resolved label where it is a translation key |
| settings | every setting the schema declares, `id:type=default`, joined by ` · `; `none` where it declares none |
| blocks | every block type with its setting ids, `type(id, id)`, joined by ` · `; `none` |
| presets | every preset name, plus `enabled_on` groups or templates where declared; `none` |
| responsive | the setting ids that differ per breakpoint — `columns_desktop`/`columns_mobile` pairs, mobile layout switches, per-breakpoint spacing and image behaviour; `none` |
| per-instance CSS/Liquid | the setting ids taking custom CSS or Liquid; `none` |

The full settings list is what makes a row usable — a consumer asks "can this section already do X?" and reads the answer off the row. One row per `sections/*.liquid` file, however small the section; section-group JSON is recorded in §Conventions, not here.

### §Theme blocks — one row per `blocks/*.liquid`

The §Section catalog columns, minus `blocks`. A theme with no matching `blocks/*.liquid` files carries the single `none — no blocks/*.liquid files` row.

### §Inheritance — one row per colour, typography, radius, or border setting

| column | carries |
|---|---|
| section/block | the file the setting is declared in |
| setting | the setting id, backticked |
| binding | `global`, `variable`, or `raw` |
| resolves to | the global's id, the `--custom-property`, or the literal value the setting takes per-instance |
| evidence | `path:line` for the resolution |

This is the section that tells a consumer whether correcting a global reaches a given section, or whether that section holds a raw per-instance value that wins over it.

One row per setting, and the header's `inheritance` count is that number — so a run that folds several settings into one row is caught here rather than passing as complete. The rows repeating `raw` against a literal are this section's most valuable content: each one is a place where correcting a global stops short.

### §Conventions — one row per aspect

A row for each of these six aspects, each stated so a new file can follow it: **schema style** · **CSS scoping** · **class naming** · **breakpoints** · **settings usage** (name every section-group JSON file in `sections/` and every `templates/**/*.json` file, with the combinations each actually uses) · **asset naming**. An aspect the theme is inconsistent about gets a row saying so, with both `path:line`s.

### §Block architecture — one row per aspect

A row for each of these four aspects: **`blocks/` directory** · **blocks in host schemas** · **shared block types** · **adding a new block**. The last is the instruction a build skill follows, taken from what the theme already does.

### §Metafield patterns — one row per metafield or metaobject a section reads

`access pattern` carries the Liquid expression verbatim, so a build skill copies it rather than deriving it.

### §CSS load — one row per stylesheet the theme loads

`scope` is `every page`, a template name, or a section name — whichever the load point makes true.

## Format version

A producer compares the doc's `format:` against the version in this spec's title.

| doc's `format:` | the producer's move |
|---|---|
| absent | regenerate in full — an absent version reads as 0 |
| lower | regenerate in full |
| equal | freshness-check it: `scanned:` counts and file lists against disk, `git:` against the current branch and short SHA. Fresh → read it. Changed → [incremental refresh](#incremental-refresh) |
| higher | read it as it stands, leave every byte, and say so in the run's output: *"`.agent/THEME-CAPABILITIES.md` is format `<n>`; this skill emits format `<this>`. Read as-is, left unchanged."* |

The higher case is how a doc keeps facts a producer cannot yet write. The producer still reads and uses it — a newer doc is a superset of what this spec asks for.

The user's refresh phrase overrides all four rows: it regenerates in full.

## Incremental refresh

An equal-version doc whose disk has moved on gets the changed entries rewritten and the rest kept byte-for-byte:

1. **Diff disk against the doc.** Files in `sections/*.liquid` and `blocks/*.liquid` against the `file` columns; `templates/**/*.json` against the header's recursive scan count; setting ids in `config/settings_schema.json` against §Globals; `git diff --name-only <doc's SHA>..HEAD` for files whose content moved.
2. **Write the rows that changed** — added files gain rows, deleted files lose theirs, changed files have their rows re-derived from the file. Untouched rows are left exactly as they are.
3. **Re-derive the whole-theme sections** — §Conventions, §Block architecture, §Metafield patterns, §CSS load — when any file feeding them changed; otherwise keep them.
4. **Update the header** — `generated:`, `git:`, `scanned:`, and one appended `updates:` line naming what was refreshed.
5. **Run the [completeness gate](#completeness-gate)** on the result.

A doc more than a third of whose rows would be rewritten is cheaper to regenerate in full; a producer takes that path and says which it took.

## Completeness gate

Run after any write, refresh, or merge — a doc that has not passed the gate has not been produced. Four checks:

1. **Headings and columns.** Each heading in the block to reproduce is present with its exact text, in that order, and the doc's `##` headings are exactly that set. Each table's header row matches the block's, cell for cell — this is what catches a §Globals that has a row per setting but no `paints` column.
2. **Counts reconcile against the header.** §Globals rows = `globals`. §Section catalog rows = `sections`. §Theme blocks rows = `blocks`. §Inheritance rows = `inheritance`. A header count of zero is met by that section's single `none — <reason>` row. A count that disagrees any other way is a shortfall in that section.
3. **Names reconcile against disk.** Every `.liquid` file in `sections/` appears in §Section catalog's `file` column; every `.liquid` file in `blocks/` in §Theme blocks'; every setting id in `config/settings_schema.json` in §Globals' `id` column; every section-group JSON file in `sections/` and every `templates/**/*.json` file appears in the §Conventions settings-usage row.
4. **Aspects and rows.** §Conventions carries a row for each of its six named aspects, §Block architecture for each of its four. Every remaining section carries at least one row — data, or the single `none — <reason>` row.

**A shortfall re-dispatches only the section that fell short**, with its check result quoted and the missing files or ids named, and the returned rows replace that section. Then the gate runs again on the whole doc.

A section still short after its second dispatch is recorded in the run's output — the section, its expected count, its actual count, and the names still missing — so what the doc is missing is declared rather than absorbed.

## Sharding

Above **400 `.liquid` files across `sections/` and `blocks/`**, the catalog is produced by 2–3 scanners instead of one. The largest theme catalogued unsharded holds 266 files — 235 sections and 31 blocks — and its catalog reconciled on every counted section, so the threshold sits above it; sharding handles scale, and the completeness gate handles thin docs at every scale.

- **§Section catalog, §Theme blocks, and §Inheritance split by file range**, each shard taking a contiguous slice of the sorted file list.
- **§Globals, §Conventions, §Block architecture, §Metafield patterns, and §CSS load are whole-theme sections** — shard 1 writes them.
- **Shards write to the run's working directory** as `THEME-CAPABILITIES-<n>.md`, each holding only its assigned sections with the same headings and row schemas.
- **The main agent merges** into `.agent/THEME-CAPABILITIES.md`: headings in the block's order, rows within a table in file order, one header assembled from the shards' counts.
- **The merged doc faces the completeness gate**, and a shortfall re-dispatches the one section that fell short.
