---
name: client-theme-onboarding
description: Generate AI-facing docs for a client Shopify theme repo — deep-scan the theme, then write the agent doc pack (AGENTS.md + CLAUDE.md symlink, ARCHITECTURE.md, COMPONENTS.md reuse inventory, COMMANDS.md, REVAMP-TODO.md, shopify.theme.toml) in imperative, grounded, token-lean form for Claude Code/LLM agents, not humans. Use when the user asks to onboard a client theme, write docs for the agent, create a CLAUDE.md / AGENTS.md / AI-readable reference for a theme repo, or regenerate one of the pack docs.
---

# Client Theme Onboarding — AI-facing docs

Every doc this skill writes is consumed by agents (Claude Code, LLM tools), not humans. Purpose: make every future agent session on this repo more accurate and cheaper to run. The user reads gates and reports; the docs are machine instructions.

Assume zero prior knowledge of the theme and nothing about its structure. Four gates, strictly in order: **interview → deep scan → plan approval → write**; each gate opens only with the user's input or approval.

## Doc Contract — every generated doc passes all 8

1. **Imperative + unambiguous** — exact commands, paths, IDs, values. Banned: "run the appropriate command", "as needed", marketing/tutorial prose.
2. **Grounded** — every claim traces to the scan, ClickUp, or the transcript. No source → it becomes an open question, never content.
3. **Deterministic** — each instruction is executable or checkable without interpretation: a command, a path, a pass/fail condition.
4. **Token-efficient** — tables/lists over paragraphs; one fact lives in one file; other files point to it by filename instead of restating.
5. **Scannable** — fixed heading contract per doc (REFERENCE.md); an agent greps a heading and lands on the answer.
6. **Example-driven** — ✅ correct / ❌ wrong pairs for every rule with a common wrong path.
7. **Failure-explicit** — `error → cause → fix` tables for every failure the scan or the user surfaced.
8. **Progressive disclosure** — AGENTS.md is the lean entry; depth lives in ARCHITECTURE.md / COMPONENTS.md / COMMANDS.md / REVAMP-TODO.md, loaded on demand.

The contract binds this skill's own files too.

## Step 1 — Interview

AskUserQuestion, five inputs (the tool caps at four questions per call — split 3+2). Record each answer or an explicit "none":

1. **Working branch** — `git checkout <branch>`; if missing, create it from the base branch.
2. **Prefix** — a short, unique namespace for everything built for this client (e.g. `acme`). Suggest a default derived from the client/project name; the user can override. Scope: every new theme artifact from this point forward — section/snippet filenames (`sections/{prefix}-x.liquid`), custom-element tags (`<{prefix}-x>` — conveniently supplies the hyphen custom elements require), CSS classes/custom properties (`.{prefix}-x__part`, `--{prefix}-gap`), schema block/setting IDs, JS module/function names. Recorded with before/after examples in AGENTS.md 🧩 (spec: REFERENCE.md §AGENTS.md).
3. **Store + environments** for `shopify.theme.toml` — store handle (`*.myshopify.com`); per-environment theme IDs only if the user wants them (offer `shopify theme list --store <handle>`). Recommend store-only — rationale + spec: REFERENCE.md §shopify.theme.toml.
4. **ClickUp project details** — pasted text or a file path. Optional.
5. **Meeting transcript** — pasted text or a file path. Optional.

Done when: branch checked out, answers 1–5 recorded.

## Step 2 — Deep scan (read-only)

No writes of any kind in this step. Cover:

- Directory tree; every config file; `package.json` scripts; build tooling; linting; CI; existing docs; `.shopifyignore`; existing `shopify.theme.toml` / CLAUDE.md / AGENTS.md.
- **Tripwires** — record each as `action → consequence → rule`:
  - CI workflows: which branch pushes deploy, and to where. A push that auto-deploys the live storefront is the repo's most important fact.
  - Committed secrets (`.npmrc`, `.env`): flag for rotation; the values never enter the docs.
  - Sync exclusions (the build tool's ignore files): paths that never auto-sync get a manual-move workflow in the docs.
- **Verdict: STANDARD or CUSTOM.** STANDARD = `assets/ config/ layout/ locales/ sections/ snippets/ templates/` (+ optional `blocks/`) at the repo root, no build pipeline in front. CUSTOM = source dirs, compile step, framework, generated output, nesting. State the verdict with evidence; the docs describe the ACTUAL structure.
- Conventions: section/snippet naming, CSS approach, JS patterns, schema style, app footprint (Klaviyo, Judge.me, subscriptions…).
- Dev loop: the exact sync command; watcher detection (`pgrep` pattern); every known failure mode (these become the `error → cause → fix` rows).
- **Reuse inventory (REQUIRED — runs on every onboarding, never dropped under time or scope pressure):** catalog every existing reusable building block into the COMPONENTS.md row schema (REFERENCE.md §COMPONENTS.md). Five categories, named exactly as REFERENCE.md's headings: Custom web components · JavaScript · Functions (= reusable Liquid utility snippets/filters) · Flows (add-to-cart, quick-view, facets) · Patterns (drawer, sticky header, sold-out state). One row per item, minor items included — a run without this inventory is an incomplete run.

Done when: verdict + evidence stated; tripwires, conventions, dev-loop facts, failure modes, and the full reuse inventory recorded.

## Step 3 — Plan gate

Bullet outline per doc, every bullet tagged with its source (scan / ClickUp / transcript). Any target file that already exists: show the diff. Wait for approval.

## Step 4 — Generate

Write per [REFERENCE.md](REFERENCE.md), shaped like [EXAMPLES.md](EXAMPLES.md):

| output | note |
|---|---|
| AGENTS.md | canonical rules — the lean entry doc |
| CLAUDE.md | `ln -s AGENTS.md CLAUDE.md` (fallback: REFERENCE.md §CLAUDE.md) |
| ARCHITECTURE.md | the map: tree, deviations, build/deploy flow |
| COMPONENTS.md | reuse inventory: five category tables + the check-first rule |
| COMMANDS.md | command table + `error → cause → fix` table |
| REVAMP-TODO.md | task rows + open-questions table |
| shopify.theme.toml | spec: REFERENCE.md §shopify.theme.toml |

Then:
- Append the six doc names (AGENTS, CLAUDE, ARCHITECTURE, COMPONENTS, COMMANDS, REVAMP-TODO) to `.git/info/exclude` — agency-internal, never in the client repo.
- Save three memories, cross-linked with `[[…]]`: `project` (client, scope, contacts, deadlines) · `feedback` (deploy-safety rules + tripwires) · `reference` (build-system cheatsheet).

Done when: seven outputs written, exclusions appended, three memories saved.

## Step 5 — Verify + contract lint

1. Lint every generated doc against the Doc Contract, all 8 items per doc. Fix violations before reporting.
2. Confirm every cross-doc pointer resolves; `readlink CLAUDE.md` prints `AGENTS.md`.
3. Report: branch · files written · STANDARD/CUSTOM verdict · open questions grouped by source (ClickUp gaps, transcript ambiguities, scan unknowns) — the same list as REVAMP-TODO.md's table.
