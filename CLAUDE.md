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

`deprecated/` is **not** a bucket. It holds a byte-identical snapshot of a skill
as it stood before a rewrite, so the previous behaviour can be restored if the
replacement misbehaves. It mirrors the same `<domain>/<skill-name>/` layout, is
listed in none of the three registries, is published by no plugin, and is
skipped by `scripts/check.sh`. Nothing reads a skill from it: to roll one back,
copy the folder over its `<bucket>/<domain>/` counterpart.

## Three registries — keep them in sync

Every skill must be listed in all three:

1. **`README.md`** — one linked entry per skill, grouped by category and by invocation.
2. **`skills.sh.json`** — grouping config for the [skills.sh](https://skills.sh) directory (lists skills by `name`).
3. **`.claude-plugin/marketplace.json`** — each bucket is published as its own plugin (`heyitsiveen-skills-<bucket>`); that plugin's `skills` array holds one `./<domain>/<name>` path per skill (relative to the bucket's `source`).

Whenever you add, rename, move, or retire a skill, update all three (and this file if a bucket or domain changes), then run `./scripts/check.sh`.

## Invocation

- **User-invoked** — run on demand: a slash command like `/gc`, or a skill whose frontmatter sets `user-invocable: true` (built to be triggered directly, usually with a structured prompt).
- **Model-invoked** — the agent reaches for them automatically when the task matches their `description`.

`README.md` groups each category's entries under **User-invoked** / **Model-invoked** headings.

## Client-theme skill suite — client-repo output convention

The seven skills `figma-shopify-composer`, `figma-shopify-builder`, `figma-shopify-globals`, `shopify-app-restyle`, `client-theme-onboarding`, `shopify-page-replicate`, and `bugherd-qa-fixer` (all `personal/shopify/`) write every artifact inside a client theme repo under `.agent/`: shared knowledge docs at its root, each produced only when absent or stale and identically by any of their producers (`THEME-CAPABILITIES.md` — globals, composer, builder, replicate, or onboarding; `COMPONENTS.md` — globals, composer, builder, replicate, or onboarding), kept current by the skills that add theme artifacts (globals → both docs plus the retained mapping table; builder → both docs; replicate → both docs, every replica section it wrote marked **Stand-in / do not reuse**; restyle → a COMPONENTS.md row per override stylesheet, plus an Animations row when the override adds reusable motion; bugherd-qa-fixer → dated append-only lines, and only where a doc already exists — it never creates one), per-skill outputs in `.agent/<skill-name>/` (globals mapping/evidence, onboarding depth docs, `app-widget-<handle>.md`, `visual-check/`, replicate's `replication.md`, bugherd-qa-fixer's `remaining/` + `notes/` + `evidence/`). `AGENTS.md`, its `CLAUDE.md` symlink, and `shopify.theme.toml` stay at the client repo root; everything is kept out of git via `.git/info/exclude`. `shopify-page-replicate` writes theme code on two surfaces and no others: the target template JSON, whose whole `order` it replaces, and — only for the sections the user chose to have built — new files under the theme's own `sections/`, `assets/` and `snippets/`, every one carrying the `replica-<template>-<name>` prefix. The Target theme's existing files are read-only in both passes.

The four **spec-driven** skills — composer, builder, restyle, and `shopify-page-replicate` — each build from a **design spec** and share one visual-check convention and one Phase 4. At `visual-check/<name>/` the root level holds only the design spec and two image classes. The three Figma-driven skills name them `figma-spec.md`, `figma-desktop.png` / `figma-mobile.png` and `result-desktop.png` / `result-mobile.png`; `shopify-page-replicate` drops the `figma-` prefix because its source is a rendered page, giving `design-spec.md`, `source-desktop.png` / `source-mobile.png` and the same `result-desktop.png` / `result-mobile.png`. restyle may add an approved `-<state>` suffix to each image class. No diff images are produced, and no `clean-`, `section-`, or other render variants are generated.

