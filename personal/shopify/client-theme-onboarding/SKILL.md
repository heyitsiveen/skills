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
5. **Scannable** — fixed heading contract per doc (REFERENCE.md; for the two shared knowledge docs, the format specs in `references/`); an agent greps a heading and lands on the answer.
6. **Example-driven** — ✅ correct / ❌ wrong pairs for every rule with a common wrong path.
7. **Failure-explicit** — `error → cause → fix` tables for every failure the scan or the user surfaced.
8. **Progressive disclosure** — AGENTS.md is the lean entry; depth lives in ARCHITECTURE.md / COMPONENTS.md / THEME-CAPABILITIES.md / COMMANDS.md / REVAMP-TODO.md, loaded on demand.

The contract binds this skill's own files too.

## Step 1 — Interview

Ask the user for five inputs. Record each answer or an explicit "none":

1. **Working branch** — `git checkout <branch>`; if missing, create it from the base branch.
2. **Prefix** — a short, unique namespace for everything built for this client (e.g. `acme`). Suggest a default derived from the client/project name; the user can override. Scope: every new theme artifact from this point forward — section/snippet filenames (`sections/{prefix}-x.liquid`), custom-element tags (`<{prefix}-x>` — conveniently supplies the hyphen custom elements require), CSS classes/custom properties (`.{prefix}-x__part`, `--{prefix}-gap`), schema block/setting IDs, JS module/function names. Recorded with before/after examples in AGENTS.md 🧩 (spec: REFERENCE.md §AGENTS.md).
3. **Store + environments** for `shopify.theme.toml` — store handle (`*.myshopify.com`); per-environment theme IDs only if the user wants them (offer `shopify theme list --store <handle>`). Recommend store-only — rationale + spec: REFERENCE.md §shopify.theme.toml.
4. **ClickUp project details** — pasted text or a file path. Optional.
5. **Meeting transcript** — pasted text or a file path. Optional.

Done when: branch checked out, answers 1–5 recorded.

## Step 2 — Deep scan (read-only; Explore subagents in parallel — A–D, plus a shard's extra scanners)

Nothing in the theme repo is written in this step — a sharded scan's shard reports go to the run's working directory, and Step 4 does every write to `.agent/`. Launch all agents in ONE message so they run in parallel; collect every report before Step 3. A subagent sees nothing of this conversation and Explore skips CLAUDE.md — each prompt carries its full ask plus three standing demands: every fact cited as `path:line` · actual commands/paths/IDs, never paraphrases · final message = the complete report.

**Knowledge-doc check first (main thread, before dispatch).** Read `.agent/COMPONENTS.md` and `.agent/THEME-CAPABILITIES.md` where they exist and run each spec's §Format version against its doc — [`references/components-format.md`](references/components-format.md), [`references/theme-capabilities-format.md`](references/theme-capabilities-format.md). That ladder decides FULL, INCREMENTAL, read-as-fresh, or read-as-newer; what it adds here is which agents dispatch — read-as-fresh and read-as-newer stand B and C, or D, down, and a read-as-newer doc is named in the Step 5 report.

