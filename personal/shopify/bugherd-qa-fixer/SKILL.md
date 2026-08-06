---
name: bugherd-qa-fixer
description: Fix reported defects on a Shopify theme from BugHerd QA tasks — fetch each task, reproduce it at the reported page and viewport, make the smallest change that clears it, then re-verify the same page at the same viewport. Use when the user wants to work through, triage, or clear BugHerd tasks, client QA feedback, pinned client comments, bug reports, or a client screenshot of something broken. This skill fixes defects in what already exists and ROUTES anything larger instead of building it — a NEW section or block from Figma is figma-shopify-builder, recreating a design from EXISTING sections and settings is figma-shopify-composer, restyling a third-party app widget is shopify-app-restyle. No reproduction, no fix; fixed is measured, never eyeballed.
---

# BugHerd QA Fixer

Work a batch of BugHerd tasks on a client theme: fetch each task, reproduce the defect on the page and at the viewport it was reported at, fix it with the smallest change that clears it, and re-verify. Five phases — triage & reproduce (read-only on the theme), plan (stop for approval), fix, verify (measured gate), report & cleanup. The task data is the brief: the skill never asks the user to describe an issue, only to resolve what the task data cannot answer. The deliberate leftovers are `.agent/bugherd-qa-fixer/` and any dated line this run appended to the shared knowledge docs.

Mechanics this skill relies on — the BugHerd surface, the subagent prompts, the entry templates, and a Shopify complaint→cause triage table — live in [REFERENCE.md](REFERENCE.md). Two human-facing guides ship alongside: [references/writing-a-task.md](references/writing-a-task.md) (author a fixable task) and [references/filing-tasks.md](references/filing-tasks.md) (remediate a board of unfixable ones).

## Inputs

Collect before starting; ask for any that are missing.

1. **Task source** — BugHerd task numbers (the per-project `#n`), or a project plus a filter (status column, search text, "everything open"). Never an issue description.
2. **Theme repo root** — default: the current working directory when it is a theme repo.
3. **Render + deploy** — `shopify theme dev` from `shopify.theme.toml` is the default render target, and **`git push` to the theme's connected branch is the only deploy path** (§Verification render tiers). Confirm the branch and which theme role it drives.
4. **Figma file link** — asked once at intake, because "doesn't match the design" is usually the largest class in a batch. Per-frame node-ids are requested later, only for tasks that need them (§Figma reference policy).
5. **Write-back permission** — may the skill post comments, change status, or reassign, and in whose voice. Default when unspecified: NO write-back — the skill drafts the text, the user posts it. Optional override: *internal thread* — both reporter and responders are inside the agency, so technical detail is permitted (§Channels).
6. **Plan granularity** — one plan per page group (default), the whole batch, or per task.

**One theme repo, one BugHerd project, per run.** The repo is per-client, and every fix rung, knowledge doc, and render target is scoped to it. A cross-project listing is grouped by project: confirm which group maps to input 2, work that group, report the rest as out of scope — never triaged, so never remaining entries.

## What the task data actually gives you

Load-bearing, and different from what the field names suggest. Full surface in REFERENCE.md.

- **The complaint is `description`.** `title` is routinely `null`; a one-line title is authored, not read.
- **Viewport is `browser_info.window_size`** (the browser window) — never `resolution`, which is the screen and is commonly *smaller*. **No DPR field exists anywhere in BugHerd data.** Capture at DPR 1 unless the user supplies otherwise.
- **Guard on emptiness, not key presence.** A meaningful share of real tasks carry `url: null` with `browser_info: {}`, `css_selector_info: {}`, `screenshot: {}` — while still reporting `type: "pinned comment"`. `type` is not a signal.
- **`css_selector_info.path` is a hint, not a locator.** Hundreds of characters long, its `html` truncated, its pin able to land outside the element it recorded, and it embeds theme-instance section ids (`template--<digits>__<name>`) that do not exist on another theme. Normalize to theme-stable classes before use — and parse the section handle out of `shopify-section-…__<handle>`, which names the section file directly.
- **Severity is usually unset**, so it orders nothing by default (§Phase 1 ordering).
- **Board columns are per-project free text** in arbitrary casing; canonical names are rare and the last column is not necessarily Done. Resolve the board before any status write.
- **Every comment this skill can post is client-visible** (§Channels).

