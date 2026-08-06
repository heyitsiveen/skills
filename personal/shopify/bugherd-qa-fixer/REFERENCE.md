# bugherd-qa-fixer — reference

Mechanics for [SKILL.md](SKILL.md): the BugHerd surface, a Shopify complaint→cause triage table, capture specs, the subagent prompts, and the two entry templates.

## The BugHerd MCP surface

Confirm the tools are connected at tooling detection; work the surface as it actually is.

**Resolve the project first.** Every task call takes `project_id` AND `task_id`, and `task_id` is the **per-project number** shown in BugHerd (`#42`), not the global id. `list_projects` (partial name or site-URL match) resolves the project once. A URL like `/projects/1234/tasks/42` carries the **local** id; the global id appears only in `view_task_url`. Both come back as **strings**, not integers.

**Enumerate** with `list_project_tasks` — `status` (a column name **or an array of names**), `search` (case-insensitive on title *and* description), `assignee_email`, `limit` (default 50, max 200) / `offset`. `list_all_tasks` / `list_my_tasks` span projects. The MCP list surface **drops** REST's `priority`, `tag`, `external_id`, `updated_since` and `created_since` filters, so severity, tags, and date windows are client-side filters after fetching. There is no sort parameter anywhere.

**Fetch** with `get_task_details` — it is the only call returning `comments` and `task_logs`.

### Fields, and what they actually contain

| what you want | field | caveat |
|---|---|---|
| the client's complaint | `description` | `title` is routinely `null` — author one |
| page | `url` | full absolute URL incl. query; **`null` on non-pinned tasks**. Records the page, never the theme |
| **viewport** | `browser_info.window_size` | e.g. `"1920 x 999 px"` — the browser window. **Use this** |
| screen (not viewport) | `browser_info.resolution` | e.g. `"1440 x 900 px"` — commonly *smaller* than `window_size`, because they are measured in different pixel spaces |
| DPR | — | **does not exist.** Not in the REST spec, not in any response. Do not derive it from the pair above |
| element | `css_selector_info.path` | full `html>body>…` chain, hundreds of chars; `html` is a **truncated** outerHTML; `data.bugOffsetX/Y` are fractions of the element box that **can exceed 1.0**, i.e. the pin can sit outside the element it recorded |
| screenshot | `screenshot.url` | `…/screenshot.jpg?showpin&task_id=<GLOBAL_id>`; a `mobile-screenshot.jpg` variant exists |
| severity | `priority` on **reads**, `severity` on **writes** | five read values (`not set` · critical · important · normal · minor); the MCP write enum has four and omits `not set`. Usually unset in practice |
| board column | `status` → `{id, name}` | see below |
| history | `task_logs` | pre-rendered strings, e.g. `"<ISO8601> - <Name>: [\"created task\"]"` |
| console / network logs | — | **not captured.** `logs` is undocumented and never populated; `metadata` is a caller-supplied convention, not an automatic capture |

**Guard on emptiness, not key presence.** Tasks not created through the browser pin return `url: null` with `browser_info: {}`, `css_selector_info: {}`, `screenshot: {}` — and `metadata` inconsistently `{}` or `null` — while still reporting `type: "pinned comment"`. **`type` is not a pinned-ness signal.** Expect a meaningful share of any real board to be shaped this way.

**Normalizing a selector.** The path embeds theme-instance section ids — `div#shopify-section-template--18969060900963__as-seen-on`, `div.as-seen-on.as-seen-on--template--18969060900963__as-seen-on`. Those digits belong to the theme the client was on and do not exist on the verification theme, so the raw path matches nothing there. Strip `--template--<digits>__<handle>` and `--sections--<digits>__<handle>` modifiers down to the base class, and **parse the handle out of `shopify-section-…__<handle>`** — it names the section file (`sections/as-seen-on.liquid`) directly, which is a far better localization input than grepping the selector.

### Board columns

