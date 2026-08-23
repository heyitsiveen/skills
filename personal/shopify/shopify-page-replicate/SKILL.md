---
name: shopify-page-replicate
description: Replicate a page from a client's current theme onto their revamped theme as a temporary stand-in, built from the revamped theme's EXISTING sections and configured to match the old page — for pages the revamp has not redesigned yet, where no Figma frame exists. Use when the user points at a live or preview page URL and wants that page rebuilt on another theme of the same store, or asks to replicate/recreate/stand in a page that has no new design. Recreating a design from Figma frames is figma-shopify-composer's job; moving sections between templates inside ONE theme is shopify-copy-template-content's. Where the theme's own sections cannot reach the page, a replica section is written only when the user chooses that over the closest approximation. The build reads from a design spec extracted from the rendered page, keeps the page's own colors and spacing while inheriting only the target theme's fonts, and reports computed styles against that spec.
---

# Shopify Page Replicate

**Replicate** a **Source page** onto the **Target theme** as a **Stand-in** — a page holding
a template's place until a real design exists for it. Same client, same store, two themes:
the revamp is unfinished, this page has no new design, and the Target theme cannot ship a
template that renders nothing. So the page is rebuilt from the sections the Target theme
already ships, configured to look like the page the client already approved.

Four phases — research (read-only on the Target theme), plan (stop 1, for approval), build
(any chosen replica sections, then the template JSON), render and report — then cleanup that
leaves the machine as found.
Nothing is created or modified before approval except knowledge docs under `.agent/`
(§Knowledge docs) and the revert of a hardcode a previous session stranded (§Phase 1); the
deliberate leftovers are the visual-check folder, the replication record, and the knowledge
docs.

A Stand-in is temporary by intent. That is why it is built from what exists rather than from
new code — and why new code, where the user chooses it, is one deliberate decision per section
rather than the run's default (§Replica sections). Everything it costs is written down
(§The replication record).

## Inputs

Collect both before starting; ask for either that is missing.

1. **Source page URL** — the page to replicate, on the Source theme. Public, or a preview URL
   (`?preview_theme_id=<id>`) for an unpublished Source theme.
2. **Target template** — e.g. `templates/page.about.json`. Created if it does not exist.

There is deliberately no placement input: a page occupies the whole template, so the target
template's entire `order` is replaced. There is no data-source input: content is entered as
theme-editor setting values matching the Source page — the existing sections' own settings, and
any replica section's. One page per run — six pages is six runs, so the plan the user approves
is one they can read end to end.

The **source template** is derived from the page, never asked for (§`references/source-page-capture.md`).
The storefront password is asked for once, and only when the store is closed.

## The build surface

The build is configuration first, and code only where the user asks for it:

- **Pass A — compose**, always: the target template JSON. NO new settings on the Target theme's
  own sections, NO schema edits to them.
- **Pass B — build**, only for the sections chosen at stop 1: new files of its own, every one
  carrying the `replica-<template>-<name>` prefix (§Replica sections).
- The Target theme's own section, block, snippet, CSS and JS files are READ-ONLY throughout,
  either pass. Nothing existing is edited to make room for a replica section.
- The other writable surfaces: the `.git/info/exclude` line for `.agent/`; `.claude/launch.json`
  if planned; and the `.agent/` tree — knowledge docs, the replication record, and
  `.agent/shopify-page-replicate/visual-check/`.
- The one exception is transient: the render's `vh-tmp-` assets, which live in the theme's
  `assets/` only between the hardcode and its revert (§Hardcode-then-revert). The build
  surface is what SURVIVES the run.
- The Source theme is never written to. It is read, and only where the Shopify CLI reaches it.

Where the Target theme genuinely cannot produce something, the forecast marks it UNACHIEVABLE
and stop 1 offers the choice: accept the closest approximation, or have a replica section built
for it. Accepting is the default, and nothing is built to close a gap the user did not choose to
close — the style report names those instead.

## Replica sections — built only when chosen

Every element the fidelity forecast marks UNACHIEVABLE reaches stop 1 as a choice: accept the
closest approximation with its visible cost, or have the section built as a **replica section**
— a new section file this run writes for this page alone.

**Accepting the approximation is the default**, and the choice is per section. A Stand-in is
temporary: a later build replaces it, and every line of section code written for one is thrown
away with it. How much of that this page is worth is the user's call, not the run's, so silence
is a no.

Choosing at least one opens **stop 2** at the head of Phase 3, covering only those sections
(§Phase 3). Choosing none skips that stop entirely and the run keeps its single one.

**Every file Pass B writes carries the `replica-<template>-<name>` prefix** — section file,
stylesheet and snippet alike: `sections/replica-page-about-hero.liquid`,
`assets/replica-page-about-hero.css`, `snippets/replica-page-about-hero-item.liquid`. One
`grep -rl 'replica-<template>'` then returns the whole Stand-in, which is what makes retiring it
mechanical rather than archaeological.

**Theme-editor settings only.** A replica section's content is its own schema settings, carrying
the design spec's values as defaults where the setting type allows one. There is no metafield and
no metaobject path: a Stand-in that needs data created in admin before it renders is a Stand-in
that does not render. Sections only, never theme blocks — a repeated item is a block type inside
the replica section's own schema. Schema shape is verified via the Shopify dev MCP, not guessed.

**Half of the split, deliberately.** A replica section renders NOTHING when its required settings
are empty — in the theme editor and on the storefront alike, one branch, no `request.design_mode`
fork. There is no editor placeholder, and that is the decision, not an omission: a placeholder's
whole job is to invite a merchant to fill the section in, and nobody should be filling in a page
that is about to be replaced. Read the missing placeholder as this rule rather than as a bug to
fix.

Shopify still wraps the section in `<div id="shopify-section-…">`. Where theme CSS gives that
wrapper margin or padding, the plan closes the leftover gap, so a section rendering nothing
leaves no band on the page.

**Required settings are the user's call at stop 2**, never inferred from "this field is blank":
the minimum that leaves the section meaningless when empty — typically its primary copy — with
every other setting skip-only. Repeated items cascade: an item whose required settings are blank
is skipped on its own, and when no item survives, the whole section renders nothing.

## The design spec is the authority

`design-spec.md` — the **design spec** — is the single document the build reads from. Every
value configured into the template traces to it: the exact-values table, the desktop/mobile
differences, the layout intent, the clip boundary, the CSS custom properties, the
requirements list, and the asset inventory. It is extracted once, in Phase 1, approved inline
at the plan stop, and never re-derived mid-run; a value that is not in it is an OPEN QUESTION,
not a judgement call.

Its source is a rendered page rather than a design file. Nothing else about it changes: it is
still the single authority a build reads from, and still the thing the style report asserts
against.

The palette is fixed to what the Target theme already ships, so the plan states upfront what
will match EXACTLY, what APPROXIMATES, what is UNACHIEVABLE without new code, and — for each of
those — whether the user accepted the approximation or chose to have it BUILT; the user approves
that **fidelity forecast** before anything is written.

Accuracy is still the goal. It is not a claim the skill makes on its own behalf: the run ends
with a **style report** — computed styles against the design spec's values, each mismatch
reconciled against the forecast — plus the rendered result saved to the visual-check folder
next to the Source page captures, and the user judges the result by eye.

## Fonts inherit; nothing else does

The Stand-in takes the Target theme's heading and body **font families** from its globals,
and takes everything else from the Source page as per-instance values:

| | Source of truth | Why |
|---|---|---|
| Heading and body font family | the **Target theme's** globals | the revamp's type choice is settled and already applies store-wide |
| Font size, weight, line-height, letter-spacing | the **Source page** | the Target theme's type scale would silently rescale the layout being preserved |
| Colors, spacing, sizes, radii, borders | the **Source page** | written as per-instance values, matching what the client already approved |

This inverts the composer's standing preference for globally-inherited settings, deliberately.
A Stand-in exists precisely because no new design exists for the page: its numbers are the
only design it has, and giving it the Target theme's numbers would be a design decision
nobody made — and an unrecoverable one, because a page that never looked like its source
cannot be restored without re-running.

The cost of the inversion is an **override table** in the fidelity forecast, naming every
setting that departs from a Target theme global (§Phase 2). That table is the unwind list for
when the real design arrives, and it is carried into the replication record.

Where the Target theme's font family does not ship the weight the Source page uses, the
element is marked APPROXIMATES with the nearest available weight named. A silent substitution
would read later as a build defect.

A replica section obeys the same table: its schema defaults and its stylesheet carry the Source
page's numbers, and its type inherits the Target theme's heading and body families through the
theme's own variables rather than re-declaring a family of its own.

## Browser tiers

**Primary: the Claude Code Desktop Browser pane** (desktop app with Browser enabled). Claude
drives it directly — screenshots, DOM/computed-style inspection, interaction — and manages
the dev server via `.claude/launch.json` (local dev servers need no site approval; the Source
page and preview/live store URLs are external sites and trigger a one-time permission card —
Allow once / Always allow). When available, it does the whole capture job, both sides.

**Fallbacks, in order:** connected browser MCP (Chrome DevTools MCP / Playwright MCP) →
installed Chrome → temporary Playwright via npx.

## Delegation

Bounded research and measurement go to subagents — isolated workers with their own context
windows that return only a final report. Delegation earns its keep most in the capability
inventory: scanning every section's schema would otherwise flood the main conversation.
Delegation multiplies tokens: skip it for trivially small reads.