## Fixed is a measured result

Never an assumption, and measured differently per class. Two halves, kept distinct: **confirmation** — the reported failure is gone; **regression** — nothing unchanged got broken.

**Precondition, every task — the defect was REPRODUCED:** observable on the reported page at the reported viewport width, matched against the client's screenshot, with `before-<breakpoint>.png` saved as proof. No repro, no fix. Not reproducible after §Cannot reproduce is a remaining entry, never a speculative change.

**Behavioral / visual-defect tasks (no Figma reference)** — PASS when all three hold:

1. **Confirmation:** the specific complaint is no longer observable in a fresh capture of the same page at the same viewport.
2. **Confirmation:** a targeted assertion tied to the complaint passes — `getComputedStyle` on the element and its relevant ancestors, or the DOM/state condition the client described.
3. **Regression:** the surface named for the fix's rung is unchanged apart from the intended change, plus the counterpart breakpoint — confirmed by before/after image diff, not by eye.

**Design-fidelity tasks (Figma reference supplied)** — the sibling skills' gate in full: every checked computed style matches its Figma value; image diff ratio ≤ 1% against the Figma screenshot with anti-aliasing ignored on unmasked regions; residual diff pixels confirmed FROM THE DIFF IMAGE to be text-rasterization noise — Figma and Chromium rasterize fonts differently, so a literal 0% is unreachable. Layout, color, or spacing differences are never "noise".

**Reports come from live; fixes render on the verification theme.** So the invariant is the **same page path at the same viewport**, not the same URL. Side-by-side eyeballing is for diagnosis only, and a capture at a viewport other than the reported one never counts as verification.

## Regression scope by rung

The fix's blast radius sets the regression surface, declared in the plan and measured in Phase 4. `.agent/COMPONENTS.md` answers "where else is this used".

| rung | regression surface |
|---|---|
| 1 — template JSON setting | that section on that template, both breakpoints, plus any `*.context.*.json` override of it |
| 2 — scoped CSS | the component on **every template it appears on** — the custom-CSS surface is theme-wide even when the selector is not |
| 3 — component internals | every template that renders that section or snippet |
| 4 — global | a named template sample — home, collection, product, cart — plus every template this batch already holds `before` images for, both breakpoints |

## The fix-scope ladder

Take the lowest rung that resolves the reported defect, and stop there.

1. **A settings value** in `templates/*.json` or a section-group JSON, when `.agent/THEME-CAPABILITIES.md` or the scan shows a setting already controls the property. First rule out two silent failures: a shadowing `<template>.context.<market>.json`, and the section missing from the template's `order` array (present, editable, never rendered).
2. **A scoped CSS change** in the theme's existing custom-CSS surface, per the theme's own loading convention.
3. **An edit inside the component that owns the CAUSE** — its Liquid, CSS, or JS — limited to the reported defect. The pinned element is where the client saw the symptom, not necessarily where it is set.
4. **A global** — a global token, or `config/settings_data.json` → `current.settings`. Individually flagged, individually approved plan line, because globals restyle the whole storefront.

Never: refactors, drive-by improvements, dependency changes, new sections or blocks, new schema settings, app-served files, `config/settings_data.json` → `current.blocks` (app-embed state — a merchant action, handed to the user), or DOM hacks. Above rung 4 is out of scope — **route it and record it as a remaining entry**: `figma-shopify-builder` for new section/block code · `figma-shopify-composer` for a recompose from existing sections and settings · `shopify-app-restyle` for third-party widget overrides. Routing is proposed, never executed from inside this skill.

**A client's proposed fix is a symptom description, not a spec.** "Make the padding 20px" records what they want typed; the root cause is diagnosed independently before a rung is chosen.

## Cannot reproduce — the protocol

Runs in the MAIN conversation, in order, stopping at the first explanation. Never fix, and never verify, against a page that is not in the reported state.

