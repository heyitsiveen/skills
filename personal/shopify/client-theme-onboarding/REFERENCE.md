# REFERENCE — output specs for the generated files

Applies on top of the Doc Contract (SKILL.md). `<angle-brackets>` = fill from a recorded source; a spec line with no source match becomes a row in REVAMP-TODO.md §Open questions.

## Shared rules

- Headings below are contracts: exact text (emoji included — stable grep anchors), exact order. Omit a section only where marked *conditional*; a STANDARD theme fills deviation sections with "none — standard layout", never omits them.
- Budgets are ceilings: AGENTS.md ≤ 120 lines · ARCHITECTURE.md ≤ 150 · COMMANDS.md ≤ 100 · REVAMP-TODO.md ≤ 150. COMPONENTS.md and THEME-CAPABILITIES.md are exempt — no ceiling; one dense row per item, completeness beats brevity.
- Dates absolute (`2026-07-10`, never "today"); paths repo-relative; every command copy-paste runnable.
- One fact, one home: safety → AGENTS.md · structure → ARCHITECTURE.md · reusable building blocks → COMPONENTS.md · settings-level capabilities → THEME-CAPABILITIES.md · commands/failures → COMMANDS.md · tasks/questions → REVAMP-TODO.md. Other docs point by filename, never restate.

## AGENTS.md — canonical rules (lean entry doc)

```markdown
# Project Rules — <Client> Theme (<Agency> revamp)

> <STANDARD|CUSTOM> · <build system, or "no build pipeline">.
> Depth docs in `.agent/client-theme-onboarding/`: Map **ARCHITECTURE.md** · Tasks **REVAMP-TODO.md** · Commands **COMMANDS.md**. Shared docs at `.agent/`: Reuse **COMPONENTS.md** · Capabilities **THEME-CAPABILITIES.md**.

## 🚫 Git & deploy safety (non-negotiable)
| action | consequence | rule |
|---|---|---|
| push to `<branch>` | `<workflow file>` auto-deploys <target> | never push `<branch>` |
| <one row per CI/secret/sync tripwire from the scan> | | |
- Work ONLY on `<working branch>`. Commit only when explicitly asked<; commit convention if enforced, e.g. Angular Conventional Commits (commitlint)>.
- Never edit or publish the client's live/published theme.
- `AGENTS.md`, `CLAUDE.md`, and `.agent/` are in `.git/info/exclude` — never commit them.
- <Committed secret: `<file>` — treat as secret, rotation flagged; value not reproduced here.>

## 🎨 Tech stack (always)
- ✅ edit `<source path>` · ❌ edit `<compiled/generated path>` — <reason, one line>.
- <one ✅/❌ pair per always/never rule from the scan>

## 🛠 Build & dev loop
- `<install + watch/dev command>` → syncs to <target theme, with id>.
- Before starting a watcher AND before edits meant to sync: `<pgrep pattern>` — empty output = safe to start; two watchers double-upload.
- <generator/scaffold commands; watcher-restart caveats>
- *(conditional: file exists)* `<path>/shopify.theme.toml` stays store-only — never add a `theme` id; rationale in its header comment.

## 🔄 What does NOT auto-sync   *(conditional: sync exclusions exist)*
- <excluded patterns> → manual move: <exact workflow — admin paste / upload>.
- Standing instruction: any change touching an excluded path → end the response with the exact file(s) + content the user must move.

## 🧩 Code conventions
- <naming · CSS approach · JS pattern · schema style — one line each, with one example path from the repo>
- Everything new is namespaced `{prefix}-`: ✅ `sections/{prefix}-testimonial-carousel.liquid` ❌ `sections/testimonial-carousel.liquid` · ✅ `<{prefix}-carousel>` ❌ `<theme-carousel>` · ✅ `.{prefix}-carousel__track`, `--{prefix}-gap` ❌ `.carousel__track`, `--gap` — same for schema block/setting IDs and JS module/function names.
- Before writing new code: search `.agent/COMPONENTS.md` by reuse keyword — match → reuse or extend it; no match → build new under `{prefix}-`.

## 📚 Knowledge docs (check before any theme scan)
| doc | consult when |
|---|---|
| `.agent/THEME-CAPABILITIES.md` | before scanning sections/blocks/settings schemas — the capability catalog |
| `.agent/COMPONENTS.md` | before writing new sections, blocks, snippets, or shared behavior — the reuse inventory |
| `.agent/shopify-app-restyle/app-widget-<handle>.md` | before inspecting that app's widget DOM |
- A missing doc is produced — identically, whichever skill produces it — by the first skill that needs it. Read the doc, then its header: a `format:` older than the reading skill's spec means regenerate, a newer one means read it as it stands and say so, a matching one means read it where the disk agrees and refresh only the entries the disk has moved past. "refresh …" from the user forces a regenerate.
- Every skill's own artifacts land under `.agent/<skill-name>/`; shared docs sit at `.agent/` root.

## 📐 Working style
- Smallest diff that works; read before editing; check in before major changes; ask when multiple valid approaches exist.

## 🌍 Project facts
- <agency / client / contacts / markets / paid deliverables — one line each, sourced from ClickUp or transcript>
```

