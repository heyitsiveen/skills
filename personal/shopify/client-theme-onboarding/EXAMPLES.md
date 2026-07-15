# EXAMPLES — recorded facts in → doc fragments out

Real case: Mrs Wordsmith theme (`mrswordsmith/shopify-theme`), scanned 2026-07-09. Top: facts as Steps 1–2 record them. Below: the fragments Step 4 writes from them — nothing in an output that isn't in a fact.

## Input — recorded facts

| # | fact | source |
|---|---|---|
| F1 | `.github/workflows/main.yml:37` runs `npm run deploy -- --group="LIVE"` on push to `master` | scan |
| F2 | dev loop `npm run watch` (`qs theme watch`) live-syncs to theme "GoldenWeb Dev" (id 141927448675) | scan + transcript |
| F3 | `.quickshotignore` excludes `theme/templates/**/*.json` and raster images from sync, both directions | scan |
| F4 | a new `.scss` file compiles only after a watcher restart (entry list read once at startup) | transcript ~9:20 (Curtis) |
| F5 | working branch `feat/goldenweb` | interview |
| F6 | paid extra: `pages/educators-hub` sales page + technical report | ClickUp |
| F7 | `<slider-component>` = `webComponents/SliderComponent.ts`, registered site-wide in `global/global.ts`; markup contract in `sections/scrolling-cards.liquid` | scan |

## Output — AGENTS.md §safety (from F1, F5)

```markdown
## 🚫 Git & deploy safety (non-negotiable)
| action | consequence | rule |
|---|---|---|
| push to `master` | `main.yml` auto-deploys LIVE (mrswordsmith.com) | never push master |
- Work ONLY on `feat/goldenweb`. Commit only when explicitly asked; Angular Conventional Commits (commitlint).
```

## Output — COMMANDS.md rows (from F2, F4)

```markdown
| command | does | when to run | ⚠️ |
|---|---|---|---|
| `npm run watch` | compile `theme/_qs/**` + live-sync to GoldenWeb Dev (141927448675) | dev loop | run `pgrep -fl "qs theme watch"` first — two watchers double-upload |
| `npm run deploy` | deploy a theme group | never locally | CI-only: LIVE/STAGING |

| error | cause | fix |
|---|---|---|
| new `.scss` never compiles | SCSS entry list is read once at watcher startup | restart `npm run watch` |
```

## Output — REVAMP-TODO.md rows (from F3, F6)

```markdown
## Educators hub (💰 paid extra)
- [ ] Build `pages/educators-hub` sales page (lead-gen + product sales) — CU
- [ ] Write the technical report for the page — CU

## Open questions
| question | who answers | blocks |
|---|---|---|
| `templates/*.json` never auto-sync (F3) — who pastes template JSON into the admin at handoff? | agency PM | go-live checklist |
```

## Output — COMPONENTS.md rows (from F7 + scan)

```markdown
## Custom web components
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| `<slider-component>` | `theme/_qs/js/src/webComponents/SliderComponent.ts` · registered in `global/global.ts` · markup: `sections/scrolling-cards.liquid` | scroll track + dots/arrows/autoplay, available on every page | carousel, slider, slideshow, scroll |

## Functions
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| `svg-wave-top` / `svg-wave-bottom` | `theme/snippets/svg-wave-*.liquid` | wave section separators, take `fill:` | wave, separator, curve, divider |

## Flows
| name | file path(s) | what it does | reuse keywords |
|---|---|---|---|
| add-to-cart | `.ajax_cart` handler in `global/global.ts` → `fetch('/cart.js')`, dispatches `updatecart` | AJAX add-to-cart from any product form | add to cart, ATC, cart ajax |
```

## ❌ → ✅ — the rewrite this skill exists for

❌ Human tutorial (banned shape):
> To get started with development, simply run the watch command and QuickShot will take care of compiling your SCSS and TypeScript for you!

✅ Agent doc (contract shape):
> `npm run watch` → compiles `theme/_qs/**` → uploads to GoldenWeb Dev (141927448675). First: `pgrep -fl "qs theme watch"` — empty output = safe to start.
