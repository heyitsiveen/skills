---
name: client-theme-onboarding
description: Generate AI-facing docs for a client Shopify theme repo — deep-scan the theme, then write the agent doc pack (AGENTS.md + CLAUDE.md symlink, ARCHITECTURE.md, COMPONENTS.md reuse inventory, THEME-CAPABILITIES.md capability catalog, COMMANDS.md, REVAMP-TODO.md, shopify.theme.toml) in imperative, grounded, token-lean form for Claude Code/LLM agents, not humans. Use when the user asks to onboard a client theme, write docs for the agent, create a CLAUDE.md / AGENTS.md / AI-readable reference for a theme repo, or regenerate one of the pack docs.
---

# Client Theme Onboarding — AI-facing docs

Every doc this skill writes is consumed by agents (Claude Code, LLM tools), not humans. Purpose: make every future agent session on this repo more accurate and cheaper to run. The user reads gates and reports; the docs are machine instructions.

Assume zero prior knowledge of the theme and nothing about its structure. Four gates, strictly in order: **interview → deep scan → plan approval → write**; each gate opens only with the user's input or approval.

Delegation boundary: Step 2 fans out to parallel Explore subagents, Step 5 lints with one fresh subagent. Steps 1, 3, 4 never delegate — subagents cannot ask the user anything, and generation needs every recorded fact in one context.

## Doc Contract — every generated doc passes all 8

1. **Imperative + unambiguous** — exact commands, paths, IDs, values. Banned: "run the appropriate command", "as needed", marketing/tutorial prose.
2. **Grounded** — every claim traces to the scan, ClickUp, or the transcript. No source → it becomes an open question, never content.
3. **Deterministic** — each instruction is executable or checkable without interpretation: a command, a path, a pass/fail condition.
4. **Token-efficient** — tables/lists over paragraphs; one fact lives in one file; other files point to it by filename instead of restating.
5. **Scannable** — fixed heading contract per doc (REFERENCE.md); an agent greps a heading and lands on the answer.
6. **Example-driven** — ✅ correct / ❌ wrong pairs for every rule with a common wrong path.
7. **Failure-explicit** — `error → cause → fix` tables for every failure the scan or the user surfaced.
8. **Progressive disclosure** — AGENTS.md is the lean entry; depth lives in ARCHITECTURE.md / COMPONENTS.md / THEME-CAPABILITIES.md / COMMANDS.md / REVAMP-TODO.md, loaded on demand.

The contract binds this skill's own files too.

## Step 1 — Interview

AskUserQuestion, five inputs (the tool caps at four questions per call — split 3+2). Record each answer or an explicit "none":

1. **Working branch** — `git checkout <branch>`; if missing, create it from the base branch.
2. **Prefix** — a short, unique namespace for everything built for this client (e.g. `acme`). Suggest a default derived from the client/project name; the user can override. Scope: every new theme artifact from this point forward — section/snippet filenames (`sections/{prefix}-x.liquid`), custom-element tags (`<{prefix}-x>` — conveniently supplies the hyphen custom elements require), CSS classes/custom properties (`.{prefix}-x__part`, `--{prefix}-gap`), schema block/setting IDs, JS module/function names. Recorded with before/after examples in AGENTS.md 🧩 (spec: REFERENCE.md §AGENTS.md).
3. **Store + environments** for `shopify.theme.toml` — store handle (`*.myshopify.com`); per-environment theme IDs only if the user wants them (offer `shopify theme list --store <handle>`). Recommend store-only — rationale + spec: REFERENCE.md §shopify.theme.toml.
4. **ClickUp project details** — pasted text or a file path. Optional.
5. **Meeting transcript** — pasted text or a file path. Optional.

Done when: branch checked out, answers 1–5 recorded.

## Step 2 — Deep scan (read-only; up to 4 Explore subagents in parallel)

