# Claude Code Skills

[![skills.sh](https://skills.sh/b/heyitsiveen/skills)](https://skills.sh/heyitsiveen/skills)

Agent Skills for Claude Code — mostly **Shopify** theme & app-integration workflows built from **Figma** designs, plus a clean git-commit helper. Packaged as Claude Code plugins (one per bucket) and installable via [skills.sh](https://skills.sh).

## Install

### As a Claude Code plugin

Add the marketplace, then install whichever bucket-plugins you want:

```sh
/plugin marketplace add heyitsiveen/skills
/plugin install heyitsiveen-skills-personal@heyitsiveen       # Shopify + Figma skills
/plugin install heyitsiveen-skills-engineering@heyitsiveen    # git commit helper
```

The `in-progress`, `misc`, and `productivity` buckets are published too, but stay hidden in Discover until they contain a skill.

### Via skills.sh (Claude Code, Cursor, Copilot, and more)

```sh
npx skills add heyitsiveen/skills
```

Install a single skill with `npx skills add heyitsiveen/skills --skill=<name>`.

## Reference

These split on who invokes them. **User-invoked** skills are run on demand — a slash command like `/gc`, or a skill built to be triggered directly (marked `user-invocable: true`), usually with a structured prompt. **Model-invoked** skills are ones the agent reaches for automatically when the task matches their description.

### Shopify

Pixel-accurate theme building, app-widget styling & injection, and template content operations — most driven by Figma designs.

**User-invoked**

- **[shopify-add-section-or-preset-from-figma](./personal/shopify/shopify-add-section-or-preset-from-figma/SKILL.md)** — Add a section to a JSON template, or append a preset to a section's schema, from a Figma design — composed only from the theme's existing sections and blocks (no new `.liquid`).
- **[shopify-copy-template-content](./personal/shopify/shopify-copy-template-content/SKILL.md)** — Copy sections or blocks from one template JSON into others at a chosen position, keeping the JSON valid and the source untouched.
- **[shopify-inject-app-into-liquid](./personal/shopify/shopify-inject-app-into-liquid/SKILL.md)** — Make a third-party app's widget render inside a container you own, instead of wherever the app drops it by default.

**Model-invoked**

- **[figma-shopify-builder](./personal/shopify/figma-shopify-builder/SKILL.md)** — Build pixel-accurate theme sections or blocks from Figma — every value traced to the design, never invented.
- **[rebuy-widget-customization](./personal/shopify/rebuy-widget-customization/SKILL.md)** — Replace a Rebuy widget's markup with custom Vue 2 templates while Rebuy's engine, discounts, and subscriptions keep running underneath.
- **[shopify-app-restyle](./personal/shopify/shopify-app-restyle/SKILL.md)** — Restyle a third-party app's widget to match a Figma design using `!important`-scoped theme CSS overrides, proven pixel-accurate against the Figma frames.
- **[shopify-migrate-page-to-new-theme](./personal/shopify/shopify-migrate-page-to-new-theme/SKILL.md)** — Audit a page on an old theme and produce a spec doc + handoff prompt to recreate it on a new theme — content verbatim, restyled to the new theme's design system.
- **[shopify-update-content-from-figma](./personal/shopify/shopify-update-content-from-figma/SKILL.md)** — Replace the text/copy (and matching icons) of existing section instances in a template to match Figma frames — values only, no restructuring.

### Engineering

General dev tools, not Shopify-specific.

**User-invoked**

- **[gc](./engineering/global/gc/SKILL.md)** — Create one clean Conventional Commits-style commit from your current changes, with no AI attribution.

## Repo layout

Skills are organised as `<bucket>/<domain>/<skill>/`, where the domain is `global` (domain-agnostic) or a specific one like `shopify` or `nextjs`.

```
.                                 # git repo root (marketplace + plugin live here)
├── README.md                     # this file — the skill catalogue
├── skills.sh.json                # grouping config for skills.sh
├── CLAUDE.md                     # repo conventions
├── .claude-plugin/
│   └── marketplace.json          # marketplace manifest — one plugin per bucket
├── engineering/
│   └── global/gc/                # git commit helper             (published)
├── personal/
│   └── shopify/                  # 8 Shopify theme & app skills  (published)
├── productivity/                 # empty — for future skills
├── misc/                         # empty — for future skills
├── in-progress/                  # empty — for future drafts
└── deprecated/
    └── shopify/                  # retired skills                (not published)
```

See [`CLAUDE.md`](./CLAUDE.md) for the conventions (bucket/domain rules, the three registries to keep in sync, and invocation types).

## Credits

Structure and workflow inspired by [mattpocock/skills](https://github.com/mattpocock/skills).