1. **Theme identity — which theme did the client actually see?** A URL records the page, never the theme: live and a draft preview produce byte-identical URLs. Signals in the task data: `?preview_theme_id=` in the captured `url`; a `*.shopifypreview.com` host; the created date against the expiries — a shareable visitor preview dies after ~2 days and a merchant preview after ~30, so a client re-opening an older link may have been dropped back onto live. Undeterminable → ask; never assume.
2. **Cache and staleness** — hard refresh; clean profile; and check whether the task PREDATES a fix by comparing its creation date against commits touching the owning component. Already-fixed is a legitimate outcome: verify it, then a remaining entry proposing the task be closed (or the write-back comment, when permitted).
3. **Exact viewport** — the reported `window_size` width precisely, not the nearest breakpoint. Many "it's broken" reports live in a 20px band.
4. **Environment** — reported browser/OS vs what is available. Chromium covers Chrome and Edge; a WebKit- or Firefox-only defect needs that engine via temporary Playwright (on the cleanup ledger). Not installable → remaining entry naming the engine required.
5. **State** — logged-in vs guest, cart contents, market/country and currency, geolocation, password-protected preview session.
6. **Data** — the exact product/variant/collection in the URL, inventory, publication and sales-channel status, and app-embed activation differences between the reported theme and the repo theme (app embeds are per-theme, so diff `current.blocks` against the live theme before accepting any "the widget is gone" task).
7. **Still unexplained** — stop and ask the user, listing what was ruled out. Never guess a fix from the screenshot alone.

## Channels — client vs internal

- **Every comment this skill posts is client-visible.** The MCP's `add_comment` takes only `{project_id, task_id, comment}`, and BugHerd's `is_private` defaults to false, so no internal-note path exists. Write every comment as if the client reads it: plain language, what changed in user terms, where to look.
- Never in a comment: file paths, CSS selectors, class names, commit hashes, tool or MCP names, subagent mentions, diff ratios, `.agent/` contents, or reasoning about why the client's report was unclear. Unless input 5 declared the thread internal.
- `guest_visible` is a write-only knob this skill never sets, and cannot be read back — it gates nothing.
- Internal detail lives in `.agent/bugherd-qa-fixer/` — that is the internal channel.
- The skill never asks the client anything. Questions go to the user, who decides what reaches the client. A task blocked on client input is a remaining entry with the question drafted in plain language.
- Comment text is shown to the user for approval before posting — every task, not conditionally.

## Verification render tiers

Per task, cheapest first. The plan names each task's tier.

1. **`shopify theme dev` at `127.0.0.1:9292`** — the default. Visual, layout, design-fidelity, content. Hot reload, so no push is needed to verify.
2. **The draft theme's real-domain preview, after `git push`** — market/currency/locale (localhost proxies geolocation, cookies and sessions), logged-in, cart, app-embed, and checkout, which localhost explicitly cannot preview.
3. **Live publish swap** — only where 1 and 2 structurally cannot render the fix: Section Rendering API paths (AJAX-refreshed sections resolve against the *published* theme and fail silently as `null` at HTTP 200 — cart drawer, facets, quick-add, bundled section rendering), or previewing broken by a CDN in front of the store. It changes what real customers see, so: explicit per-occurrence go-ahead, never covered by plan approval; **batched** into one swap for every task that needs it; record the original live theme's name and ID first; **captures only** inside the window — no edits, no iteration, no diagnosis; re-publish the original immediately, then confirm it is live again; abort by re-publishing at once if anything is unexpected; low-traffic window at the user's discretion; window start/end timestamps in the run record. Declined or unavailable → remaining entries blocked on "needs a live-published render".

Reproduction never needs tier 3 — the report came from live, so reproducing is read-only browsing.

**Browser tiers:** the Claude Code Desktop Browser pane leads when available (it drives screenshots, DOM and computed-style inspection, interaction, viewport emulation, and manages the dev server via `.claude/launch.json`). Fallbacks in order: connected browser MCP → installed Chrome → temporary Playwright via an on-demand runner. There is **no static-render fallback** — a BugHerd task points at a real store render. Capture-exactness check and capture hygiene: REFERENCE.md.

## Figma reference policy

- Ask for the **file link at intake** (input 4). From it, attempt frame resolution with `get_metadata` and match frame names against the section handles parsed out of the pinned selectors — that resolves most frames without asking.
- Ask for a **per-frame link with its node-id** only for the frames that could not be matched; the remote Figma MCP cannot resolve a bare file link to a frame.
- Whole-file token values: `get_variable_defs` works only on the desktop Figma MCP server, so with only the remote server connected, token values are read off the section frame or supplied by the user.
- No reference and no way to decide what "correct" looks like → remaining entry ("needs a design reference"), never a guess.