Per-project free text in arbitrary casing; canonical `backlog/todo/doing/done/closed` names are rare in practice, and **the last column is not necessarily Done**. Resolve before any status write:

- Project details expose `statuses[]` as `{name, position}` — **no id**. Task `status` is `{id, name}` — **no position**. Join on **name**, case-insensitively.
- `position` is a sparse signed integer (values from `-1073741824` to `2013265920` observed), not an ordinal. Sort by it; never assume small or non-negative.
- `status.id` values are 7-digit integers for custom columns.
- Setting `status` to `feedback` returns a task to the Feedback panel. Feedback is a real state carrying no `status_id`.
- BugHerd's own definitions: **Done** = *"the task is done, but is not yet verified by the task owner"*; **Archive** = *"archived and completed or closed for other reasons."* This skill moves tasks to the Done-equivalent and never archives or closes.

### Writes

`add_comment`, `update_task` (status, severity, title, description, url, due_at, `guest_visible`), `update_task_assignees`, `update_task_tags` (add/remove/set), `update_task_attachments` (add/remove/set, via a prepare→PUT→attach three-step for local files).

- **`add_comment` is `{project_id, task_id, comment}` — no visibility parameter**, and BugHerd's `is_private` defaults to false. Every comment posted through it is client-visible; there is no MCP path to an internal note. Falling back to REST with `is_private: true` is deliberately not done: the "Members only" control is Premium-gated so it silently doesn't exist on lower plans and the plan can't be detected, it adds a second auth surface, and it turns an absolute boundary into a constraint that fails *open* — leaking client-inappropriate detail into a client-visible thread.
- `is_private` *is* visible on comment **reads**, so an existing internal note can be recognised even though a new one cannot be created.
- **`guest_visible`** exists only as an `update_task` write parameter, appears in no read response, and is Premium-gated. Unreadable, so it gates nothing.
- **No agent attribution.** The MCP's own convention appends "(via <agent name>)" to comments; this skill strips it. A comment posts exactly as approved.
- `update_task` is a partial field-set write, so replaying it converges. `add_comment` and task creation are **not** idempotent — a retry duplicates.
- Task, comment and column **deletion is unsupported and unsafe** — BugHerd's spec contradicts itself on whether the endpoints exist.
- Rate limit: 60 requests/minute sustained, burst 10.

**Degrade gracefully:** the MCP absent, a write call missing, or permission withheld → output the drafted comment and the intended status change for the user to apply. Never a silent skip.

## Shopify complaint→cause triage

Check before choosing a rung. Every row's answer is "this is probably not a theme-code bug."

| client says | most likely cause |
|---|---|
| image is blurry | source asset intrinsic size — *"an image can never be resized to be larger than its original dimensions"*, whatever `image_url` requests. Content bug |
| crop is wrong | merchant focal point, auto-applied by `image_tag` as `object-position`, editable in admin |
| metafield renders blank | never storefront-access — *"metafields are always accessible in Liquid regardless of this setting"*. Check definition, value on that resource, owner type, dynamic-source context |
| section is empty | a `publishable` metaobject in **draft** status returns `nil` |
| works on the site, dead in the theme editor | missing `shopify:section:load` listener — *"any associated JavaScript that runs when the page loads won't run again"* after a section re-render |
| it flickers when I type in the editor | expected. Live preview covers only unfiltered `{% style %}` color settings and sole-child text settings; everything else forces a full section re-render |
| AJAX-refreshed section wrong or missing | Section Rendering API resolves against the **published** theme and returns `null` **at HTTP 200** — status-code-only handling reads failure as success |
| broken on one page only | stylesheet subsetting — a style present on one template can legitimately be absent on another |
| broken only in one market | `<template>.context.<market>.json` override; the base file gives no hint it exists. Market overrides also stop inheriting Default updates |
| app widget disappeared | per-theme app embed. Diff `current.blocks` against the live theme; grep `templates/*.json` for `shopify://apps/`. A manual Theme Store update installs as a **new unpublished theme with app embeds off** |
| checkout still in English | checkout and system translations live in Shopify's Language Editor, outside theme locale files |
| hardcoded `/cart` misbehaves in another market | use the `routes` object and `window.Shopify.routes.root` |
| section exists but never renders | present in `sections` but absent from the template's `order` array |
| setting changed, nothing happened | edited `presets` while `current` holds the live values in `settings_data.json` |