Prefer the named custom agents `page-extractor`, `theme-scanner`, and `style-reporter` when
installed in `~/.claude/agents/` or `.claude/agents/` — their definitions add tool-enforced
restrictions (e.g. `disallowedTools: Write, Edit` on the style reporter). Otherwise run the
built-in general-purpose subagent with the embedded prompts below; in that fallback the
no-theme-edits rule is instruction-enforced, so each prompt states it explicitly.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the
browser tools reach subagents (subagents inherit internal + MCP tools by default; the Browser
pane's preview tools may be main-session-only). Any role whose tools don't reach a subagent
runs in the main conversation instead — which for the page extractor is the likely case, and
is a reassignment rather than a problem.

**Handoff protocol:** subagents can't see the conversation and can't ask the user questions —
every delegation prompt carries its exact inputs (the Source page URL, file paths, the design
spec's path, the approved fidelity forecast, capture specs); every worker writes FULL findings
to a report file in the temp working directory (the capability scanner writes its knowledge
doc instead, and the two reuse scanners write the shards the main agent merges into theirs —
§Knowledge docs) and returns a short summary; ambiguities come back as OPEN QUESTIONS for the
main agent to put to the user. The temp working directory is created per run (use the session
scratchpad when available) and is deleted at cleanup.

**Never delegated:** the requirements-to-capabilities matching (1c — the synthesis that feeds
the fidelity forecast), planning and every user approval (the design spec, the forecast, the
removal list, the accept-or-build choice, each replica section's schema), all implementation
edits, and the correction round that follows the style report.

| Role | Phase | Report |
|---|---|---|
| page-extractor | 1a, parallel | `design-spec.md` — the design spec |
| theme-scanner — capability catalog | 1b, parallel | `.agent/THEME-CAPABILITIES.md` (canonical; shards `{temp-dir}/THEME-CAPABILITIES-<n>.md`, merged into it by the main agent) |
| theme-scanner — reuse inventory, JavaScript side | 1b, parallel | `{temp-dir}/COMPONENTS-<n>.md` |
| theme-scanner — reuse inventory, Liquid/CSS side | 1b, parallel | `{temp-dir}/COMPONENTS-<n>.md` (every side's report merged into `.agent/COMPONENTS.md` by the main agent) |
| style-reporter (never edits theme files) | 4, once per breakpoint, plus the correction round's re-check | `style-report-<breakpoint>.md` |

All three scanners are read-only on the theme, and each dispatches only when its doc is absent
or stale (§Knowledge docs). The two reuse scanners share one doc, so they stand or dispatch
together — except in INCREMENTAL, where a side whose tree holds no changed entry stands down
and its half of the doc is kept byte-for-byte, its rows and its share of the header's counts
carried into the merge so the gate still measures the whole theme.

### page-extractor prompt

```
You are extracting a design spec from a RENDERED Shopify page — the Source page — which
will be replicated on a different theme of the same store from that theme's EXISTING
sections, plus new section code only where the developer explicitly chooses it. Every value
must be exact. Work only in the browser and, where it reaches, a Shopify CLI pull of the
Source theme; do not modify anything.

Source page: {source-page-url}
Breakpoints: 1440px and 390px, both fixed.

Procedure: {skill-dir}/references/source-page-capture.md
Read it in full before opening a browser and follow it exactly — reaching the page, the
`?pb=0` suppression, the clip boundary, the full scroll, the per-section computed-style
read, and the Shopify CLI upgrade. It is the source of HOW to read the page; this prompt is
the source of WHAT to write down.

This document is the DESIGN SPEC: the single authority the build reads from. Nothing is
re-read from the Source page later, so anything the build needs must be in it — and
anything you are unsure of is an OPEN QUESTION, never a guess.

Compile:
1. Exact-values table per breakpoint, PER SECTION: typography (family, size, weight,
   line-height, letter-spacing), colors, spacing (padding/margin/gap), sizes,
   border-radii, borders, image dimensions, content width. These are the
   settings-configuration targets AND the expected values for computed-style assertions —
   record exactly.
2. The clip boundary: the selector you captured, every `#shopify-section-*` id inside it in
   render order, and confirmation that the header and footer are outside it.
3. Section structure: one entry per section in render order — its `type` where the CLI pull
   or the DOM gives it, its rendered copy VERBATIM (typos, casing, em-dashes and leading
   spaces included), its images and videos, and whether an app owns any of its output.
4. Layout structure per breakpoint and every desktop vs mobile difference (column counts,
   stacking, order, visibility, alignment — e.g. 2 columns on desktop → 1 column on
   mobile). Responsive behaviour is built deliberately from this table, not rediscovered.
5. CSS custom properties: the properties in scope on each section wrapper and on `:root`,
   with their computed values. A value resolving from a named property is closer to design
   intent than the hex it computes to.
6. Typography rows carry TWO font families: `measured` — what the Source page renders — and
   `target-global` — the Target theme's heading or body global that will replace it. Leave
   `target-global` as TBD; the main agent fills it from the Target theme's globals. Both
   families stay in the row: the style report asserts against the second, and without the
   first the substitution looks like an error later.
7. Asset inventory — one row per image or video: where it is used | its `src` | rendered
   w×h | whether the src is a Shopify Files/CDN URL or an asset of the Source theme itself.
   That last column decides how it moves (the run re-uploads only the second kind).
8. The REQUIREMENTS LIST — the distilled page: section order; each content element
   (headings, text, CTAs/buttons, images, badges, app regions); each style requirement
   (colors, typography, radius, borders, spacing, alignment).

Sections 3 and 4 are WRITTEN FROM THE SCREENSHOTS — read the images, describe what the page
actually does — and EVERY claim in them is backed by a computed value, cited inline. A claim
you cannot back with a value is an OPEN QUESTION, not an assertion. The screenshots are the
source of the structure; the computed styles are the source of the numbers.

Open the document with this header line, verbatim, before section 1:

    producer: shopify-page-replicate — write surface: the target template JSON, plus
    any replica-<template>-* files the plan approves — the Target theme's own sections,
    blocks, snippets, CSS and JS are read-only

Write the FULL findings to {temp-dir}/design-spec.md with an OPEN QUESTIONS section at the
end for anything ambiguous, and the two screenshots to {temp-dir}/source-desktop.png and
{temp-dir}/source-mobile.png. Return only a 3–5 line summary plus the open questions —
including whether the Shopify CLI pull succeeded, since a DOM-only structure read is a
recorded downgrade.
```

### theme-scanner prompts — one per doc

Each opens with the absolute path of its format spec and the same instruction: **read that
spec in full before writing a byte of the doc, and reproduce the block it gives.** The doc's
shape, its row schemas, and the sources to sweep are the spec's; the prompt carries the run.

**Capability catalog:**

```
You are cataloging what a Shopify theme's existing sections, blocks, and settings can
already do. A page from another theme of the same store will be replicated from those
capabilities wherever they reach — so what you catalog decides what is achievable without
new code, and every gap you leave unrecorded reads later as a gap in the theme.
READ-ONLY on the theme: your only write is the doc named below.

Format spec: {skill-dir}/references/theme-capabilities-format.md
Read it in full before writing a byte of the doc, and reproduce the block it gives. Every
fact a row carries is the spec's §Row schemas.

Theme repo: {repo-path}
Header `skill:` field: shopify-page-replicate (theme-scanner — capability catalog)
Read: config/settings_schema.json · every `.liquid` file in sections/ and blocks/ ·
section-group JSON for §Conventions · templates/**/*.json · layout/theme.liquid, the
CSS-variable snippet and the theme's stylesheets · every section that reads a metafield or
metaobject
Write to: .agent/THEME-CAPABILITIES.md
Mode: {FULL | INCREMENTAL — refresh only these entries: {list}}
Scope: {whole theme | shard {n} of {total} — {file range}, written to
{temp-dir}/THEME-CAPABILITIES-{n}.md instead, holding your sections only — the main agent
assembles the merged header from every shard's counts}

PER-RUN — return in your summary, never in the doc:
1. Whether {target-template} exists, and if it does, its whole `order` array — the list of
   sections this run will REMOVE.
2. The heading and body font family globals, with the weights each family ships.
3. Whether .git/info/exclude carries a `.agent/` line.

Return only a 3–5 line summary, each section's row count, the per-run findings, and the
open questions.
```

**Reuse inventory, JavaScript side:**

```
You are inventorying what a Shopify theme already ships, JavaScript side, so a page
replication can tell which existing sections carry a page's behaviour and motion.
READ-ONLY on the theme: your only write is the report named below.

Format spec: {skill-dir}/references/components-format.md
Read it in full before writing a byte of the report, and reproduce the block it gives,
holding the categories your tree produced. Which category a row belongs to, and the sources
to sweep, are the spec's.

Theme repo: {repo-path}
Header `skill:` field, for the merged doc: shopify-page-replicate (theme-scanner — reuse
inventory)
Read: the JavaScript source tree
Write to: {temp-dir}/COMPONENTS-{n}.md, holding the categories your tree produced — the
main agent merges every side's report into .agent/COMPONENTS.md and assembles the header
from their counts
Mode: {FULL | INCREMENTAL — refresh only these entries: {list}}
Scope: {the whole tree | shard {n} of {total} — {file range}}

Return only a 3–5 line summary, each category's row count, the header counts your tree
yields, and the open questions.
```

**Reuse inventory, Liquid/CSS side:** the same prompt with every Liquid file — `sections/`,
`blocks/`, `snippets/`, `layout/`, `templates/` — and every stylesheet as the tree it reads,
and its own report number. Between them the two sides read every file the theme ships, which
is what the gate measures against.

### style-reporter prompt

```
You are producing the style report for one breakpoint of a replicated Shopify page — the
Target theme's existing sections configured via template JSON, plus any replica sections the
plan approved — built from a design spec extracted from a rendered Source page. You NEVER
edit theme files — no Write, no Edit, no shell command that changes a theme file. Your ONLY
writes are the result screenshot and the report file named below. Capture, assert, reconcile, report.

Breakpoint: {desktop|mobile}, width {1440|390}px
Render at: {dev-server-url | preview-url}
Clip to: {the Target theme's equivalent of the design spec's clip boundary} — the
template's own sections, never the header or footer
Design spec (the expected values): {temp-dir}/design-spec.md
Fidelity forecast, from the approved plan: {element → EXACT | APPROXIMATES (with the
forecast delta) | BUILT (a replica section renders it) | UNACHIEVABLE}
Capability map for tagging: .agent/THEME-CAPABILITIES.md + the approved settings map
Key elements to assert: {the forecast's EXACT, APPROXIMATES and BUILT elements, from the
approved plan, GROUPED BY SECTION} — elements forecast UNACHIEVABLE are NOT asserted; list
them by name instead

1. Capture hygiene, then capture: viewport at the width above; animations/transitions
   disabled; full scroll then back to top so lazy content is present; wait for
   document.fonts.ready + network idle; clip to the region above, not the full page.
2. Computed styles: getComputedStyle on each key element vs the design spec's values
   (font-family/size/weight, line-height, letter-spacing, color, background, padding,
   margin, gap, border, border-radius). Assert font-family against the row's
   `target-global` family, NOT its `measured` family — the substitution is deliberate, and
   asserting the measured family would report every heading on the page as a mismatch and
   bury the real ones. Record every mismatch: section, element, property, expected, actual.
3. Reconcile each mismatch against the forecast for that element:
   - forecast EXACT → BROKEN FORECAST. The plan promised this value was fully achievable
     from existing settings, and it did not land. Tag it either "settings-fixable per the
     capability map" (name the setting) or "undeclared gap". This is a forecasting failure,
     not a build defect — say so.
   - forecast APPROXIMATES → APPROXIMATION, QUANTIFIED. Not a failure. Give the measured
     delta (expected vs actual, and the numeric difference) and whether it is within the
     delta the forecast described.
   - forecast BUILT → BUILD DEFECT. A replica section was written specifically to render
     this element exactly, so a mismatch is code this run owns and can edit. Name the
     replica section file.
4. Write the capture to .agent/shopify-page-replicate/visual-check/{name}/
   result-{breakpoint}.png, overwriting what is there. Generate no other render variant.

Write the FULL table to {temp-dir}/style-report-{breakpoint}.md, GROUPED BY SECTION in
render order, with a subheading per section: one row per mismatch — element | property |
expected | actual | forecast (EXACT / APPROXIMATES / BUILT) | reconciliation (BROKEN FORECAST
+ tag, the quantified delta, or BUILD DEFECT + the replica section file) — followed by the
UNACHIEVABLE elements named and excluded.
Report every mismatch: there is NO cap and no truncation, because a capped report reads as
complete when it is not. Return that table as TEXT only, plus the mismatch count split by
forecast class and by section. Return no images.
```

## Knowledge docs — scan once, reuse

`.agent/` at the Target theme repo root holds every durable artifact this skill suite
produces: shared knowledge docs at its root, per-skill outputs under `.agent/<skill-name>/`.
Knowledge docs are written for an AI reader — tables, exact identifiers (section filenames,
setting ids, types, defaults), composition rules and constraints, zero filler prose — and are
the one exception to "nothing before approval": each lands before the run continues — the
capability catalog as its scanner writes it, the reuse inventory as soon as the main agent
merges both sides — so the knowledge survives even an abandoned run.

This skill produces both shared docs and reads both:

| doc | what it answers here | shape |
|---|---|---|
| `.agent/THEME-CAPABILITIES.md` | what the Target theme's existing sections, blocks and settings can already do — the capability inventory 1c matches every Source page requirement against | [`references/theme-capabilities-format.md`](references/theme-capabilities-format.md) |
| `.agent/COMPONENTS.md` | what the Target theme already ships and where — its Flows, Patterns and Animations rows map a Source page requirement to candidate sections, motion included: reveals · hover treatments · loading states | [`references/components-format.md`](references/components-format.md) |

**Their shape comes from their format specs, not from this file.** Read the spec in full
before writing a byte of either doc, and reproduce the block it gives. Each spec carries that
block, the header fields, a row schema per section, the `format:` ladder deciding regenerate /
refresh / read-as-is, the completeness gate, and the sharding threshold.

Producing the reuse inventory rather than only consulting it is what keeps a run on a theme
without one from silently losing a signal this skill says it uses.

**A replica section earns a row in both docs**, appended at cleanup: one capability-catalog
entry and one reuse-inventory row per section the run wrote, each carrying the word **Stand-in**,
the instruction **do not reuse**, and the path to `.agent/shopify-page-replicate/replication.md`.
A replica section is built for one page and dies with it, so a later run that finds it must
neither reuse it as a capability nor rediscover it as a mystery.

**Read before any scan (main agent, at 1b):**

1. Read each doc where it exists and run its spec's §Format version against it. That ladder
   decides FULL, INCREMENTAL, read-as-fresh, or read-as-newer — per doc, independently.
2. Dispatch only the scanners the ladder leaves standing: a doc read as fresh or read as
   newer stands its scanner(s) down, and a doc read as newer is named in the final output as
   read-as-is. A stood-down capability catalog still leaves the target template's `order`,
   the font globals, and the `.git/info/exclude` check to three small inline reads.
3. The scanners write BEFORE 1c matching continues — the capability scanner into its doc, the
   two reuse scanners into shards the main agent merges into theirs.
4. Run each written or merged doc's completeness gate (its spec's §Completeness gate) before
   1c reads it. A shortfall re-dispatches only the section or category that fell short; one
   still short after that second dispatch carries its expected count, actual count, and
   missing names into the final output.
5. An explicit user refresh always wins, per that doc's own refresh phrase: FULL rescan, doc
   rewritten.

**Root pointer:** the repo's root `AGENTS.md`/`CLAUDE.md` names this convention so future
sessions find the docs before rescanning. Missing → append it (or create a minimal
`CLAUDE.md` holding just this block, excluded like everything else) as a planned edit:

```
## 📚 Knowledge docs (check before any theme scan)
Skill outputs + knowledge docs live under `.agent/` — shared docs at its root,
per-skill outputs in `.agent/<skill-name>/`. Read `.agent/THEME-CAPABILITIES.md`
before any theme scan and search `.agent/COMPONENTS.md` before writing new
code; freshness checks + refresh instructions in their headers.
```

## The visual-check folder

`.agent/shopify-page-replicate/visual-check/<name>/` in the Target theme repo, `<name>`
kebab-cased from the target template (e.g. `templates/page.about.json` →
`.agent/shopify-page-replicate/visual-check/page-about/`). Its root holds the design spec and
two image classes:

- **The design spec**, at the folder root — `design-spec.md`, copied in from the temp
  directory at render start and retained, so the values this build was given survive the run
  and can be re-read when the client asks for a change months later.
- **Source page captures**, at the folder root — `source-desktop.png` / `source-mobile.png`,
  written once at render start. There is no `figma-` prefix here: the source is a page.
- **Clean renders**, at the folder root — `result-desktop.png` / `result-mobile.png`, written
  by the style reporter, one per breakpoint.
- No other render variant is generated. These whole-page files are what the user compares by
  eye.
- **Per-asset files**, in `assets/`, flat — the images the run had to move, and `UPLOAD.md`
  (§Asset capture).
- `HARDCODE-ACTIVE.md` — present only while a hardcode is live (§Hardcode-then-revert).

The folder is not theme code: `.agent/` stays out of git via a `.git/info/exclude` line
(confirm the `.agent/` line exists; append it as a planned edit if not — a local,
never-committed file, and the Shopify CLI ignores non-theme root directories, so it is never
pushed). At cleanup, the root retains only the design spec and the four image files above;
`assets/` remains for the user to review and upload, while `HARDCODE-ACTIVE.md` is deleted
after every revert.

## Asset capture — same store, two piles

The Source theme and the Target theme are on the same store, so most images need no work at
all. Every row of the design spec's asset inventory falls into exactly one of two piles:

| Pile | Recognised by | What the run does |
|---|---|---|
| **Already in Files** | a `cdn.shopify.com/s/files/…` src | keeps the existing reference — the same picture is never uploaded twice |
| **An asset of the Source theme** | a `cdn.shopify.com/s/files/…/assets/…` src, or any src resolving into the Source theme's `assets/` | downloads it, and stages it in the visual-check `assets/` for upload to Files, so it survives the move between themes |

The distinction is the src, not the eye: a theme asset dies when the Source theme is deleted,
a Files upload does not. Where a src is ambiguous — a third-party CDN, an app-served image,
a data URI — it is an OPEN QUESTION, not a coin flip.

**Prove the sort by count:** inventory rows equals pile-one rows plus pile-two rows, and
files staged in `assets/` equals pile-two rows. Name any miss. A silently dropped image is
the failure this count exists to catch.

**Source-quality flag:** where a downloaded asset is narrower than 2× its slot's rendered CSS
width, record it in the plan and the final output with both numbers. The remedy is better
source art, not a bigger upload.

Upload what was downloaded, unconverted: Shopify's CDN re-encodes to WebP or AVIF per browser
and per derivative on its own, so pre-converting only adds a generation of loss and no image
encoder ever reaches the ledger.

`assets/UPLOAD.md` closes the phase and keeps the folder self-describing once the run's temp
directory is gone:

```
UPLOAD THESE
<file>                  <w>×<h>  → <the section setting to assign it to>

ALREADY IN FILES — nothing to do
<existing Files reference>        <where it is used>
```

## Apps on the page

| What it is | What the run does |
|---|---|
| **An app block** in the source template's `order` or a section's `blocks` | copied straight across — same store, same installed apps, so the app that was on the page is still on the page |
| **An app embed** (store-wide, in `settings_data.json`'s `current.blocks`) | left alone. A page-level run does not touch store-wide app settings |
| **An app injected into the Source theme's Liquid** — a snippet, a hardcoded script tag, markup inside a section file | named in the plan and ROUTED to `shopify-inject-app-into-liquid`. Never attempted here |

The routing is proposed, never executed: the run names the skill, the app, and the element,
and the user decides. Growing a second job into this skill is how it stops doing this one.

## Hardcode-then-revert

`image_picker` takes no `default`, so an assigned-by-hand image region renders empty and the
result screenshot would show a hole — the one thing the user is going to judge the Stand-in
by. The render puts the captured images in directly, then puts the settings back.

**Before hardcoding**, write `HARDCODE-ACTIVE.md` into the visual-check folder: every file
path about to be touched, the original template JSON verbatim, and every temp asset copied
into the theme's `assets/`. It is the snapshot the revert restores from.

**Inject once**, after the render is up and before the first capture, at the first tier that
reaches the region:

0. **A replica section's own Liquid**, where the region sits inside one — this run wrote that
   file and owns it, so the sentinels go straight in and come straight back out at revert.
1. **The section's own `liquid` setting** in the template JSON — renders in the right DOM
   position and stays inside the template-only build surface. The capability inventory flags
   which sections expose one.
2. **A temporary Custom Liquid section** in `order`, emitting a `{% style %}` block alone that
   background-images the real element in place — for host sections with no `liquid` setting,
   and only where the empty picker still renders a targetable element.
3. **No tier reaches it** — for a region in one of the Target theme's own sections, which this
   skill does not edit, with no `liquid` setting and no targetable element. It is not injected
   and not worked around: the plan names it, the result render shows the empty picker, and the
   final output says so with the tier that would be needed.

Injected regions sit between sentinels and temp assets carry the `vh-tmp-` prefix, which is
what makes both greppable:

```liquid
{%- comment -%} VERIFY-HARDCODE-START <name> {%- endcomment -%}
<img src="{{ 'vh-tmp-hero.png' | asset_url }}" width="…" height="…" alt="">
{%- comment -%} VERIFY-HARDCODE-END <name> {%- endcomment -%}
```

Correction-round fixes go outside the marked region — tier 2's temporary section is removed
wholesale at revert, so a settings fix parked inside it would go with it.

Tiers 1 and 2 copy temp assets into the theme's `assets/`, the one point where this skill
writes a theme file. They are transient by construction: the revert deletes them, and the
final output reports that no theme file remains rather than that none was created.

**Revert** on every exit — completion and abort alike: restore from the breadcrumb, delete
`assets/vh-tmp-*`, remove the temp Custom Liquid section from `order`, delete the breadcrumb.

**Prove it** in the final output: `grep -r VERIFY-HARDCODE` over the theme returns nothing, no
`vh-tmp-*` remains, and the template JSON matches the breadcrumb's original. A revert that
fails reports **REVERT FAILED** with the breadcrumb path.

A session that dies mid-render leaves the breadcrumb and the sentinels in place. Finding
either at the start of a run means reverting from it first.

## The replication record

`.agent/shopify-page-replicate/replication.md` in the Target theme repo, one appended entry
per replicated page. It records the Source page URL, the date, the section map, the fonts, the
override table, the asset sort, the apps, and the honest gap list — and it doubles as the
retirement checklist, so replacing the Stand-in later is mechanical. Its shape is
[`references/replication-record-template.md`](references/replication-record-template.md); read
that and reproduce the block it gives.

**A pointer in the template**, written as the first line of the target template JSON, so
somebody opening the file in git sees the page is deliberate:

```
/* Stand-in replicated from <source-page-url> on <YYYY-MM-DD> by shopify-page-replicate —
   see .agent/shopify-page-replicate/replication.md */
```

The theme editor rewrites JSON templates on save and may drop that comment. Nothing depends
on it: the record under `.agent/` stands alone, and the run neither verifies the comment
survives nor treats its loss as a failure.

## Phase 1 — Research (read-only on the Target theme)

**Stranded-hardcode check first** (main agent, before anything else): a `HARDCODE-ACTIVE.md`
in any `.agent/shopify-page-replicate/visual-check/*/`, or a `grep -r VERIFY-HARDCODE` hit in
the theme, is a hardcode a previous session left live. Revert it per §Hardcode-then-revert and
report it before the run continues — a stranded hardcode is the one theme edit this phase
makes, and leaving it live in a client's theme is the risk the mechanism exists to close.

Run 1a and every standing scanner of 1b in parallel, then match in main. Beyond that revert,
no theme file is created or modified; the only writes are the knowledge docs (§Knowledge docs).

- **1a. The Source page** → page-extractor: the page reached and captured at 1440 px and
  390 px per `references/source-page-capture.md`; the producer/write-surface header; the
  per-section exact-values table (the settings-configuration targets AND the style report's
  expected values); the clip boundary; the section structure with verbatim copy; the
  per-breakpoint layout differences; the CSS custom properties; the two-family typography
  rows; the asset inventory with its Files/theme-asset column; the distilled REQUIREMENTS
  LIST. Report: `design-spec.md`, the design spec. This is the run's only extraction — the
  build reads from it and never returns to the Source page for a value.
- **1b. Target theme knowledge** — the knowledge-doc check first (§Knowledge docs), then the
  scanners it leaves standing: the capability scanner into `.agent/THEME-CAPABILITIES.md`, the
  two reuse scanners into the shards the main agent merges into `.agent/COMPONENTS.md`, each
  doc gated on arrival. What each scanner reads, and every fact its rows carry, is its format
  spec's. Per-run and never in a doc: whether the target template exists and its whole current
  `order` (the removal list), the heading and body font globals with the weights each family
  ships, and the `.git/info/exclude` check — inline reads where the catalog stood its scanner
  down. Above a spec's sharding threshold each standing scanner splits further into the shards
  the spec defines, each carrying its file range, and the main agent merges. Current global
  values are read live from `config/settings_data.json` in main — the catalog carries the
  schema's declared defaults, which are a different fact.
- **1c. Match the page to the Target theme's capabilities** (main agent, from `design-spec.md`
  + `.agent/THEME-CAPABILITIES.md`): section by section, in render order — which existing
  Target section type (or stack of instances) reproduces it, which block types, which settings
  and values, per breakpoint. Fill each typography row's `target-global` family from the font
  globals, and mark APPROXIMATES with the nearest available weight where the Target family
  lacks the measured one. Every color, spacing, size, radius and border is a per-instance value
  from the Source page, and each one that departs from a Target theme global is a row of the
  override table. Anything with no existing capability is a GAP: record the closest achievable
  approximation and its visible cost, whether an existing per-instance custom CSS/Liquid
  setting (an existing setting, so within the constraint) could close it, and what a replica
  section would have to contain to render it exactly — so stop 1 has two costed options to
  choose between rather than a refusal.
- **1d. Tooling detection** (main agent, non-mutating checks only): Browser pane availability
  first, then fallbacks per §Browser tiers; the Agent tool and which tools reach subagents (fix
  the delegation map — the page extractor most likely runs in main). The Shopify CLI's reach
  into the Source theme, which is an upgrade and not a requirement. Render path: Shopify CLI +
  `shopify.theme.toml` → `shopify theme dev` (desktop app: defined in `.claude/launch.json` so
  the pane manages the server); otherwise a preview/live store URL. There is NO static-render
  fallback — existing sections depend on the full theme runtime (snippets, global settings,
  theme CSS/JS), which a local Liquid engine cannot reproduce. Record the tiers and any
  temporary installs required.
- **1e. Ask**: put anything still ambiguous — including OPEN QUESTIONS from the reports — to
  the user as concise questions before planning.

**Done when:** the design spec `design-spec.md` exists, carrying its producer/write-surface
header and all eight sections; both knowledge docs are current and past their gates — produced
this run, refreshed incrementally, or read as fresh or newer with that decision recorded;
every section of the Source page is matched to a capability or recorded as a gap; every OPEN
QUESTION is answered; and the tooling record names browser tier, capture source, Source theme
structure source, render path, delegation map, temp dir, and the exclude status.

## Phase 2 — Plan (stop 1, for approval)

Present the complete plan and stop. Create or modify nothing until the user approves. Approval
covers the design spec, the fidelity forecast, the override table, the removal list, the
accept-or-build choice on every UNACHIEVABLE element, and the temporary installs.

- **The design spec, quoted inline**: the per-section exact-values table reproduced in the
  plan itself, per breakpoint, plus the layout differences and the verbatim copy — quoted,
  never referenced by file path. The user approves the numbers themselves, because after this
  stop nothing re-reads the Source page and a misread page is not caught again. Every OPEN
  QUESTION is resolved above it.
- **Section-by-section routing**: for each Source page section in render order, the existing
  Target section type (one instance or a stack) and block types that reproduce it.
- **Settings map**: for every chosen section instance and block, every setting id → value, per
  breakpoint where responsive settings exist, with the Source page value it satisfies.
  Text/link settings carry the verbatim copy. Image settings stay unassigned — the user uploads
  the staged files via the theme editor and assigns them (§Asset capture); the render shows
  those regions through the hardcode, and a region no injection tier reaches is declared as an
  empty picker in the result render.
- **Removal list**: every section currently in the target template's `order` that this run will
  remove, by customizer label and type — or "the template does not exist and will be created".
  The whole `order` is replaced, so this list is how existing work is never lost to a silent
  overwrite.
- **Font table**: the heading and body families inherited from the Target theme's globals, the
  families measured on the Source page they replace, and every weight substitution with its
  nearest available weight.
- **Override table**: every setting whose value departs from a Target theme global, with the
  global it departs from. This is the unwind list, and it exists from day one.
- **Fidelity forecast**: every element sorted into EXACT (fully met by existing capabilities),
  APPROXIMATES (closest achievable, its visible cost and expected delta described), or
  UNACHIEVABLE without new code, with the nearest achievable alternative named so there is
  something to accept rather than only a refusal. A per-instance custom CSS/Liquid setting
  proposed as a gap-closer is its own flagged line item. The forecast is per element, because
  the style report reads every mismatch back against it: an EXACT element that misses is a
  broken forecast, an APPROXIMATES element that misses is the approximation quantified, a BUILT
  element that misses is a build defect, and the UNACHIEVABLE elements are the ones the report
  names rather than asserts.
- **Accept or build, per UNACHIEVABLE section** (§Replica sections): each one is presented as
  a two-option line — the closest approximation with its visible cost, ACCEPT (the default),
  against the replica section that would render it exactly, BUILD, named with the files it
  would add under the `replica-<template>-<name>` prefix and what it would contain. Say plainly
  that a replica section is thrown away when the real design lands. Every element the user
  chooses to build is reclassified BUILT and moves onto the style report's assertion list;
  everything left stays UNACHIEVABLE and is named there instead. Choosing at least one build
  opens stop 2 at the head of Phase 3; choosing none keeps the run at a single stop.
- **Asset plan** (§Asset capture): every inventory row, its pile, the section setting it will be
  assigned to, and the staged filename for anything downloaded; the sort's counts; any
  source-quality flags; `assets/UPLOAD.md` is written from this list.
- **App plan** (§Apps on the page): the app blocks being copied, confirmation that app embeds
  are untouched, and any Liquid-injected app named as routed to `shopify-inject-app-into-liquid`.
- **Template diff**: the exact JSON — the new `sections` map and the new `order`, replacing the
  target template's whole `order`; or the whole file where the template is being created. The
  pointer comment as its first line.
- **Hardcode plan** (§Hardcode-then-revert): per image region, the injection tier that reaches
  it and its temp `vh-tmp-` asset; a region no tier reaches is named as one the result render
  will show empty, with the tier it would need.
- **Git hygiene**: confirmation `.git/info/exclude` carries the `.agent/` line, or the append
  adding it.
- **Delegation map**: which roles ran/will run delegated vs main, and the report paths produced
  so far.
- **Render-and-report approach**: browser tier, render path, whether `.claude/launch.json` will
  be created/updated (a planned file if so), the capture width per breakpoint, the clip
  boundary's Target theme equivalent, the key elements the style report asserts grouped by
  section — the forecast's EXACT and APPROXIMATES elements, with the UNACHIEVABLE ones listed
  separately as excluded — and the exact temporary-install list with method (on-demand runner /
  project-local / venv) and removal confirmation.

**Done when:** the user has approved.

## Phase 3 — Build (main agent only)

Touch only planned files; no delegated edits. Two passes, and **Pass B runs first** — forced,
not chosen: a template cannot reference a section type whose file does not exist yet.

**Stop 2 — the replica sections** (only where stop 1 chose at least one; otherwise this stop
does not fire at all and Pass B is skipped with it). Present, and stop for approval:

- Each replica section's files, by path, under the `replica-<template>-<name>` prefix — the
  section file, its stylesheet, its snippets.
- Its schema: every setting id, type, label and default, with the design spec's values quoted
  inline, plus the block types any repeated item needs.
- Which of those settings are REQUIRED, so the section renders nothing when they are empty
  (§Replica sections) — proposed, then confirmed or corrected by the user, never assumed into
  approval.
- The markup and CSS outline per breakpoint, including the desktop/mobile differences the design
  spec records, and the wrapper-gap fix where theme CSS leaves one.
- The elements this moves off the UNACHIEVABLE list and onto the style report's assertion list
  as BUILT.

Approval here covers new code only; everything else was approved at stop 1.

**Pass B — write the replica sections** (only what stop 2 approved):

- Create each file under its `replica-<template>-<name>` prefix, configuring from the approved
  design spec alone — its exact values, its layout differences, its verbatim copy; both
  breakpoints exact. The Source page is not re-read.
- Theme-editor settings only: no metafield and no metaobject access, no theme blocks, schema
  shape verified via the Shopify dev MCP rather than guessed.
- Wire the render-nothing branch per §Replica sections — the required-settings check emitting no
  markup and no placeholder, with no `request.design_mode` fork to differ on; item level first,
  then the whole section when no item survives; the wrapper gap closed.
- Edit no existing theme file to accommodate them. A replica section that would need one is an
  OPEN QUESTION back to the user, not an edit.

**Pass A — write the target template JSON:**

- Write the target template JSON exactly as approved — the `sections` map with its settings
  maps and block configurations, the whole `order` replaced by the Source page's section order,
  and the pointer comment as the first line. Create the template where it does not exist.
  Configure from the approved design spec alone: its exact values, its layout differences, its
  verbatim copy. The Source page is not re-read; a value the spec does not carry goes back to
  the user. Show the diff again before writing.
- Copy the app blocks across per the app plan, and nothing else app-related.
- Stage the downloaded assets into
  `.agent/shopify-page-replicate/visual-check/<name>/assets/` per the approved asset plan; run
  the sort's counts and write `assets/UPLOAD.md`.
- Append the `.agent/` line to `.git/info/exclude` if planned.
- Append the run's entry to `.agent/shopify-page-replicate/replication.md` per
  §The replication record. Its gap list is completed after the style report.

**Done when:** every approved replica section exists under its `replica-<template>-<name>`
prefix — written before the template that references it — the target template JSON is in place
as approved, and nothing else changed: no new settings on the Target theme's own sections, no
edited section/block/snippet/CSS/JS file of theirs, the Source theme untouched. The asset sort's
counts reconcile with `assets/UPLOAD.md` written, and the replication record carries the run's
entry, listing every replica file.

## Phase 4 — Render and report

**Static, first:** the target template still parses as valid JSON; `shopify theme check` on
changed files if available; fix errors.

Then **seven steps, in this order** — render → data check → capture hygiene → `style-reporter` → correction round → style report → cleanup.
The spec-driven skills share this shape; the one step this skill varies is step 6, the style
report, which reconciles every mismatch against the approved fidelity forecast. There is no loop, no iteration cap and no pass/fail verdict: the
run passes through the seven once and ends by handing the user the evidence.

At the start, write `source-desktop.png` / `source-mobile.png` into the visual-check folder and
copy the approved design spec in beside them as `design-spec.md`.

**1. Render.** `shopify theme dev` when available (Browser pane manages it via
`.claude/launch.json` in the desktop app); otherwise the Target theme's preview URL in the
browser. There is no static fallback — existing sections require the full theme runtime.

**2. Data check** (main agent) — the shape's data check in its plain form. Each skill's render
pulls its own kind of data, so each fills this step with the check that data needs; the
builder's metafield/metaobject stop-and-hand-over is that skill's, and this is this skill's.
Existing sections render the store's REAL data, so a configured instance can come up empty or
wrong-shape for reasons the settings map cannot see: a product/collection/blog reference that
resolves to nothing, a section whose content comes from a resource the template's context
doesn't supply. Same store means references resolve by handle without translation, so a miss
here is a real absence rather than a mapping error. Confirm each configured instance renders
the content the approved settings map points at; where it doesn't, hand the user exactly what
is missing and resume once it exists — nothing is captured against a render that isn't showing
the page.

**3. Capture hygiene** (before every capture): 1440 px and 390 px, the same two widths the
Source page was captured at; clip to the Target theme's equivalent of the design spec's clip
boundary — the template's own sections, never the header or footer; full scroll then back to
top so lazy content is present; animations/transitions disabled; wait for
`document.fonts.ready` + network idle. Same widths and same clip as the Source page, so the
style report compares like with like. No scale-matching and no pixel-dimension requirement —
nothing compares the capture to the reference mechanically. Capture source: the Browser pane,
else connected browser MCP or installed Chrome, else `npx playwright screenshot` (with `npx
playwright install chromium` if no system browser — the download goes on the cleanup ledger).
**Hardcode last** (main agent, before the first capture): breadcrumb, then inject at the
planned tier per §Hardcode-then-revert, so the result screenshot shows the page rather than an
empty `image_picker`.

**4. `style-reporter`, once per breakpoint.** One call each for desktop and mobile: it captures,
asserts the key elements' computed styles against the design spec's values — typography against
each row's `target-global` family, never its measured one — reconciles each mismatch against the
fidelity forecast, writes `result-{breakpoint}.png` into the visual-check folder, and returns a
text mismatch table grouped by section. It never edits theme files and returns no images.
Without delegation the same work runs in the main conversation, once per breakpoint.

**5. Correction round** (main agent, once), and the surface splits by pass. A **Pass A section**
is corrected by ADJUSTING SETTINGS VALUES in the template JSON per the capability map — never by
editing section code, which belongs to the Target theme and is read-only. A **replica section**
is corrected by EDITING ITS OWN CODE, which this run wrote and owns — its Liquid, its schema
defaults, its stylesheet. Each surface keeps the constraint it already had. If neither can move
the value, it is an undeclared gap: surface it, don't hack it. Then re-render and re-run
`style-reporter` once per affected breakpoint. One pass, one re-check, then stop; whatever
remains goes into the report as-is.

**Revert** closes this step, the last capture now taken: restore from the breadcrumb and prove
it per §Hardcode-then-revert. **Render-nothing check** after, for replica sections only, on the
real settings path: blank each replica section's required settings, confirm it emits no markup at
the dev-server or preview URL AND shows no placeholder in the theme editor — item level first,
then the whole section — then restore the content. The Target theme's own sections are not this
run's code and are not touched by this check.

**6. Style report — this skill's permitted variation.** Emit the surviving mismatches per
breakpoint, GROUPED BY SECTION in render order — a page-scale report reads in the order it
would be repaired — each one read back against the approved forecast for its element:

- **Forecast EXACT, mismatched → BROKEN FORECAST.** The plan promised existing settings would
  hit the value and they did not. It is a forecasting failure, reported as such and distinct
  from a build defect, tagged either settings-fixable per the capability map (naming the
  setting) or an undeclared gap.
- **Forecast APPROXIMATES, mismatched → the approximation, quantified.** Not a failure: the row
  carries the measured delta — expected, actual, the numeric difference — and whether it sits
  inside the delta the forecast described.
- **Forecast BUILT, mismatched → a build defect.** A replica section was written specifically
  to render this element exactly, so the code is this run's own: step 5 edits it, and anything
  surviving is reported as a defect in a file the report names, not as a limit of the theme.
- **Forecast UNACHIEVABLE → excluded from the assertion list and named.** These are never
  asserted, so they never appear as mismatches; the report lists them by name as out of reach
  without new code.

One row per mismatch — element, property, expected, actual, forecast class, reconciliation —
and "no mismatches" where a section has none. **No cap and no truncation**, however long the
page: a report that silently drops rows reads as complete when it is not. Typography is
compared against the Target theme's family, so the deliberate font substitution never appears
as a mismatch and never buries a real one. It is output, not judgment: it never blocks
completion and carries no threshold, ratio, iteration count, plateau state or verdict. Nothing
is excluded except the UNACHIEVABLE elements the forecast already named. It sits beside
`result-desktop.png` / `result-mobile.png` and `source-desktop.png` / `source-mobile.png`,
which the user compares by eye. Note the report scope: computed styles were checked at the two
captured widths, on the key elements the plan named.

If no render or capture path exists even with temporary installs: revert any live hardcode,
then stop and report exactly what's missing.

**7. Cleanup.** The ledger lists every temporary install (name, method, location). First
complete the replication record's gap list from the emitted report — every UNACHIEVABLE element
and every surviving approximation with its delta — then refresh both shared knowledge docs
against the current branch using their format ladders: reconcile the changed template scan and
`git:` line, append one row per replica section to each doc — **Stand-in**, **do not reuse**,
and the path to `.agent/shopify-page-replicate/replication.md` (§Knowledge docs) — append the
run to `updates:`, and rerun both completeness gates before the final report; a higher-format
doc is read-as-newer and left byte-for-byte unchanged. Then uninstall project-local packages,
delete venvs, `npx playwright uninstall` downloaded browsers, and delete the temp working
directory (including subagent reports). The Browser pane is a built-in — nothing to uninstall;
`.claude/launch.json`, if created per the plan, is project config and stays. RETAIN `.agent/`
in full — the knowledge docs for the next run, the replication record, plus
`.agent/shopify-page-replicate/visual-check/<name>/` (the design spec, the Source page
captures, the result renders, the staged assets) — untracked via `.git/info/exclude`. The user
reviews the renders before committing, uploads the files `assets/UPLOAD.md` lists through the
theme editor and assigns them to the image settings, and manages the folder themselves. Nothing
lands in git except the planned template edit.

**Final output (no explanatory prose):** files changed (expected: the target template JSON,
every approved `replica-<template>-<name>` file by path; possibly the `.git/info/exclude` append,
`.claude/launch.json`) with confirmation that NO theme file REMAINS beyond those, that no schema
of the Target theme's own sections was edited, and that the Source theme was not written to; the
render-nothing check's result per replica section — no markup on the storefront, no placeholder
in the editor — with the required settings it was run against, or "no replica sections were
built"; the
sections removed from the target template, by label and type, or that the template was created;
the revert proof (`grep -r VERIFY-HARDCODE` clean, no `vh-tmp-*` remaining, template JSON
matching the breadcrumb original) or **REVERT FAILED** with the breadcrumb path; the style report
per breakpoint, grouped by section and uncapped — element, expected, actual, forecast class and
reconciliation per surviving mismatch, or "no mismatches" — with the broken forecasts called
out, the approximations' deltas given, and the UNACHIEVABLE elements named as excluded; the font
table with every weight substitution; the accept-or-build outcome per UNACHIEVABLE element; the
override table's row count; the asset sort's counts
with any miss named and any source-quality flags; the app blocks copied and any app routed to
`shopify-inject-app-into-liquid`; any image region no hardcode tier reached, named as showing
empty in the result render; the delegation map and whether the Shopify CLI pull of the Source
theme succeeded; the tooling ledger with removal confirmation (or "nothing installed");
knowledge-doc status, one line each for `.agent/THEME-CAPABILITIES.md` and
`.agent/COMPONENTS.md` — created / refreshed incrementally / read as fresh / read as newer and
left unchanged, with the gate's reconciled counts or its declared shortfall; the path
`.agent/shopify-page-replicate/replication.md` and the path
`.agent/shopify-page-replicate/visual-check/<name>/` with a one-line inventory (the design spec,
the Source page captures, the result renders, staged assets, `UPLOAD.md`) and exclusion
confirmation.

## Rules

- Read every file before editing; show a diff before overwriting anything existing.
- Ask instead of assuming. Never guess a URL, a handle, or a storefront password — a run that
  captures the wrong page is worse than a run that stops.
- Subagents research and measure; the main conversation decides, edits, and asks. A delegated
  worker never edits theme files; OPEN QUESTIONS come back through the main agent.
- The design spec is the authority: the build reads from it alone, no value is re-read from the
  Source page after Phase 1, and a value it does not carry goes back to the user.
- The Stand-in inherits the Target theme's heading and body font families and nothing else.
  Sizes, weights, line heights, letter spacings, colors, spacing, radii and borders are the
  Source page's, written as per-instance values, and every departure from a global is a row of
  the override table.
- A replica section is written only where the user chose BUILD over the closest approximation at
  stop 1, and accepting the approximation is the default — a page that is about to be replaced
  does not quietly acquire custom sections.
- Every file Pass B writes carries the `replica-<template>-<name>` prefix — sections, stylesheets
  and snippets alike — and Pass B runs before Pass A, so the template never references a section
  file that does not exist.
- A replica section uses theme-editor settings only: no metafield, no metaobject, no theme blocks.
- A replica section renders nothing when its required settings are empty, on the storefront and in
  the theme editor alike, with no placeholder in either — because a Stand-in is not meant to be
  edited by a merchant, and the wrapper gap is closed so nothing renders as a band.
- The correction round adjusts a Pass A section's settings values and edits a replica section's
  own code. Neither surface crosses into the other.
- The style report reports; it never blocks completion. One check against the design spec, one
  correction round, then it is emitted with whatever remains — grouped by section, uncapped, no
  threshold, no ratio, no iteration count, no verdict.
- Every mismatch is read back against the approved forecast: EXACT that missed is a BROKEN
  FORECAST, not a build defect; APPROXIMATES that missed is the approximation quantified, not a
  failure; UNACHIEVABLE is never asserted, only named. Nothing else is excluded from the report.
- Typography asserts against the Target theme's family, never the family measured on the Source
  page.
- The build surface is the target template JSON plus the approved `replica-<template>-<name>`
  files; `.git/info/exclude`, `.claude/launch.json`, and the `.agent/` tree are the only other
  writable paths, per the plan. The Target theme's own section, block, snippet, CSS and JS files
  stay read-only — no new settings on them, no schema edits to them, and nothing existing edited
  to make room for a replica section. The render's `vh-tmp-` assets are the one transient
  exception and the revert removes them.
- The whole `order` is replaced, so every section the run removes is listed in the plan before
  approval.
- Only the template's own sections are read, built, captured or compared. The header, the footer
  and every other section group are outside the run.
- An image already in Files keeps its reference; an image living in the Source theme's assets is
  downloaded and staged for upload; the sort is proven by count and any miss is named.
- App blocks are copied, app embeds are untouched, and an app injected into the Source theme's
  Liquid is routed to `shopify-inject-app-into-liquid` and never attempted here.
- A hardcode is breadcrumbed before it exists and reverted on every exit — completion and abort
  alike — with the grep proof in the final output.
- Knowledge docs first: read `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` before
  any theme scan and run each spec's `format:` ladder on it; a scanner that runs writes its doc
  back, past its completeness gate, before the task continues. An explicit user refresh always
  wins.
- This skill produces both shared docs, so a theme missing one is scanned rather than worked
  around, and a doc at a higher `format:` is read as it stands and named in the output.
- Never change a global setting VALUE. A Stand-in is temporary; restyling the whole storefront
  for one is not a trade this skill makes.
- A per-instance custom CSS/Liquid setting is used only when the theme already has it AND the
  plan flagged it.
- Verify template/schema JSON structure via the Shopify dev MCP instead of guessing.
- The Browser pane leads when available; fallbacks apply only when it's absent.
- Only `result-desktop.png` and `result-mobile.png` are generated at the visual-check root,
  alongside the design spec and the two Source page captures; no other render variant.
- `.agent/` lives at the repo root, is always excluded via `.git/info/exclude`, and is never
  committed.
- The replication record lists every replica file the run wrote, and both knowledge docs carry a
  row per replica section marked **Stand-in** and **do not reuse**.
- The replication record is the retirement checklist. Every run appends to it; no run rewrites
  another run's entry.
- CLI tools: check installed first (on PATH, project dep, or npm script) — installed → invoke
  directly (`shopify theme dev`, `npm run …`), no runner. Not installed → on-demand runner
  (`npx` / `pnpm dlx` / `bunx` / `pipx run`), never a global install. Runner impossible
  (persistent binary/venv needed) → project-local or venv, on the ledger.
- Leave the machine as it was found — the retained `.agent/` tree (knowledge docs, the
  replication record, visual-check) is the one deliberate leftover, kept for the next run,
  review, and asset uploads.

## Usage

```
Use the shopify-page-replicate skill.
- Source page: https://client-store.com/pages/about?preview_theme_id=123456789
- Target template: templates/page.about.json
```

No placement line — the page is the template. No data-source line — content comes from the
existing sections' own settings, matching the Source page.