The shared seven-step Phase 4 — render → data check → capture hygiene → `style-reporter` → correction round → style report → cleanup — permits exactly three variations: builder's metafield/metaobject data check (step 2), reconciliation of the style report against the fidelity forecast (step 6), shared by composer and `shopify-page-replicate`, and restyle's per-state axis (steps 3, 4 and 6 run per state as well as per breakpoint). A fourth variation is a rule break. Two things in `shopify-page-replicate` that read like one are not. Its step 5 splits by pass — a reused section is corrected by adjusting settings values, a replica section by editing the code the run itself wrote — which is each surface's existing constraint applied, not a new variation. And it stops twice for approval where its three siblings call their plan phase the run's only stop: stop 1 approves the plan, stop 2 approves the design of the replica sections and fires only when stop 1 chose to build at least one. One stop would mean a single page-scale plan covering both a whole composition and the full design of new section code — long enough that nobody reads it, and an unread approval is not an approval. See `docs/adr/0004-replicate-has-two-approval-stops.md`. The steps' presence and order are asserted by `scripts/check.sh`, which also refuses an eighth; that the three variations are the only ones is still enforced by reading the four Phase 4 sections, not by `cmp`. `figma-shopify-pixel-match` is a reserved, unbuilt name — do not create a skill under it. See `docs/adr/0001-design-spec-replaces-pixel-diff.md` for why.

`assets/` remains flat for per-asset exports; assets ship as client-uploaded files rather than inline SVG; verification hardcodes them and proves the revert; each per-asset export is the design's crop, with the uncropped original kept beside it as `original-source-*`. The `## Asset export` sections of the three Figma-driven skills are byte-identical and change together. `shopify-page-replicate` sits outside that set on purpose: it exports nothing from Figma, so its `## Asset capture` sorts the Source page's images into the pile already in the store's Files, which keep their existing reference, and the pile living in the Source theme's own assets, which are downloaded and uploaded to Files. Holding it to a Figma export section would be wrong rather than consistent. `## Asset delivery` and `## Hardcode-then-revert` diverge on purpose across the three, because they have different write surfaces — builder owns a section file, composer only template JSON, restyle only its override stylesheet — and where one cannot reach a destination it declares that rather than downgrading silently.

The two knowledge-doc format specs — `references/theme-capabilities-format.md` and `references/components-format.md` — are byte-identical across the five producer skills: `client-theme-onboarding`, `figma-shopify-builder`, `figma-shopify-composer`, `figma-shopify-globals`, and `shopify-page-replicate`. They change together. The duplication is deliberate.

When editing these skills, keep every path on this convention and the seven skills in agreement.

## Checking the repo's invariants

`scripts/check.sh` asserts this repo's cross-file rules — the two format specs' byte-identity across the five producers, `## Asset export`'s byte-identity across the three Figma-driven skills, every skill's presence in all three registries and every registry entry's resolution to a directory that exists, the absence of the retired pixel-diff vocabulary from the four spec-driven skills and the README, and the presence in each of those four of Phase 4's seven steps in order, `style-reporter`, and the design spec's producer header. The script's own header comment is the authoritative list, and the retired terms are the `BANNED_TERMS` array inside it — extend those rather than restating them here. Run it before committing any change to a shared file — it resolves the repo root itself, so the working directory does not matter:

```sh
./scripts/check.sh
```

It exits 0 when every rule holds, and otherwise names the offending path and exits non-zero.

## Distribution

The repo root is a Claude Code **plugin marketplace** (`.claude-plugin/marketplace.json`). Each top-level bucket is published as its own plugin, `heyitsiveen-skills-<bucket>`, defined **inline** in the marketplace (`strict: false`, so there is no per-bucket `plugin.json`). Empty buckets are listed but stay hidden in `/plugin` Discover until they hold a skill. Install the marketplace, then the buckets you want:

```sh
/plugin marketplace add heyitsiveen/skills
/plugin install heyitsiveen-skills-personal@heyitsiveen
/plugin install heyitsiveen-skills-engineering@heyitsiveen
```

It's also installable via skills.sh: `npx skills add heyitsiveen/skills`.

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/` in this repo. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