`shopify theme check` cannot see any of this — it parses Liquid and JSON on disk, so runtime, visual, data-dependent, market-specific and app-injected defects are precisely the residue that reaches BugHerd. Treat it as an authoring-error gate only.

## Capture specs

**Capture-exactness check** (tooling detection): the measured comparisons need captures at the reported viewport width and the reference scale, with identical pixel dimensions, clipped to the element's region. Confirm the Browser pane can honor that; if not, the pane still does reproduction, inspection, interaction and diagnosis while the MEASURED captures fall to the first fallback that can.

**Capture hygiene, before every capture:** reported `window_size` width exactly, not the nearest breakpoint; DPR 1 unless the user supplied one; identical pixel dimensions to the reference (diff tools require same-size inputs); clipped to the element's region, not the full page; animations and transitions disabled; wait for `document.fonts.ready` + network idle; reproduce the reported state by interacting *before* capturing.

## Subagent prompts

Used when the named custom agents (`figma-extractor`, `theme-scanner`, `visual-verifier`) are not installed. In that fallback the no-theme-edits rule is instruction-enforced, so each prompt states it.

### bugherd-triage

```
You are fetching a batch of BugHerd QA tasks for a Shopify theme. Work only
from the BugHerd MCP; do not read or modify the theme repo.

Project id: {project-id}
Task ids (per-project numbers): {ids}
Evidence root: .agent/bugherd-qa-fixer/evidence/

First, from project details, record the board: statuses[] as {name, position}
sorted by position ascending. Note which column is last and which one, if any,
is a Done-equivalent.

For every task call get_task_details, then:
1. Save the client's screenshot to
   .agent/bugherd-qa-fixer/evidence/{task-id}/client-report.png (create the
   directory). Note when a task carries none.
2. Normalize into one row per task: id · the VERBATIM complaint from
   `description` (quote exactly, never paraphrase; `title` is usually null) ·
   page URL · viewport width from browser_info.window_size (NOT resolution) ·
   browser/OS · severity from `priority` · status column · assignee ·
   requester · created date · tags · attachments.
3. COMPLETENESS, four booleans per task, guarding on EMPTINESS of the object
   and not on the key being present: url · browser_info.window_size ·
   css_selector_info · screenshot. Every task reports type "pinned comment"
   whether or not it carries pin data, so `type` proves nothing.
4. Normalize each selector: give both the raw css_selector_info.path AND a
   theme-stable form with `--template--<digits>__<handle>` and
   `--sections--<digits>__<handle>` modifiers stripped, plus the section
   handle parsed out of any `shopify-section-…__<handle>` id.
5. COMPOUND TASKS: if a description contains more than one distinct complaint,
   split it into sub-defects {id}a, {id}b, … and quote each separately.
6. Propose a classification per defect: content/copy · style-or-layout ·
   design-fidelity vs Figma · behavior/JS · third-party app widget ·
   data/admin/content-entry · unclear.
7. OPEN QUESTIONS — one per defect whose complaint is not unambiguous, phrased
   so the main agent can put it to the user verbatim. A complaint that could
   mean two different fixes is ambiguous; say so rather than picking one.

Write the FULL findings to {temp-dir}/bugherd-tasks.md as a table plus a
per-defect detail block, with the board record at the top. Return only the row
count, the completeness tally, the classification tally, and the open questions.
```

### theme-scanner