## Delegation

Bounded fetching, research, and measurement go to subagents — isolated workers with their own context windows returning only a final report. Delegation earns its keep in **task intake** (a batch of payloads plus screenshots would flood the main conversation) and in **per-iteration verification**. It multiplies tokens: skip it for a single small task.

Prefer the named custom agents when installed in `~/.claude/agents/` or `.claude/agents/` — `figma-extractor`, `theme-scanner`, and `visual-verifier` (the sibling skills' verifier, which is the file the **repro-verifier** role runs on) — their definitions add tool-enforced restrictions such as `disallowedTools: Write, Edit`. Otherwise run the built-in general-purpose subagent with the prompts in REFERENCE.md, where the no-theme-edits rule is instruction-enforced.

**Capability gate** (at tooling detection): confirm the Agent tool is available and that the BugHerd MCP, Figma MCP, and browser tools reach subagents. Any role whose tools don't reach a subagent runs in the main conversation.

**Handoff protocol:** every delegation prompt carries its exact inputs (project id, task ids, page paths, viewport widths, normalized selectors, node-ids, file paths, evidence directory, capture specs); every worker writes FULL findings to a report file in the temp working directory and returns a short summary; ambiguities come back as OPEN QUESTIONS for the main agent to put to the user. A worker never writes into `remaining/` or `notes/`. The temp directory is created per run and deleted at cleanup.

**Never delegated:** interpreting what the client meant; every question to the user; classification, grouping, and routing; the root-cause diagnosis; the plan and every approval; all implementation edits, commits, and pushes; the diagnosis half of the verification loop; any BugHerd write-back; the publish swap; and the authoring of the remaining and notes docs.

| Role | Phase | Report |
|---|---|---|
| bugherd-triage (from ~4 tasks up; 1–2 fetch in main) | 1a | `bugherd-tasks.md` |
| theme-scanner (read-only — no Write/Edit; one call for the batch) | 1e | `theme-scan.md` |
| figma-extractor (design-fidelity subset only) | 1e, parallel | `figma-spec.md` |
| repro-verifier (never edits theme or config files) | 1f and 4, one call per task per iteration | `verify-report-<task-id>-<n>.md` |

## `.agent/bugherd-qa-fixer/` — the run record

`.agent/` at the theme repo root holds every durable artifact this skill suite produces: shared knowledge docs at its root, per-skill outputs under `.agent/<skill-name>/`. This skill writes `remaining/NEEDS-HUMAN-<YYYY-MM-DD>.md` (assigned work not finished), `notes/FOUND-ISSUES-<YYYY-MM-DD>.md` (unassigned problems found on the way), and `evidence/<task-id>/` holding `client-report.png`, `before-<breakpoint>.png`, `after-<breakpoint>.png`, and `diff-<breakpoint>.png` where a Figma reference exists. Entry templates: REFERENCE.md.

**The two docs never blur.** `remaining` = work that WAS assigned via a BugHerd task and could not be completed; every entry carries its task id. `notes` = problems NOT assigned to anyone, found incidentally; no task id, nothing in it was fixed. The one crossover: an unassigned problem that BLOCKED an assigned fix was fixed as part of that task — its notes entry records that with a cross-reference, so the diff is explainable.

Both are written every run, dated, `-2` for a same-day rerun, "None this run." when empty. A prior run's file is never deleted or overwritten. At intake, read the prior `remaining/` files: entries this run resolves are marked resolved in their own file; entries still open are carried forward BY REFERENCE (task id · one-line title · source file), so the newest file alone answers "what is still open".

**Git hygiene:** `.agent/` stays out of git via a `.git/info/exclude` line, asserted at 1a before the first evidence write — client screenshots must never reach a commit, and on a git-connected theme every commit is a deploy.

**The knowledge docs are an append-only cache, read at triage, never regenerated here:** `.agent/THEME-CAPABILITIES.md` answers "is there already a setting for this?", so a complaint gets fixed on rung 1 instead of rung 3; `.agent/COMPONENTS.md` maps a selector to its owning component and answers "where else is this used" for rung 2 and 3 regression scope. Verify any entry against the real file before relying on it; flag stale entries in notes. For an existing doc, append durable facts only to its header's `updates:` list, with the date, skill, and affected section or category. This skill deliberately does not create either knowledge doc: an absent doc is declared degradation, reported with `format: unknown`, and left for a producer scan to supply.

## Phase 1 — Triage & reproduce

Read-only on the theme; the only writes are `.agent/bugherd-qa-fixer/evidence/` and, before them, the exclusion line.

- **1a. Intake.** FIRST, before anything writes into the repo: confirm `.git/info/exclude` carries a `.agent/` line and append it if not. Then → bugherd-triage: resolve `project_id`, fetch every task, save client screenshots into the evidence directories, build the normalized table, and record the board's `statuses[]` sorted by `position`. Read the prior `remaining/` files in the same pass.
- **1b. Tooling detection** (main agent, non-mutating): Browser pane availability then fallbacks, plus the capture-exactness check; the BugHerd MCP's connected surface including which writes exist; the Agent tool and which tools reach subagents (fix the delegation map); **deploy path — the connected branch, which theme role it drives (never the live one), and one freshness check against it**; `shopify theme dev` availability from `shopify.theme.toml`; whether publishing is available, for tier 3; diff tool — installed `pixelmatch`/`odiff` invoked directly, else via an on-demand runner. Record every temporary install required.
- **1c. Classify and split** (main agent). One class per defect: content/copy · style-or-layout · design-fidelity vs Figma · behavior/JS · third-party app widget · data/admin/content-entry · unclear. **A task carrying more than one complaint splits into sub-defects `<id>a/b/c`**, each with its own verdict, rung, and measurement; the task passes only when all of its defects pass. Record per task whether `url`, `window_size`, `css_selector_info` and `screenshot` are present — guarding on emptiness.
- **1d. Blocking asks only** (main agent, one message): tasks missing `url` or `window_size` are **incomplete-as-filed** and cannot be reproduced — ask for page, viewport width, and state. Plus the Figma file link if not already given. Unanswerable → remaining entry, blocked on "incomplete report — no reported URL or viewport".
- **1e. Locate the source and group** → theme-scanner, one call for the batch: normalized selector and parsed section handle → owning template/section/block/snippet/stylesheet; **the winning declaration** that actually sets the complained-about property, and any ancestor whose layout constrains it; whether an existing setting or global token already controls it; theme-owned vs app-injected; the custom-CSS loading convention; each knowledge doc's observed `format:` and currency. Figma extraction runs in parallel. Then group: **component grouping decides what shares a fix; page grouping decides what shares a repro session.**
- **1f. Reproduce every reproducible task** → repro-verifier in REPRODUCE mode: exact page path, exact `window_size` width, the reported engine where the defect is engine-specific, the reported state reproduced by interacting; compare against the client screenshot; save `before-<breakpoint>.png`. Not reproducible → §Cannot reproduce → still unexplained, the task leaves the batch as a remaining entry.
- **1g. Ask the residue**, batched **per page group** — one message per group, so the user answers with that page's design open. Every ambiguous complaint reproduction did not resolve, every unmatched Figma frame, every worker OPEN QUESTION. **One round per group**; still ambiguous after it → remaining entry, not a second round.

**Ordering.** Severity where it is actually set → board column position → created date, oldest first. On a **thin-signal board** — severity unset on ≥80% of the batch, and no tags, and no assignees — tiebreak on task number ascending instead of created date (dates collapse into filing sessions), and let page group drive the order.

**Done when:** every defect is classified and has a repro verdict with its `before` image or a drafted remaining entry; every question has been asked and answered; the owning source and winning declaration are known for every reproduced defect; prior still-open entries are listed for carry-forward; and the tooling record names browser tier, capture source, render tiers, deploy branch and freshness, BugHerd write surface, diff tool, delegation map, temp dir, and exclude status.

## Phase 2 — Plan (stop for approval)

Present the plan and stop. Create or modify no theme or config file until the user approves. One plan per page group by default, per input 6.

- **Per defect**: id · **root-cause line** — which declaration, rule, or value produces the symptom, in which file at which line, and why it surfaces at the pinned element · the ladder rung and why nothing lower suffices · the exact file(s) and the edit (diff for existing files) · verification render tier · which gate applies and the rung's regression surface · the reference values the assertions will use · masks where a Figma diff applies · and, when write-back is permitted, the exact plain-language comment text and the target column resolved from the board.
- **Grouping and order**, naming where one fix clears several tasks.
- **The routing list**: defects that belong to a sibling skill, named per defect.
- **The draft remaining and notes lists as they stand right now** — so the user sees what is about to be handed back before any code is touched.
- **Globals** as individually flagged, individually approved lines.
- **Deploy**: the connected branch, per-task commit cadence, and the pushes this plan authorises.
- **Verification**: capture width per defect; the key elements for the computed-style assertions; diff tool and threshold; iteration cap (default 8 per breakpoint, plateau exit after 2 iterations without improvement); and the temporary-install list with method and removal confirmation.

Approving the plan also approves the listed temporary installs, the masks, the global changes it explicitly lists, the comment texts it quotes, and **the pushes it describes**. It never approves a live publish swap.

**Done when:** the user has approved — globals and comment texts confirmed, never assumed into approval.

## Phase 3 — Fix (main agent only)

One defect at a time, in the approved order. No delegated edits.

- Read every file before editing. Stay on the approved rung and inside the approved file list. Log every file touched against its defect id.
- **Commit per task, task id in the message, then push** — the commit is the revert unit and, on a git-connected theme, the deploy. A push rejected by the remote, or a push touching a file the plan did not list, stops and reports.
- A fix that turns out to need a higher rung than approved: STOP that defect, report, and either get the new rung approved or move it to remaining. Never silently escalate scope.

**Done when:** every approved edit is in place, every diff is in the transcript, and nothing outside the plan changed.

## Phase 4 — Verify

Per defect, measured, on that defect's render tier. Re-render, then re-capture the same page path at the same viewport, plus the counterpart breakpoint and the rung's regression surface.

**Landed check, before any assertion runs:** confirm the change is present in the served theme. **"Not landed" is its own outcome and does not count as an iteration** — otherwise the loop measures a stale render, fails a correct fix, and burns toward the cap.

**Capture hygiene:** the reported width at the reference scale with identical pixel dimensions (diff tools require same-size inputs); clipped to the element's region, not the full page; animations and transitions disabled; wait for `document.fonts.ready` + network idle; reproduce the reported state by interacting before capturing.

**Loop, per defect per breakpoint** — with delegation, steps 1–3 run as ONE repro-verifier call per iteration; the main agent reads the report, performs step 4, and launches the next round.

1. **Assertion layer first**: `getComputedStyle` on the element and its relevant ancestors, or the DOM/state condition, against the reference values. Fix mismatches on the approved rung — never by widening scope.
2. **Image layer**: design-fidelity → the diff against the Figma screenshot with approved masks; every other class → before/after over the rung's regression surface, confirming the reported defect is gone and nothing else in that surface changed. Record the numbers.
3. **Live tracking, every iteration, no exceptions**: overwrite `after-<breakpoint>.png` and the diff image, so the folder always shows the latest attempt.
4. **Diagnosis** (main agent): on failure, read the diff image and the mismatch report to localize the cause, map it to a fix on the approved rung, re-render, re-capture, repeat from step 1.

**Static checks:** any edited JSON still parses; `shopify theme check` on changed files if available — an authoring-error gate, not evidence a fix works. Fix errors before declaring a defect done.

**Exit, per defect:** PASS when §Fixed is a measured result holds for its class at the reported viewport with no regression on the rung's surface. CAP after 8 iterations per breakpoint, or 2 consecutive iterations without improvement — then stop, and the task becomes a remaining entry carrying the final measurements, the diff image path, the suspected cause, and whether it is a settings issue, a code issue, or out of scope. Never thrash, never lower a threshold silently, never grow a mask list silently. Note the report scope: fidelity is proven at the captured viewports, on the verification theme, only.

## Phase 5 — Report, write-back, cleanup

- **The two docs**: write `remaining/` and `notes/` per the REFERENCE.md templates — both files, every run, "None this run." when empty, prior still-open entries carried forward by reference. Mark any earlier entry this run resolved as resolved in its own file. Append dated lines to `.agent/THEME-CAPABILITIES.md` / `.agent/COMPONENTS.md` only where they already exist, append only.
- **Knowledge-doc append home:** the dated lines named above belong in the existing doc's header `updates:` list, never in another header field. Absent docs remain absent as declared degradation.
- **Write-back**, only per input 5: per task, a plain-language comment via `add_comment` plus the status change to the board's **Done-equivalent, resolved from `statuses[]`** — never archived or closed, because Done means "done, but not yet verified by the task owner" and closing is the reporter's. Comment text approved by the user first, and posted exactly as approved — no agent attribution appended. Where write-back is not permitted or the call does not exist, output the drafted comment and the intended change.
- **Cleanup**: uninstall project-local packages, delete venvs, remove any downloaded browser, and delete the temp working directory including subagent reports. RETAIN `.agent/bugherd-qa-fixer/` in full. Nothing from the run is committed except the approved theme and config edits.

**Final output (no explanatory prose):**

- Per-defect table: id · classification · reproduced yes/no · fixed or remaining · rung used · render tier · files touched · final measurement.
- The routed-to-sibling list; any tasks out of scope because they belong to another project.
- The two docs' paths with entry counts, including how many were carried forward still-open; what was appended to the knowledge docs, or "nothing".
- Knowledge-doc status per path: observed `format: <n>` and read status, plus dated entries appended under `updates:` or "nothing"; an absent doc is `format: unknown` and **declared degradation — not created**, with the producer scan it would need named.
- The delegation map — which roles ran delegated vs main, and their report paths.
- The tooling ledger with removal confirmation, or "nothing installed"; the commits pushed; any publish-swap window with its timestamps.
- BugHerd write-back confirmation per task, or the drafted comments to post.
- The `.agent/bugherd-qa-fixer/` path with its exclusion confirmation.
- **Once per run, where earned:** recommend stamping `BugHerdConfig.metadata` with `theme_id` / `theme_role` / `template` in the theme's BugHerd snippet — it turns "works for me" into a one-line check and removes the largest cannot-reproduce class permanently. If any task was incomplete-as-filed or needed clarification, name `references/writing-a-task.md`; if three or more were, also `references/filing-tasks.md`.

## Rules

- The task data is the brief: fetch it, reproduce it, then work — never ask the user to describe an issue first, and never ask a question reproduction could answer.
- No repro, no fix — the alternative is a remaining entry, never a speculative change.
- Verify the reported page at the reported viewport; a pass at another width, or on a page the client didn't report, is not a pass.
- Smallest change, lowest rung, nothing else in the diff. The pinned element is the symptom, not the diagnosis. Anything found but not assigned goes in notes.
- Never change a global silently; never write `config/settings_data.json` → `current.blocks`; app-served files stay untouched.
- `git push` to the connected branch is the only deploy; never `shopify theme push`, never the live-theme branch, and a live publish swap only under §Verification render tiers.
- Every BugHerd comment is client-visible and is approved before posting; internal detail lives only in `.agent/`.
- `.agent/` is excluded via `.git/info/exclude`, never committed, never pushed to the store; evidence after/diff images are overwritten every iteration, never only at the end.
- The measured gate is mandatory: eyeballing only diagnoses, the threshold never drops, the mask list never grows silently.
- Verify Liquid, schema, and template JSON structure via the Shopify dev MCP instead of guessing.
- CLI tools: installed → invoke directly, no runner. Not installed → on-demand runner (`pnpx` / `pnpm dlx` / `bunx` / `pipx run`), never a global install. Runner impossible → project-local or venv, on the ledger. Leave the machine as it was found — `.agent/bugherd-qa-fixer/` and any dated knowledge-doc append are the deliberate leftovers.

## Usage

```
Use the bugherd-qa-fixer skill.
- Tasks: #412, #415, #418
  (or: project "<project name>" — everything in "<status column>")
- Repo: .
- Render: shopify theme dev   ·   Deploy: git push to <branch>
- Figma: <file link>          (optional at intake)
- Write-back: comment + move to the Done column, as "the dev team"
  (or: no write-back — draft the comments for me)
- Mode: one plan per page group
```

No issue description — the task data carries the report. Per-frame Figma node-ids are asked for only where a design-fidelity task's frame can't be matched from the file link.
