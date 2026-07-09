---
name: client-theme-onboarding
description: Onboard a client Shopify theme repo from zero — interview, deep-scan, classify standard vs custom, then generate AGENTS.md, CLAUDE.md, ARCHITECTURE.md, COMMANDS.md, REVAMP-TODO.md and shopify.theme.toml. Use when the user asks to onboard a client theme, set up working docs / agent rules for a theme repo, or regenerate one of those onboarding docs.
---

# Client Theme Onboarding

A client's theme: assume zero prior knowledge, and assume nothing about its structure — many client themes are not standard Shopify. Four gates, strictly in order: **interview → deep scan → plan approval → write**; each gate opens only with the user's input or approval.

Every sentence in the generated docs must trace to a source — the scan, the ClickUp details, or the meeting transcript. What no source answers becomes an open question, recorded, never invented.

Read any file before editing it; smallest possible diffs; files outside the six targets need the user's OK first.

## Step 1 — Interview

One AskUserQuestion call, four questions; record every answer (or explicit "none"):

1. **Working branch** for the revamp — check it out; create it from the base branch if it doesn't exist.
2. **Store + environments** for `shopify.theme.toml` — store handle (`*.myshopify.com`), plus per-environment theme IDs only if the user wants them (offer `shopify theme list --store <handle>` if the IDs aren't handy). Recommend **store-only — no `theme` id, no `password`**: `shopify theme dev` then creates its own disposable development theme and cannot touch the dev, staging, or live theme; an id in the toml would point the CLI at a real one.
3. **ClickUp project details** — pasted text or a file path (scope, special requests, notes, deadlines). Optional.
4. **Meeting transcript** — pasted text or a file path. Optional.

Done when: branch checked out and answers 1–4 recorded.

## Step 2 — Deep scan (read-only)

No writes of any kind in this step. Cover the whole repo:

- Directory tree; every config file; `package.json` scripts; build tooling; linting; CI; existing docs; `.shopifyignore`; any existing `shopify.theme.toml`, CLAUDE.md, or AGENTS.md.
- **Tripwires** — the facts that hurt the client if missed. Read every CI workflow: which branch pushes deploy, and to where? (A push that auto-deploys the live storefront is the most important fact in the repo.) Committed secrets (`.npmrc`, `.env` tokens): flag for rotation; the values stay out of the docs. Sync exclusions (the build tool's ignore files): paths that never auto-sync need a documented manual-move workflow.
- **Verdict: STANDARD or CUSTOM.** STANDARD = the Shopify dirs (`assets/ config/ layout/ locales/ sections/ snippets/ templates/`, optionally `blocks/`) at the repo root with no build pipeline in front of them. CUSTOM = source dirs, compile step, framework, generated output, nesting. State the verdict with its evidence; every generated doc describes the ACTUAL structure.
- Conventions: section/snippet naming, CSS approach, JS patterns, schema style, third-party app footprint (Klaviyo, Judge.me, subscriptions…).
- Dev loop: the exact command that syncs local ↔ theme, and how to detect an already-running watcher (a `pgrep` pattern) — the docs will carry the rule "check for a running watcher before starting one, and before edits meant to sync".

Done when: verdict + evidence stated, tripwires listed, conventions and dev-loop facts recorded.

## Step 3 — Plan gate

Present a bullet outline of each generated file's contents, every bullet sourced (scan / ClickUp / transcript). Any target file that already exists: show the diff of what would change — the user sees every overwrite before it happens. Wait for approval.

## Step 4 — Generate

Blueprints for all six files: [templates.md](templates.md). Write:
AGENTS.md · CLAUDE.md · ARCHITECTURE.md · COMMANDS.md · REVAMP-TODO.md · shopify.theme.toml

Then:
- Add the five `.md` docs to `.git/info/exclude` — they are agency-internal and stay out of the client repo.
- Save three memories: `project` (client, scope, contacts, deadlines), `feedback` (deploy-safety rules the user gave + tripwires found), `reference` (build-system cheatsheet) — cross-linked with `[[…]]`.

Done when: six files written, exclusions added, three memories saved.

## Step 5 — Verify

Report: current branch · files written · the STANDARD/CUSTOM verdict restated · every unresolved question, grouped by source (ClickUp gaps, transcript ambiguities, scan unknowns). The same questions live at the bottom of REVAMP-TODO.md.