- **Agent A — survey + tripwire candidates:** directory tree; every config file; `package.json` scripts; build tooling; linting; CI workflows (which branch pushes deploy, and to where); committed secrets (`.npmrc`, `.env` — paths only, never values); sync exclusions (the build tool's ignore files); existing docs / `.agent/` knowledge docs (`THEME-CAPABILITIES.md`, `COMPONENTS.md`, `app-widget-*.md`) / `.shopifyignore` / `shopify.theme.toml` / CLAUDE.md / AGENTS.md; conventions — section/snippet naming, CSS approach, JS patterns, schema style, app footprint (Klaviyo, Judge.me, subscriptions…); dev loop — the exact sync command, watcher detection (`pgrep` pattern), every known failure mode (these become the `error → cause → fix` rows).
- **Agent B — reuse inventory, JS side:** the JavaScript source tree.
- **Agent C — reuse inventory, Liquid/CSS side:** every Liquid file — `sections/`, `blocks/`, `snippets/`, `layout/`, `templates/` — and every stylesheet; between them B and C read every file the theme ships.
- **Agent D — capability catalog:** `config/settings_schema.json` · every `.liquid` file in `sections/` and `blocks/` · `templates/**/*.json` recursively · section-group JSON for its §Conventions settings-usage aspect · the layout, the CSS-variable snippet, and the theme's stylesheets · the sections that read metafields or metaobjects.
- What each of B, C, and D looks for in its tree, and every fact its rows carry, is its format spec's job — for B and C, §Which category a row belongs to and the sources it lists; for D, §Row schemas. Each reads the theme against its spec.
- Each of B, C, and D opens its prompt with the absolute path of its format spec (B and C: `references/components-format.md`; D: `references/theme-capabilities-format.md`) and this instruction: **read that spec in full before writing a byte of the doc, and reproduce the block it gives.** The doc's shape comes from the spec. The prompt carries the run's context — repo path, mode (FULL or INCREMENTAL with the entries to refresh), and the files in scope.
- Above a spec's sharding threshold, that doc's agent dispatches as the 2–3 scanners the spec defines, each carrying its file range; the main thread merges their shards.
- Small repo (quick `ls` first: fewer than ~40 files across sections/, snippets/, JS source): skip the fan-out, scan inline — identical coverage, same demands.

Merge in the main thread — subagent reports are leads, not sources:

- **Tripwires** — record each as `action → consequence → rule`, only after re-reading the cited `path:line` yourself; also glob the CI workflow dir directly. A tripwire missed or invented by a scan agent is the one failure this run cannot absorb; recording one unread is a Contract #2 violation.
  - CI workflows: which branch pushes deploy, and to where. A push that auto-deploys the live storefront is the repo's most important fact.
  - Committed secrets (`.npmrc`, `.env`): flag for rotation; the values never enter the docs.
  - Sync exclusions (the build tool's ignore files): paths that never auto-sync get a manual-move workflow in the docs.
- **Verdict: STANDARD or CUSTOM.** STANDARD = `assets/ config/ layout/ locales/ sections/ snippets/ templates/` (+ optional `blocks/`) at the repo root, no build pipeline in front. CUSTOM = source dirs, compile step, framework, generated output, nesting. State the verdict with evidence; the docs describe the ACTUAL structure.
- **Reuse inventory (REQUIRED — every onboarding ends with `.agent/COMPONENTS.md` present and past its gate; never dropped under time or scope pressure):** an existing fresh or higher-format doc is reused as it stands; otherwise merge B + C into `.agent/COMPONENTS.md` per `references/components-format.md` — Flows, Patterns, and Animations arrive split across the two, so merge those by feature. One canonical doc, never forked. A run without this inventory is an incomplete run.
- **Capability catalog (when Agent D ran):** D's output is `.agent/THEME-CAPABILITIES.md` per `references/theme-capabilities-format.md`; one canonical doc, never forked.
- **Completeness gate** — run each scanned or merged doc's gate (its spec's §Completeness gate) on the content, here, before Step 3. A higher-format doc is read as-is and declared rather than gated by this older spec. A shortfall re-dispatches only the section or category that fell short; a section still short after that second dispatch carries its expected count, actual count, and missing names into the Step 5 report. Step 4 writes gated content; Step 5 runs the gate again on the file on disk.

Done when: verdict + evidence stated; every tripwire re-verified at its cited line; conventions, dev-loop facts, failure modes recorded; both knowledge docs past their gates — merged this run, refreshed incrementally, read as fresh, or read as higher-format and declared.

## Step 3 — Plan gate

Bullet outline per doc, every bullet tagged with its source (scan / ClickUp / transcript). Any target file that already exists: show the diff. Wait for approval.

## Step 4 — Generate

Write per [REFERENCE.md](REFERENCE.md), shaped like [EXAMPLES.md](EXAMPLES.md):

| output | note |
|---|---|
| AGENTS.md | repo root — agents auto-load it there; canonical rules, the lean entry doc |
| CLAUDE.md | repo root — `ln -s AGENTS.md CLAUDE.md` (fallback: REFERENCE.md §CLAUDE.md) |
| .agent/client-theme-onboarding/ARCHITECTURE.md | the map: tree, deviations, build/deploy flow |
| .agent/COMPONENTS.md | reuse inventory (shared doc) — shape: [`references/components-format.md`](references/components-format.md) |
| .agent/THEME-CAPABILITIES.md | capability catalog (shared doc) from Agent D — shape: [`references/theme-capabilities-format.md`](references/theme-capabilities-format.md) |
| .agent/client-theme-onboarding/COMMANDS.md | command table + `error → cause → fix` table |
| .agent/client-theme-onboarding/REVAMP-TODO.md | task rows + open-questions table |
| shopify.theme.toml | repo root — the Shopify CLI reads it there; spec: REFERENCE.md §shopify.theme.toml |

Then:
- Append `AGENTS.md`, `CLAUDE.md`, and `.agent/` to `.git/info/exclude` — agency-internal, never in the client repo (the `.agent/` line also covers every skill's knowledge docs and visual-check outputs).
- Save three memories, cross-linked with `[[…]]`: `project` (client, scope, contacts, deadlines) · `feedback` (deploy-safety rules + tripwires) · `reference` (build-system cheatsheet).

The two shared docs are written from the gated content Step 2 merged — the same bytes, now on disk.

Done when: all eight outputs present — the two shared docs reused when fresh or higher-format, written otherwise — exclusions appended, three memories saved.

## Step 5 — Verify + contract lint (fresh eyes)

1. Lint every generated doc against the Doc Contract, all 8 items per doc, via ONE fresh general-purpose subagent — the writer under-reports its own violations. Its prompt carries: the 8 contract items verbatim, the absolute paths of every generated doc plus this skill's REFERENCE.md (heading contracts + line budgets) and, for the two shared docs, their format specs in `references/`, and the return shape `doc | contract # | line | violation | fix`. Regenerating a single doc → lint inline instead.
2. Fix every returned violation before reporting; heading/budget disputes resolve in REFERENCE.md's favor.
3. Run each shared doc's completeness gate against the file on disk — the same four checks, now measuring what was written; a higher-format doc is left as-is and reported with its version.
4. Confirm every cross-doc pointer resolves; `readlink CLAUDE.md` prints `AGENTS.md`.
5. Report: branch · files written · STANDARD/CUSTOM verdict · violations found → fixed · each shared doc's gate result with its reconciled counts, or its declared shortfall · any doc read at a higher `format:` and left unchanged · open questions grouped by source (ClickUp gaps, transcript ambiguities, scan unknowns) — the same list as REVAMP-TODO.md's table.
