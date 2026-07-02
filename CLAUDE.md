# Skills repo — conventions

This folder is the git repo root: the Claude Code marketplace files (`.claude-plugin/`, `README.md`, `skills.sh.json`) live here, and skills are organised as **bucket → domain → skill**:

```
<bucket>/<domain>/<skill-name>/SKILL.md
```

- **Bucket** — status/category: `engineering`, `personal`, `productivity`, `misc`, `in-progress`, `deprecated`.
- **Domain** — `global` for domain-agnostic skills, or a specific domain such as `shopify`, `nextjs`, etc.
- **Skill** — a folder named **exactly** as its `name:` frontmatter, holding `SKILL.md` (plus optional `REFERENCE.md`, `EXAMPLES.md`, `scripts/`, `references/`, or `evals/`).

Current buckets:

- `engineering/` — general dev tools (e.g. `engineering/global/gc`)
- `personal/` — my main skills (e.g. `personal/shopify/…`)
- `productivity/`, `misc/`, `in-progress/` — kept empty for future skills
- `deprecated/` — retired skills, kept for reference (never published)

## Three registries — keep them in sync

Every **active** skill (anything not under `deprecated/`) must be listed in all three:

1. **`README.md`** — one linked entry per skill, grouped by category and by invocation.
2. **`skills.sh.json`** — grouping config for the [skills.sh](https://skills.sh) directory (lists skills by `name`).
3. **`.claude-plugin/plugin.json`** — the `skills` array holds one `./<bucket>/<domain>/<name>` path per skill.

Skills under `deprecated/` must appear in **none** of the three. Whenever you add, rename, move, or retire a skill, update all three (and this file if a bucket or domain changes).

## Invocation

- **User-invoked** — run on demand: a slash command like `/gc`, or a skill whose frontmatter sets `user-invocable: true` (built to be triggered directly, usually with a structured prompt).
- **Model-invoked** — the agent reaches for them automatically when the task matches their `description`.

`README.md` groups each category's entries under **User-invoked** / **Model-invoked** headings.

## Distribution

The repo root is both a Claude Code **plugin marketplace** (`.claude-plugin/marketplace.json`) and a single bundled **plugin** (`.claude-plugin/plugin.json`, named `heyitsiveen-skills`). Install:

```sh
/plugin marketplace add heyitsiveen/skills
/plugin install heyitsiveen-skills@heyitsiveen
```

It's also installable via skills.sh: `npx skills add heyitsiveen/skills`.

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).
