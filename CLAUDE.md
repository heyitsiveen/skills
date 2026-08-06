# Skills repo — conventions

This folder is the git repo root: the Claude Code marketplace files (`.claude-plugin/`, `README.md`, `skills.sh.json`) live here, and skills are organised as **bucket → domain → skill**:

```
<bucket>/<domain>/<skill-name>/SKILL.md
```

- **Bucket** — status/category: `engineering`, `personal`, `productivity`, `misc`.
- **Domain** — `global` for domain-agnostic skills, or a specific domain such as `shopify`, `nextjs`, etc.
- **Skill** — a folder named **exactly** as its `name:` frontmatter, holding `SKILL.md` (plus optional `REFERENCE.md`, `EXAMPLES.md`, `scripts/`, `references/`, or `evals/`).

Current buckets:

- `engineering/` — general dev tools (e.g. `engineering/global/gc`)
- `personal/` — my main skills (e.g. `personal/shopify/…`)
- `productivity/`, `misc/` — kept empty for future skills

## Three registries — keep them in sync

Every skill must be listed in all three:

1. **`README.md`** — one linked entry per skill, grouped by category and by invocation.
2. **`skills.sh.json`** — grouping config for the [skills.sh](https://skills.sh) directory (lists skills by `name`).
3. **`.claude-plugin/marketplace.json`** — each bucket is published as its own plugin (`heyitsiveen-skills-<bucket>`); that plugin's `skills` array holds one `./<domain>/<name>` path per skill (relative to the bucket's `source`).

Whenever you add, rename, move, or retire a skill, update all three (and this file if a bucket or domain changes).

## Invocation

- **User-invoked** — run on demand: a slash command like `/gc`, or a skill whose frontmatter sets `user-invocable: true` (built to be triggered directly, usually with a structured prompt).
- **Model-invoked** — the agent reaches for them automatically when the task matches their `description`.

`README.md` groups each category's entries under **User-invoked** / **Model-invoked** headings.

## Client-theme skill suite — client-repo output convention

The six skills `figma-shopify-composer`, `figma-shopify-builder`, `figma-shopify-globals`, `shopify-app-restyle`, `client-theme-onboarding`, and `bugherd-qa-fixer` (all `personal/shopify/`) write every artifact inside a client theme repo under `.agent/`: shared knowledge docs at its root, each produced only when absent or stale and identically by any of their producers (`THEME-CAPABILITIES.md` — globals, composer, builder, or onboarding; `COMPONENTS.md` — globals, composer, builder, or onboarding), kept current by the skills that add theme artifacts (globals → both docs plus the retained mapping table; builder → both docs; restyle → a COMPONENTS.md row per override stylesheet, plus an Animations row when the override adds reusable motion; bugherd-qa-fixer → dated append-only lines, and only where a doc already exists — it never creates one), per-skill outputs in `.agent/<skill-name>/` (globals mapping/evidence, onboarding depth docs, `app-widget-<handle>.md`, `visual-check/`, bugherd-qa-fixer's `remaining/` + `notes/` + `evidence/`). `AGENTS.md`, its `CLAUDE.md` symlink, and `shopify.theme.toml` stay at the client repo root; everything is kept out of git via `.git/info/exclude`.

The three Figma-measuring skills — composer, builder, restyle — additionally share one visual-check convention: `visual-check/<name>/` holds only root-level `figma-desktop.png` / `figma-mobile.png`, `result-desktop.png` / `result-mobile.png`, and `diff-desktop.png` / `diff-mobile.png`; restyle may add an approved `-<state>` suffix to each class. No `clean-`, `section-`, or other render variants are generated. `assets/` remains flat for per-asset exports; assets ship as client-uploaded files rather than inline SVG; verification hardcodes them and proves the revert; each per-asset export is the design's crop, with the uncropped original kept beside it as `original-source-*`. Their `## Asset export` sections are byte-identical and change together. `## Asset delivery` and `## Hardcode-then-revert` diverge on purpose, because the three have different write surfaces — builder owns a section file, composer only template JSON, restyle only its override stylesheet — and where one cannot reach a destination it declares that rather than downgrading silently.

The two knowledge-doc format specs — `references/theme-capabilities-format.md` and `references/components-format.md` — are byte-identical across the four producer skills: `client-theme-onboarding`, `figma-shopify-builder`, `figma-shopify-composer`, and `figma-shopify-globals`. They change together. Before committing a format-spec change, run this from the repo root; every comparison must exit 0:

```sh
for spec in theme-capabilities-format.md components-format.md; do
  base="personal/shopify/client-theme-onboarding/references/$spec"
  cmp -s "$base" "personal/shopify/figma-shopify-builder/references/$spec" &&
    cmp -s "$base" "personal/shopify/figma-shopify-composer/references/$spec" &&
    cmp -s "$base" "personal/shopify/figma-shopify-globals/references/$spec" || exit 1
done
```

The duplication is deliberate.

When editing these skills, keep every path on this convention and the six skills in agreement.

## Distribution

The repo root is a Claude Code **plugin marketplace** (`.claude-plugin/marketplace.json`). Each top-level bucket is published as its own plugin, `heyitsiveen-skills-<bucket>`, defined **inline** in the marketplace (`strict: false`, so there is no per-bucket `plugin.json`). Empty buckets are listed but stay hidden in `/plugin` Discover until they hold a skill. Install the marketplace, then the buckets you want:

```sh
/plugin marketplace add heyitsiveen/skills
/plugin install heyitsiveen-skills-personal@heyitsiveen
/plugin install heyitsiveen-skills-engineering@heyitsiveen
```

It's also installable via skills.sh: `npx skills add heyitsiveen/skills`.

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).