```
You are locating the theme source behind a batch of reported defects.
READ-ONLY: do not create or modify any theme file.

Theme repo: {repo-path}
Per defect: {defect-id → normalized selector + parsed section handle →
  page path → the property or behavior complained about}
Existing docs: .agent/THEME-CAPABILITIES.md and .agent/COMPONENTS.md
{— current contents attached | absent}

Treat both docs as a CACHE, never as truth: read them first, then verify each
entry you rely on against the real file, and report every entry that no longer
matches as STALE with what it says vs what the file says.

For every defect report:
1. Owning source: start from the parsed section handle (it names the section
   file directly) and confirm against the selector — which template, section,
   block, snippet and stylesheet the element belongs to, with file paths.
2. THE WINNING DECLARATION: which rule actually sets the complained-about
   property — file and line — after the cascade, plus any ancestor whose
   layout constrains it (flex/grid/overflow/width). The pinned element is
   where the symptom shows, not necessarily where the value is set. Say
   plainly when the cause is elsewhere.
3. Whether an EXISTING setting or global token already controls that property
   (setting id, type, where it lives, current value). Say plainly when none
   exists. For a template-JSON setting also report: whether a
   <template>.context.*.json override of that template exists, and whether
   the section appears in the template's `order` array.
4. Whether the selector is theme-owned or injected by a third-party app
   (app-served stylesheet, vendor prefix, JS-set inline styles).
5. WHERE ELSE the owning component is used — every template that renders it —
   because that is the regression surface for a component-level fix.
Batch-wide:
6. How the theme loads custom CSS — asset naming, include point.

Write the FULL findings to {temp-dir}/theme-scan.md, one section per defect
plus the batch-wide item and a STALE-ENTRIES list. Return only a 3–5 line
summary, the stale-entry count, and the open questions.
```

### figma-extractor

```
You are extracting a Figma design spec for design-fidelity BugHerd defects on
a Shopify theme. Work only from the Figma MCP; do not read or modify the theme
repo.

File link: {figma-file-link}
Frames to match: {defect-id → section handle → reported breakpoint}
Known node-ids: {defect-id → node-id, where supplied}

1. For defects without a node-id, call get_metadata on the file and match
   frame names against the section handles above. Report each match with the
   node-id you resolved and your confidence; list every handle you could NOT
   match — those become OPEN QUESTIONS asking the user for a frame link.
2. For each resolved node-id call get_design_context and get_screenshot, then
   compile an exact-values table: typography (family, size, weight,
   line-height, letter-spacing), colors, spacing (padding/margin/gap), sizes,
   borders, border-radii, frame width. These are the fix targets AND the
   expected values for computed-style assertions — record exactly.
3. Per-breakpoint layout differences where both frames exist.
4. Each screenshot's scale (1x/2x) and pixel dimensions — captures must match
   them exactly for the pixel diff. This is the only authority on scale;
   BugHerd carries no DPR.

Write the FULL findings to {temp-dir}/figma-spec.md, keyed by defect id, with
an OPEN QUESTIONS section at the end. Return only a 3–5 line summary, the
matched/unmatched frame counts, and the open questions.
```

### repro-verifier