## CLAUDE.md — symlink to AGENTS.md

```sh
ln -s AGENTS.md CLAUDE.md   # run at repo root
readlink CLAUDE.md          # pass condition: prints AGENTS.md
```

- Both names go into `.git/info/exclude`.
- Fallback where symlinks fail (e.g. Windows checkout): a 2-line CLAUDE.md — line 1 `@AGENTS.md`, line 2 `<!-- pointer file: edit AGENTS.md only -->`.
- Converting an existing full-mirror CLAUDE.md: the deletion appears in the Step 3 diff before anything is written.

## ARCHITECTURE.md — the map

Required sections, exact order:

1. `## Directory tree` — real tree (depth ≤ 3), one `# role` comment per line.
2. `## Deviations from standard` — table `standard expectation | this repo | consequence for agents`. STANDARD theme: single row "none — standard layout".
3. `## Build & deploy flow` — one arrow chain per pipeline (`edit <src> → compile <out> → sync <how> → theme <id>`), then CI table `workflow | trigger | deploys to`.
4. `## Key templates, sections, snippets` — table `path | role | edit or leave`.
5. `## Data flow & integrations` — table `integration | hook point | owned by` (settings, metafields, APIs, apps).

## The two shared knowledge docs

`.agent/COMPONENTS.md` (reuse inventory, REQUIRED on every run) and `.agent/THEME-CAPABILITIES.md` (capability catalog). One canonical doc each, never forked, shared with every other skill in the suite.

**Their shape comes from their format specs, not from this file.** Read the spec in full before writing a byte of either doc, and reproduce the block it gives:

| doc | spec |
|---|---|
| `.agent/COMPONENTS.md` | [`references/components-format.md`](references/components-format.md) |
| `.agent/THEME-CAPABILITIES.md` | [`references/theme-capabilities-format.md`](references/theme-capabilities-format.md) |

Each spec carries the block to reproduce, the header fields, a row schema per section, how a `format:` version decides between regenerate / refresh / read-as-is, the completeness gate, and the sharding threshold. This skill's run context — which agent reads which tree, and when the docs are written — is Step 2 and Step 4 of SKILL.md.

The reuse inventory is the doc that stops rebuilds: build and composition tasks search it by reuse keyword before writing anything new, and AGENTS.md 🧩 carries that rule so every later session obeys it without re-asking.

## COMMANDS.md — commands + failures

Two tables (split table 1 by `## <group>` headings only when > 15 rows):

1. `command | does | when to run | ⚠️` — every `package.json` script and every theme-CLI command accounted for; ⚠️ names the tripwire or stays empty.
2. `error | cause | fix` — every failure mode recorded in Step 2 (build, sync, editor, CLI).

## REVAMP-TODO.md — tasks + open questions

1. `- [ ]` rows grouped under `## <area>` headings (areas = ClickUp scope): `- [ ] <task> — <CU|TR|scan><, P1 / 💰 paid extra / deadline YYYY-MM-DD if any>`.
2. Final section `## Open questions` — table `question | who answers | blocks`. The one deliberately human-readable block: phrased so the client/PM can answer; agents surface these, never resolve them.

## shopify.theme.toml

```toml
# Verification-only: the dev loop is <real dev command>, not Shopify CLI.
# No `theme` id: `shopify theme dev` creates its own disposable dev theme — an id
# would aim the CLI at a real theme. No `password`: first run does interactive
# `shopify auth login`, so no credential is copied out of <credential file>.
[environments.default]
store = "<handle>.myshopify.com"
ignore = ["<build-source>/**"]   # only non-theme files
```

- Extra `[environments.<env>]` blocks with `theme = "<id>"` only when the user supplied IDs in Step 1.
- The header comment is the rationale's single home — AGENTS.md links to it, never restates it.