No writes of any kind in this step. Launch all agents in ONE message so they run in parallel; collect every report before Step 3. A subagent sees nothing of this conversation and Explore skips CLAUDE.md — each prompt carries its full ask plus three standing demands: every fact cited as `path:line` · actual commands/paths/IDs, never paraphrases · final message = the complete report.

- **Agent A — survey + tripwire candidates:** directory tree; every config file; `package.json` scripts; build tooling; linting; CI workflows (which branch pushes deploy, and to where); committed secrets (`.npmrc`, `.env` — paths only, never values); sync exclusions (the build tool's ignore files); existing docs / `.agent/` knowledge docs (`THEME-CAPABILITIES.md`, `COMPONENTS.md`, `app-widget-*.md`) / `.shopifyignore` / `shopify.theme.toml` / CLAUDE.md / AGENTS.md; conventions — section/snippet naming, CSS approach, JS patterns, schema style, app footprint (Klaviyo, Judge.me, subscriptions…); dev loop — the exact sync command, watcher detection (`pgrep` pattern), every known failure mode (these become the `error → cause → fix` rows).
- **Agent B — reuse inventory, JS side** (B and C skip entirely when `.agent/COMPONENTS.md` exists and is fresh — figma-shopify-builder produces the identical doc): every `customElements.define` registration (→ Custom web components) · reusable scripts/utils not tied to one component (→ JavaScript) · event/fetch interaction sequences (→ Flows).
- **Agent C — reuse inventory, Liquid/CSS side** (same skip as B): parameterized utility snippets/filters (→ Functions) · repeated section/CSS structures (→ Patterns) · multi-step markup sequences, e.g. product form → cart (→ Flows).
- **Agent D — capability catalog** (knowledge-doc check first: skip D entirely when `.agent/THEME-CAPABILITIES.md` exists and is fresh — its file lists + `scanned:` counts vs disk, header git line vs current branch/short SHA; figma-shopify-composer produces the identical doc): global design tokens in `config/settings_schema.json` — ids, types, labels, options/ranges, defaults; schema only, `settings_data.json` current values are merchant-volatile and never recorded — and where globals become CSS variables · every section in `sections/`: display name, full settings list, block types with their settings, presets, responsive settings flagged, per-instance custom CSS/Liquid settings flagged · theme blocks in `blocks/`, same detail · inheritance trace per color/typography/radius/border setting (global-connected vs raw) · usage conventions from `templates/*.json`.
- B, C, and D prompts include the absolute path of this skill's REFERENCE.md; B and C carry the row schema `name | file path(s) | what it does | reuse keywords` (one row per item, per §COMPONENTS.md); D carries the eight section names (§THEME-CAPABILITIES.md).
- Small repo (quick `ls` first: fewer than ~40 files across sections/, snippets/, JS source): skip the fan-out, scan inline — identical coverage, same demands.

Merge in the main thread — subagent reports are leads, not sources:

- **Tripwires** — record each as `action → consequence → rule`, only after re-reading the cited `path:line` yourself; also glob the CI workflow dir directly. A tripwire missed or invented by a scan agent is the one failure this run cannot absorb; recording one unread is a Contract #2 violation.
  - CI workflows: which branch pushes deploy, and to where. A push that auto-deploys the live storefront is the repo's most important fact.
  - Committed secrets (`.npmrc`, `.env`): flag for rotation; the values never enter the docs.
  - Sync exclusions (the build tool's ignore files): paths that never auto-sync get a manual-move workflow in the docs.
- **Verdict: STANDARD or CUSTOM.** STANDARD = `assets/ config/ layout/ locales/ sections/ snippets/ templates/` (+ optional `blocks/`) at the repo root, no build pipeline in front. CUSTOM = source dirs, compile step, framework, generated output, nesting. State the verdict with evidence; the docs describe the ACTUAL structure.
- **Reuse inventory (REQUIRED — every onboarding ends with `.agent/COMPONENTS.md` present and fresh; never dropped under time or scope pressure):** an existing fresh doc is reused as-is; otherwise merge B + C rows into the COMPONENTS.md row schema (REFERENCE.md §COMPONENTS.md). Five categories, named exactly as REFERENCE.md's headings: Custom web components · JavaScript · Functions (= reusable Liquid utility snippets/filters) · Flows (add-to-cart, quick-view, facets) · Patterns (drawer, sticky header, sold-out state). Flows and Patterns arrive split across B and C — merge by feature. One row per item, minor items included — a run without this inventory is an incomplete run.
- **Capability catalog (when Agent D ran):** D's report becomes `.agent/THEME-CAPABILITIES.md` — identical to what figma-shopify-composer produces (spec: REFERENCE.md §THEME-CAPABILITIES.md); one canonical doc, never forked.

Done when: verdict + evidence stated; every tripwire re-verified at its cited line; conventions, dev-loop facts, failure modes, the full merged reuse inventory, and the capability catalog (or the fresh-doc reuse decision) recorded.

## Step 3 — Plan gate

Bullet outline per doc, every bullet tagged with its source (scan / ClickUp / transcript). Any target file that already exists: show the diff. Wait for approval.

## Step 4 — Generate

Write per [REFERENCE.md](REFERENCE.md), shaped like [EXAMPLES.md](EXAMPLES.md):

| output | note |
|---|---|
| AGENTS.md | repo root — agents auto-load it there; canonical rules, the lean entry doc |
| CLAUDE.md | repo root — `ln -s AGENTS.md CLAUDE.md` (fallback: REFERENCE.md §CLAUDE.md) |
| .agent/client-theme-onboarding/ARCHITECTURE.md | the map: tree, deviations, build/deploy flow |
| .agent/COMPONENTS.md | reuse inventory (shared doc): five category tables + the check-first rule; knowledge-doc header — written only when absent or stale, identical to figma-shopify-builder's production |
| .agent/THEME-CAPABILITIES.md | capability catalog (shared doc) from Agent D: eight fixed §-sections, knowledge-doc header — written only when absent or stale, identical to figma-shopify-composer's production |
| .agent/client-theme-onboarding/COMMANDS.md | command table + `error → cause → fix` table |
| .agent/client-theme-onboarding/REVAMP-TODO.md | task rows + open-questions table |
| shopify.theme.toml | repo root — the Shopify CLI reads it there; spec: REFERENCE.md §shopify.theme.toml |

Then:
- Append `AGENTS.md`, `CLAUDE.md`, and `.agent/` to `.git/info/exclude` — agency-internal, never in the client repo (the `.agent/` line also covers the build skills' knowledge docs and visual-check outputs).
- Save three memories, cross-linked with `[[…]]`: `project` (client, scope, contacts, deadlines) · `feedback` (deploy-safety rules + tripwires) · `reference` (build-system cheatsheet).

Done when: all eight outputs present — the two shared docs reused when already fresh, written otherwise — exclusions appended, three memories saved.

## Step 5 — Verify + contract lint (fresh eyes)

1. Lint every generated doc against the Doc Contract, all 8 items per doc, via ONE fresh general-purpose subagent — the writer under-reports its own violations. Its prompt carries: the 8 contract items verbatim, the absolute paths of every generated doc plus this skill's REFERENCE.md (heading contracts + line budgets), and the return shape `doc | contract # | line | violation | fix`. Regenerating a single doc → lint inline instead.
2. Fix every returned violation before reporting; heading/budget disputes resolve in REFERENCE.md's favor.
3. Confirm every cross-doc pointer resolves; `readlink CLAUDE.md` prints `AGENTS.md`.
4. Report: branch · files written · STANDARD/CUSTOM verdict · violations found → fixed · open questions grouped by source (ClickUp gaps, transcript ambiguities, scan unknowns) — the same list as REVAMP-TODO.md's table.
