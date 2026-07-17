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
3. **`.claude-plugin/marketplace.json`** — each bucket is published as its own plugin (`heyitsiveen-skills-<bucket>`); that plugin's `skills` array holds one `./<domain>/<name>` path per skill (relative to the bucket's `source`).

Skills under `deprecated/` must appear in **none** of the three. Whenever you add, rename, move, or retire a skill, update all three (and this file if a bucket or domain changes).

## Invocation

- **User-invoked** — run on demand: a slash command like `/gc`, or a skill whose frontmatter sets `user-invocable: true` (built to be triggered directly, usually with a structured prompt).
- **Model-invoked** — the agent reaches for them automatically when the task matches their `description`.

`README.md` groups each category's entries under **User-invoked** / **Model-invoked** headings.

## Figma→Shopify suite — client-repo output convention

The four skills `figma-shopify-composer`, `figma-shopify-builder`, `shopify-app-restyle`, and `client-theme-onboarding` (all `personal/shopify/`) write every artifact inside a client theme repo under `.agent/`: shared knowledge docs at its root, each produced only when absent and identically by either of its two producers (`THEME-CAPABILITIES.md` — composer, builder, or onboarding; `COMPONENTS.md` — onboarding or builder), per-skill outputs in `.agent/<skill-name>/` (onboarding depth docs, `app-widget-<handle>.md`, `visual-check/`). `AGENTS.md`, its `CLAUDE.md` symlink, and `shopify.theme.toml` stay at the client repo root; everything is kept out of git via `.git/info/exclude`. When editing these skills, keep every path on this convention and the four skills in agreement.

## Distribution

The repo root is a Claude Code **plugin marketplace** (`.claude-plugin/marketplace.json`). Each top-level bucket is published as its own plugin, `heyitsiveen-skills-<bucket>`, defined **inline** in the marketplace (`strict: false`, so there is no per-bucket `plugin.json`). Empty buckets are listed but stay hidden in `/plugin` Discover until they hold a skill. Install the marketplace, then the buckets you want:

```sh
/plugin marketplace add heyitsiveen/skills
/plugin install heyitsiveen-skills-personal@heyitsiveen
/plugin install heyitsiveen-skills-engineering@heyitsiveen
```

It's also installable via skills.sh: `npx skills add heyitsiveen/skills`.

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).
