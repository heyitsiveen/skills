# The replication record

`.agent/shopify-page-replicate/replication.md` in the **Target theme** repo. One `##` entry
per replicated page, appended — never rewritten, so a repo with six Stand-ins holds six
entries in the order they were built.

The record does two jobs. It explains the page to whoever opens the template months later,
and it is the **retirement checklist**: everything a later build has to undo when the real
design for this page arrives. Nothing automates that undo; this file is what makes it
mechanical rather than archaeological.

Reproduce the block below, filling every field. Delete the parenthetical guidance, keep the
headings.

```markdown
## <target-template> — Stand-in

| Field | Value |
|---|---|
| Source page | <url as captured, including ?pb=0> |
| Source template | <templates/<file>.json, as derived from the page> |
| Target template | <templates/<file>.json> |
| Replicated on | <YYYY-MM-DD> |
| Design spec | .agent/shopify-page-replicate/visual-check/<name>/design-spec.md |
| Clip boundary | <the selector both captures used> |
| Structure source | Shopify CLI pull of the Source theme / DOM only |
| Sections removed from the target template | <list, or "none — template created by this run"> |

### Section map

(One row per entry in the new `order`, in render order. "Fidelity" is the forecast class the
plan approved for that section.)

| # | Target section type | Source section | Fidelity | Notes |
|---|---|---|---|---|

### Override table — the unwind list

(Every setting whose value departs from a Target theme global, and the global it departs
from. This is what a real design would put back. Font families are absent by construction:
they inherit.)

| Section instance | Setting id | Value written | Target theme global it departs from |
|---|---|---|---|

### Fonts

| | Source page | Written into the Stand-in |
|---|---|---|
| Heading family | <measured> | <Target theme global> |
| Body family | <measured> | <Target theme global> |
| Weights substituted | <measured weight → nearest available in the Target family, per element> |

### Assets

(Which pile each image fell into, and the counts that prove the sort.)

| Image | Pile | Reference |
|---|---|---|

### Replica files

(Every file Pass B wrote, by path, under the `replica-<template>-<name>` prefix — section files,
stylesheets and snippets alike — with the element each section was built to render and the
required settings that make it render nothing when empty. Empty where the run built nothing:
say "none — every gap was accepted as an approximation".)

| File | Renders | Required settings |
|---|---|---|

### Apps

(App blocks copied across, with their app. App embeds are untouched by construction — say so.
Any app injected into the Source theme's Liquid is named here as out of scope,
not attempted.)

### What is not the Source page

(Every UNACHIEVABLE element the forecast named, and every approximation that survived the
style report with a measured delta. This is the honest gap list — the reason a reader should
not treat the Stand-in as a faithful copy.)

### Retirement

- Replace `<target-template>` with the real design when it exists.
- Delete this entry and the visual-check folder `<name>/`.
- Revert every row of the override table to its global, or delete the section instance.
- Delete every file listed under **Replica files** — one
  `grep -rl 'replica-<template>'` finds them all, and nothing else depends on them.
- Delete their rows from `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md`.
```
