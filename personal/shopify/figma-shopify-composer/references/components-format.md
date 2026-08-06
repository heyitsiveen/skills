# COMPONENTS.md — format spec, format 1

The reuse inventory's shape. Every skill that produces this doc reproduces the block below, so a consumer reads one shape whichever skill wrote it.

This file is duplicated byte-identical inside each producer skill. A change lands in every copy in the same commit. It repeats its sibling spec on the header, the version ladder, the gate, and sharding for the same reason: a skill that produces only one of the two docs ships only one of the two files, so each stands alone.

## Contents

- [The block to reproduce](#the-block-to-reproduce) — emit this, filled
- [Header fields](#header-fields) — what each line carries
- [Row schema](#row-schema) — one schema, six categories
- [Which category a row belongs to](#which-category-a-row-belongs-to) — the six, and the rule that settles motion
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
scanned: custom-elements <N> · keyframes <N> · js-source <N> · snippets <N> · sections <N>
refresh: user says "refresh components" → regenerate
updates:
---

# COMPONENTS — <Client> theme reuse inventory

> Check here BEFORE writing new code: search by reuse keyword.
> Match → reuse or extend it. No match → build new under `{prefix}-` (AGENTS.md 🧩).

## Custom web components
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| `<tag-name>` | <definition · registration · markup contract> | <one line> | <search terms a build task would try> |

## JavaScript
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| <export or utility name> | <path> | <one line> | <search terms> |

## Functions
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| <snippet or filter name> | <path> | <one line, naming its parameters> | <search terms> |

## Flows
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| <flow name> | <every file in the sequence> | <the steps, in order> | <search terms> |

## Patterns
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| <pattern name> | <path(s)> | <one line> | <search terms> |

## Animations
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| <treatment name> | <path(s)> | <trigger · tech> — <one line> | <trigger words + search terms> |
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
| `scanned:` | five counts, taken at scan time: the tag names `customElements.define` registers — a loop over a list of names registers each name in it — named `@keyframes`, files in the JavaScript source tree, files in `snippets/`, `.liquid` files in `sections/`. The gate recomputes all five counts; it reconciles `custom-elements` against `## Custom web components`' data-row count and `keyframes` by name against `## Animations`. The three file counts also define the source scope an incremental refresh diffs against. |
| `refresh:` | the phrase that forces a regenerate, verbatim: `user says "refresh components" → regenerate`. |
| `updates:` | the home for dated append lines. Empty at generation. |

### `updates:` — where a later run records itself

A skill that builds a component appends its rows to the affected tables and then adds one line here:

```
updates:
  - 2026-08-04 figma-shopify-builder — Custom web components: added `<gw-carousel>`; Animations: added card-hover-lift
  - 2026-08-06 shopify-app-restyle — Animations: added synchrony-banner fade
```

One line per run, newest last, each naming its date, its skill, and the categories it touched. Every other field holds exactly one value, so the doc's history has one home and the header stays greppable.

## Row schema

All six categories share `name | file path(s) | what it does | reuse keywords`.

| column | carries |
|---|---|
| name | what a build task would call the thing — a tag name backticked, an export, a snippet name, a flow's common name |
| file path(s) | every file the item lives in: definition, registration, and the markup contract that shows it in use, joined by ` · ` |
| what it does | one line, concrete enough to decide reuse from |
| reuse keywords | the synonyms a build task would search — `carousel, slider, slideshow, scroll` |

One row per item, exhaustive: a minor item gets a thin row, and the row is what makes it findable. `reuse keywords` is the column the doc is searched by, so it carries the words a *future* task would type rather than the words this file uses.

A literal pipe inside a cell is written `\|`, so the row keeps its four cells: an attribute value written `data-cart-type="drawer\|page"` stays one cell, where a bare `|` splits the row into five and the row is lost.

## Which category a row belongs to

Six categories, in this order:

| category | holds |
|---|---|
| **Custom web components** | every `customElements.define` registration |
| **JavaScript** | reusable scripts and utilities not tied to one component — debounce, cart-AJAX, focus traps |
| **Functions** | reusable Liquid utility snippets and filters — parameterized snippets, money and class-list helpers |
| **Flows** | multi-step interaction sequences — add-to-cart, quick-view, facet filtering |
| **Patterns** | recurring structural and design patterns — sticky header, drawer, modal, wave separators, sold-out state |
| **Animations** | reusable or recurring motion and state-transition treatments — named `@keyframes`, shared animation classes, IntersectionObserver and scroll reveal systems, loading indicators (skeleton, spinner, button-loading), and recurring conventions such as "cards lift on hover" |

**Motion homes in Animations whatever its tech or host.** An IntersectionObserver reveal utility rows in Animations, not JavaScript; a skeleton shimmer rows in Animations while the skeleton's layout rows in Patterns. The host Pattern or Flow row cross-references the animation by name, so each fact keeps one home. A per-element transition earns a row once it recurs.

Animations rows open `what it does` with trigger and tech — `scroll · IntersectionObserver`, `hover · CSS transition` — and repeat the trigger words in `reuse keywords`, because that is what a motion task searches for.

Two worked rows:

```
| scroll-reveal | `assets/reveal.js` · `.reveal` in `assets/base.css:88` | scroll · IntersectionObserver adds `.is-visible`, CSS fades and translates in — used across landing sections | reveal, scroll, fade in, entrance, animate on scroll |
| card-hover-lift | `assets/base.css:412` (`.card`) | hover · CSS transition — card lifts and gains shadow, shared by every card grid | hover, lift, card, shadow |
```

**Sources**, all from the theme scan: `customElements.define` registrations · util and helper exports · parameterized snippets and filters · event and fetch sequences · repeated section and CSS structures · named `@keyframes` and transition rules · IntersectionObserver and scroll-library wiring · loading-state classes and markup.

A category with nothing to record carries exactly one row whose first cell reads `none — <reason>` and whose remaining cells are empty, so absence is stated rather than left to inference.

## Format version

A producer compares the doc's `format:` against the version in this spec's title.

| doc's `format:` | the producer's move |
|---|---|
| absent | regenerate in full — an absent version reads as 0 |
| lower | regenerate in full |
| equal | freshness-check it: `scanned:` counts and file lists against disk, `git:` against the current branch and short SHA. Fresh → read it. Changed → [incremental refresh](#incremental-refresh) |
| higher | read it as it stands, leave every byte, and say so in the run's output: *"`.agent/COMPONENTS.md` is format `<n>`; this skill emits format `<this>`. Read as-is, left unchanged."* |

The higher case is how a doc keeps facts a producer cannot yet write. The producer still reads and uses it — a newer doc is a superset of what this spec asks for.

The user's refresh phrase overrides all four rows: it regenerates in full.

## Incremental refresh

An equal-version doc whose disk has moved on gets the changed entries rewritten and the rest kept byte-for-byte:

1. **Diff disk against the doc.** The `scanned:` counts against fresh greps for `customElements.define` and `@keyframes`; the source, snippet, and section file lists against the `file path(s)` column; `git diff --name-only <doc's SHA>..HEAD` for files whose content moved.
2. **Write the rows that changed** — new items gain rows, deleted files lose theirs, changed files have their rows re-derived from the file. Untouched rows are left exactly as they are.
3. **Update the header** — `generated:`, `git:`, `scanned:`, and one appended `updates:` line naming what was refreshed.
4. **Run the [completeness gate](#completeness-gate)** on the result.

A doc more than a third of whose rows would be rewritten is cheaper to regenerate in full; a producer takes that path and says which it took.

## Completeness gate

Run after any write, refresh, or merge — a doc that has not passed the gate has not been produced. Four checks:

1. **Headings and columns.** Each heading in the block to reproduce is present with its exact text, in that order, and the doc's `##` headings are exactly that set. Each table's header row matches the block's four columns, cell for cell.
2. **Counts reconcile against the header.** Recompute every `scanned:` count from the theme before the gate passes: registrations, named `@keyframes`, JavaScript source files, snippet files, and section files. The recomputed counts must match the header. `## Custom web components` data rows = `custom-elements`; when that count is zero, its single `none — <reason>` row is the required sentinel rather than a data row. The three file counts are scope checks, not semantic row counts.
3. **Names reconcile against disk.** Every tag name passed to `customElements.define` appears in `## Custom web components`' `name` column, and every named `@keyframes` appears somewhere in `## Animations` — in a `name` cell, a `what it does` cell, or a `file path(s)` cell, since one treatment may drive several keyframes.
4. **Rows.** Every category carries at least one row — data, or the single `none — <reason>` row.

**A shortfall re-dispatches only the category that fell short**, with its check result quoted and the missing names listed, and the returned rows replace that category. Then the gate runs again on the whole doc. (This doc's headings carry no `§`; the capability catalog's do. Each gate greps the headings its own block emits.)

A category still short after its second dispatch is recorded in the run's output — the category, its expected count, its actual count, and the names still missing — so what the doc is missing is declared rather than absorbed.

## Sharding

The JavaScript side and the Liquid/CSS side are always two scanners: they read different trees for the same six categories, and Flows, Patterns, and Animations arrive split across the two and merge by feature. That is the topology at every size.

**Between them the two sides read every file the theme ships** — the JavaScript source tree on one side; every Liquid file (`sections/`, `blocks/`, `snippets/`, `layout/`, `templates/`) and every stylesheet on the other, the inline `<script>` and `<style>` those files carry included, since a file belongs to the side that reads it. The gate reconciles `customElements.define` and `@keyframes` against the whole theme, so a tree assigned to neither side surfaces as a shortfall — in practice a `@keyframes` in `blocks/` or a carousel wired inline in a section.

Above **400 `.liquid` files across `sections/` and `blocks/`** — the same threshold on the same measure as the capability catalog, so scale is handled identically wherever it is triggered — each side splits further into 2–3 shards by file range. The largest theme catalogued unsharded holds 266 files — 235 sections and 31 blocks — and its catalog reconciled on every counted section, so the threshold sits above it; sharding handles scale, and the completeness gate handles thin docs at every scale.

- **Each shard takes a contiguous slice** of its side's sorted file list and reports rows for every category its slice contains.
- **Shards write to the run's working directory** as `COMPONENTS-<n>.md`, each holding only the categories its slice produced, with the same headings and row schema.
- **The main agent merges** into `.agent/COMPONENTS.md`: headings in the block's order, one table per category, rows merged by feature so a flow split across shards lands as one row naming every file in the sequence.
- **The merged doc faces the completeness gate**, and a shortfall re-dispatches the one category that fell short.