```
You are measuring ONE defect at ONE breakpoint for a Shopify theme QA fix. You
NEVER edit theme or config files — set up, measure, record, report only.

Defect: {defect-id} — iteration {n}, mode {REPRODUCE | VERIFY}
Page: {exact reported page path + query | verification-theme URL for the same
  path}
Render tier: {theme dev localhost | draft preview | live-published}
Viewport: {w}px wide, DPR 1  (use this width exactly, not a breakpoint)
Engine: {chromium | webkit | firefox}
Element: {theme-stable selector}  (raw BugHerd path, for reference only:
  {raw-path} — it embeds theme-instance ids and will not match here)
Client's report: "{verbatim description}"
Client screenshot: .agent/bugherd-qa-fixer/evidence/{task-id}/client-report.png
Evidence dir: .agent/bugherd-qa-fixer/evidence/{task-id}/
Expected values: {the assertion list — element, property, expected value}
State to reproduce: {logged in / option selected / dropdown open / cart
  contents / market — or "default"}
Regression surface: {the rung's surface — templates and breakpoints to check}
Figma reference + masks: {path and approved mask list | none}
Diff tool: {pixelmatch … | odiff-bin …} (anti-aliasing ignored)

1. VERIFY mode only — LANDED CHECK FIRST: confirm the expected change is
   present in the served theme before measuring anything. If it is not, stop
   and report NOT LANDED. That is not a failed iteration; do not run
   assertions, do not overwrite images.
2. Capture hygiene, then capture: viewport at the exact width above; DPR 1;
   animations/transitions disabled; wait for document.fonts.ready + network
   idle; reproduce the reported state by interacting BEFORE capturing; clip to
   the element's region, not the full page. Capture dimensions must equal the
   reference's exactly.
3. REPRODUCE mode: save before-{breakpoint}.png and state plainly whether the
   defect is observable and whether it matches the client screenshot — yes /
   no / partial, with what differs. Do not diagnose a cause.
   VERIFY mode: save after-{breakpoint}.png.
4. Assertions: getComputedStyle on the element and its relevant ancestors, or
   the DOM/state condition described, vs the expected values. Record every
   mismatch: element, property, expected, actual.
5. Image layer — design-fidelity: diff vs the Figma reference with the
   approved masks applied; record the ratio, save diff-{breakpoint}.png.
   Otherwise: before/after comparison across the REGRESSION SURFACE above,
   reporting whether the reported defect is gone and whether anything else in
   that surface changed.
6. Overwrite after-{breakpoint}.png and diff-{breakpoint}.png in the evidence
   dir with THIS iteration's images.
7. TAG every mismatch exactly one of: "matches the reported defect" ·
   "settings-fixable" · "code-fixable in the owning component" · "not fixable
   without new code" · "out of scope — third-party app".

Write the FULL report to {temp-dir}/verify-report-{defect-id}-{n}.md: landed
status, repro or pass verdict, mismatch table with tags, diff ratio where
applicable, largest diff regions and where they sit, then OPEN QUESTIONS for
anything that blocked the measurement — the selector matched nothing or
matched several elements, the described state could not be reproduced, the
page needed a login or a password you were not given. Return only the landed
status, the verdict, mismatch count by tag, one line on the biggest offender,
and the open questions.
```

## Entry templates

### Remaining — assigned work not finished

```
### <task-id>[<defect letter>] — <authored one-line title>   <task permalink>
Client said: "<verbatim description>"
Reported at: <page path> · <window_size width>px · <browser>/<OS>
  Element: <theme-stable selector>
Reproduced: yes | no | partial → .agent/bugherd-qa-fixer/evidence/<task-id>/
Blocked by: <one of — incomplete report, no reported URL or viewport / not
  reproducible at the reported page and viewport / needs a design decision or
  a missing Figma reference / needs a live-published render / needs admin,
  app-settings, or credentialed access / needs content or data changes / needs
  new code beyond this skill's scope (<sibling skill>) / blocked by a
  third-party app / complaint ambiguous>
  <for an ambiguous complaint: the exact open question, in plain language>
Tried and ruled out: <what was attempted, what it proved>
Next step: <suggestion> — owner: <who>
BugHerd: commented <yes/no> · moved to <column | not moved>
```

For a compound task, list each defect's verdict so "fixed 2 of 3" is explicit.

### Notes — unassigned problems found on the way

```
### <what and where>
Where: <page path> · <viewport>px · <selector> → <evidence path, if captured>
Surfaced by: work on <defect-id>
Severity guess: <…> · shopper-visible: yes | no
Candidate BugHerd task: yes | no — NOT filed (filing is client-visible; the
  user decides)
Not fixed this run.   | Fixed as a blocker of <defect-id>.
```
