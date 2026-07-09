# Blueprints — the six generated files

Shared rules: short sections, bold key terms, concrete commands over prose; every claim sourced (scan / ClickUp / transcript). When the theme is STANDARD, the deviation sections say so plainly instead of being omitted.

## AGENTS.md — canonical agent rules

The one file any coding agent must obey. Order matters — safety first:

```markdown
# Project Rules — <Client> Theme (<Agency> revamp)

> <One line: STANDARD/CUSTOM verdict + build system.>
> Full architecture: **ARCHITECTURE.md**. Task tracker: **REVAMP-TODO.md**. Commands: **COMMANDS.md**.
> _This file mirrors CLAUDE.md — keep the two in sync._

## 🚫 Git & deploy safety (non-negotiable)
- Work ONLY on `<branch>`. Never commit or push to <deploy branches>.
- <Every CI tripwire: "pushing X auto-deploys to Y" — from the workflows.>
- Never edit or publish the client's live/published theme.
- Commit only when explicitly asked. <Commit convention, if enforced — commitlint etc.>
- Never commit the internal docs (AGENTS/CLAUDE/ARCHITECTURE/COMMANDS/REVAMP-TODO) — kept in `.git/info/exclude`.
- <Committed secrets found in the scan: treat as secrets, flagged for rotation.>

## 🎨 Tech stack (always)
- <Source-of-truth dirs; compiled/generated paths that must never be hand-edited.>

## 🛠 Build & dev loop
- <Install + dev/watch command and its target theme.>
- Before starting a watcher (and before edits meant to sync), check one isn't already
  running (`<pgrep pattern>`) — two watchers double-upload and fight.
- <Scaffolding/generator commands; restart-the-watcher caveats.>

## 🔄 What does NOT auto-sync            <!-- only if the build tool has sync exclusions -->
- <Excluded patterns + the manual-move workflow (admin copy-paste / upload).>
- Standing instruction: any change touching an excluded path → end the response with the
  exact file(s) and content the user must move manually.

## 🧩 Code conventions
- <Naming, CSS approach, JS patterns, schema style — from the scan.>

## 📐 Working style
- Smallest diff that works; read before editing; check in before major changes;
  ask when multiple valid approaches exist.

## 🌍 Project facts
- <Agency / client / contacts / markets / paid deliverables — from ClickUp + transcript.>
```

## CLAUDE.md — Claude Code entry point

Same body as AGENTS.md — they are mirrors, each header naming the other — so Claude Code and every other agent obey identical rules. If the user prefers a thin CLAUDE.md instead: a pointer to AGENTS.md plus the workflow rules (interview before planning · plan approval before writes · read-before-edit · minimal diffs).

## ARCHITECTURE.md — the map

- Directory tree (real, from the scan) with one-line annotations.
- **How this deviates from a standard theme** — the CUSTOM specifics, or "standard layout" stated.
- Build & deploy flow: source → compile → sync → theme; CI pipelines and their triggers.
- Key templates/sections/snippets and how a page assembles; data flow (settings, metafields, APIs).
- Integrations & apps (from the scan footprint) and where each hooks in.

## COMMANDS.md — every command that matters

Grouped: setup · dev loop · build · lint/format/check · generators · theme CLI (`shopify theme dev/push/pull` with correct flags/environments) · CI. Every `package.json` script accounted for. Deploy-capable commands carry a ⚠️ and the reason (tripwires).

## REVAMP-TODO.md — the actionable checklist

- `- [ ]` items grouped by area (from the ClickUp scope), each traceable to ClickUp or the transcript.
- Priorities and special requests flagged (**P1**, 💰 paid extra, deadline dates).
- Bottom section: **Open questions** — everything unresolved, phrased so the client/PM can answer.

## shopify.theme.toml

```toml
[environments.development]
store = "<handle>.myshopify.com"
ignore = ["<build-source>/**"]   # only what isn't a real theme file

# Only if the user supplied IDs in Step 1:
[environments.staging]
store = "<handle>.myshopify.com"
theme = "<staging id>"
```

- Default is development-only and store-only: no `theme` id (the CLI creates a disposable dev theme; an id would aim it at a real one) and no `password` (interactive `shopify auth login` beats a copied token of the wrong type).
- Document this rationale in AGENTS.md/CLAUDE.md so nobody "fixes" the file by adding a theme id later.
