---
name: shopify-inject-app-into-liquid
description: Use when the user wants a third-party Shopify app's widget to RENDER INSIDE a specific theme container — a styled card, a custom section, a designed CTA area — instead of wherever the app drops it by default (e.g., "inject Bundler inside the Bundle block", "the widget renders below the card, I want it inside", "embed the reviews app in my custom section", "route the app block into this div", "can this app even be injected into my Liquid?"). Covers the qualification question first: detects whether the app integrates as an APP BLOCK (fully injectable via {% render block %} routing), an APP EMBED (injectable only via a documented manual mount div), or a legacy SCRIPT-TAG app (usually not injectable), using template JSON / settings_data.json / theme-editor / DOM fingerprints. Then executes the injection: section-schema @app wiring, the two-loop skip-guard + container-render pattern keyed on block.id, deploy, and server- and client-side verification. Distinct from the sibling skill shopify-app-style-override-from-figma, which restyles an app widget IN PLACE with CSS only — this skill moves WHERE the widget renders; combine the two when a design needs both placement and skin.
user-invocable: true
---

# Shopify: Inject an App Widget Into Custom Liquid

Make a third-party app's widget render **inside** a container you own — a styled card, a
custom CTA area, a designed panel — instead of the app's default placement. The proven
reference implementation: the Bundler app's purchase widget routed into the PDP bundle
card's `.pdp-bundle__cta` (koora-honey), while Seal Subscriptions stayed untouched in the
normal product-info flow.

Sibling positioning:

- `shopify-app-style-override-from-figma` — restyles an app widget **in place** (CSS only).
- **This skill** — changes **where** the widget renders (Liquid routing). No app code is
  modified here either: you re-route the app's *block*, never copy or edit its HTML.

When a design needs the widget moved *and* re-skinned, run this skill first, then the
style-override sibling against the new container.

## Phase 0 — Qualify: not every app is injectable (run this gate FIRST)

Shopify apps reach the storefront through three mechanisms. **Which one the app uses
decides whether injection is possible at all** — find out before promising anything.

| Mechanism | Where it lives | Fingerprint | Injectable? |
|---|---|---|---|
| **App block** (theme app extension, `target: section`) | A section's `blocks` in `templates/*.json` | `"type": "shopify://apps/<app>/blocks/<name>/<uuid>"` inside a template; rendered DOM wrapper `<div id="shopify-block-…">`; appears under "Apps" in a section's **Add block** picker | **YES — fully.** Path A below: `{% render block %}` routing. |
| **App embed** (theme app extension, `target: head`/`body`) | `config/settings_data.json` under `current.blocks` | Same `shopify://apps/…` type string but in settings_data, not a template; toggled in Theme settings → **App embeds**; injected before `</head>` or `</body>` (chat bubbles, overlays, pixels) | **Only if** the app documents a manual mount div / shortcode → Path B. Otherwise no. |
| **Script-tag / legacy** | Nowhere in theme files | No `shopify://apps` string anywhere, yet the widget appears; an external `<script>` self-injects DOM next to the product form, with no `shopify-block-` wrapper | **Usually no.** Path B if the app docs offer a manual placement div; otherwise it's fragile JS relocation — escalate to the user, separate scope. |

### The detection sequence

```
1. grep -rn "shopify://apps" templates/
     hit?  → APP BLOCK exists for this app → Path A. Note the section it sits in
             and its block KEY (the JSON key, e.g. "bundle_app").
2. grep -n "shopify://apps" config/settings_data.json
     hit for this app? → APP EMBED. Check the app's admin/docs for a "manual
             placement" / "place this div" / shortcode instruction → Path B or stop.
     (Embeds stay in settings_data.json with "disabled": true after being toggled
      off — presence alone doesn't mean active.)
3. Neither file mentions the app, but the widget renders?
     → script-tag app. Inspect the live DOM: how does the widget mount? If its
       mount node is a div the THEME could own (documented class/data attributes),
       Path B. If the app's JS picks its own anchor → not injectable; escalate.
4. Theme-editor cross-check (catches what grep can't):
     open the target template in the editor → target section → "Add block".
     The app's block listed under "Apps"? → app block exists even if no template
     uses it yet. NOT listed? Either the app ships no app block, or it restricts
     placement via enabled_on (apps may limit their blocks to specific templates
     and section groups — so a block that exists for product pages may be
     unaddable elsewhere). App blocks never render on checkout pages.
```

Two prerequisites for Path A even when the app block exists:

- **The host section must accept app blocks**: its `{% schema %}` `blocks` array must
  include `{ "type": "@app" }`, and the page must use a JSON template. One-line schema
  addition if missing.
- **The app block must be IN the template** with a known key. If it isn't yet: add it once
  via the theme editor (Add block → the app), save, and pull the sync commit — **never
  hand-author the `shopify://apps/…/<uuid>` type string** (the uuid identifies the app's
  extension; let Shopify write it). Then optionally rename the JSON key to something
  stable and readable (e.g. `bundle_app`) before wiring the routing to it.

## Required inputs

Ask the user for any missing input before writing code:

1. **Which app, and which widget instance** — some apps key the widget to a configured
   entity (Bundler: a per-bundle `shortcode`). Confirm which instance must appear.
2. **Target page(s) + container** — which template(s) (`templates/product.json`,
   `product.<variant>.json`, …) and which container (an existing block's markup? a new
   div?). Multi-template stores: the same section renders per-template block sets — wire
   once in the section, enable per template.
3. **Preview URL + theme ID** — for verification.
4. **Deploy path** — GitHub-integration auto-sync on push (and who pushes), or
   `shopify theme push`. This decides the verify-after-deploy loop.

## Path A — App block routing (the primary workflow)

### Phase 1 — Orient (parallel reads)

- `Read` the host section's `.liquid` — find the main block loop (`{% for block in
  section.blocks %}` + `case block.type`), confirm `{ "type": "@app" }` in its schema.
- `Read` the target template JSON — find the app block's key, the host block's key, and
  `block_order` (the app block's order position doesn't matter once routed; it just must
  exist and be enabled).
- `git log --oneline -10` — mirror the repo's commit style.
- Identify EVERY app block in the section (`grep "shopify://apps" <template>`): the skip
  guard must single out the target app and leave the others (e.g. a subscriptions widget)
  in the normal flow.

### Phase 2 — The routing pattern

Two coordinated edits in the host section's Liquid — a skip-guard where app blocks
normally render, and a render inside the container. Generalized from the proven
implementation (`sections/product.liquid`, koora-honey):

```liquid
{%- comment -%} Precompute once, before the main block loop {%- endcomment -%}
{%- liquid
  assign has_host_block = false
  for b in section.blocks
    if b.type == 'HOST_TYPE'
      assign has_host_block = true
    endif
  endfor
-%}

{%- comment -%} 1. In the main loop's app-block case: skip the routed app {%- endcomment -%}
{%- when '@app' -%}
  {%- unless has_host_block and block.id contains 'APP_BLOCK_KEY' -%}
    {% render block %}
  {%- endunless -%}

{%- comment -%} 2. In the host block's case: render it inside the container {%- endcomment -%}
{%- when 'HOST_TYPE' -%}
  <div id="host-{{ block.id }}" class="host" {{ block.shopify_attributes }}>
    {% render 'host-chrome-snippet', block: block %}
    <div class="host__cta">
      {%- for block in section.blocks -%}
        {%- case block.type -%}
          {%- when '@app' -%}
            {%- if block.id contains 'APP_BLOCK_KEY' -%}
              {% render block %}
            {%- endif -%}
        {%- endcase -%}
      {%- endfor -%}
    </div>
  </div>
```

Why each piece is the way it is (each rule below was paid for in real round-trips —
see Hard-won lessons):

- The inner loop variable **must be named `block`** — `{% render %}` only accepts a
  quoted snippet name or the literal variable name `block`; anything else silently
  renders nothing. The inner `block` shadows the outer one only inside the loop body,
  and this nested shape (a block loop inside another block's `when` branch) is proven
  to work.
- Discrimination is by **`block.id`** (which surfaces the template JSON key, e.g.
  `…__bundle_app`) — **never by `block.settings.*`**, which is nil in section scope.
- The skip-guard condition and the container condition must mirror each other exactly,
  so the widget renders **exactly once**: in the container when the host block exists,
  in the normal flow when it doesn't (e.g. templates without the card).
- `has_host_block` keeps every other template (and other app blocks, like a
  subscriptions widget) rendering exactly as before. Smallest possible blast radius.

### Phase 3 — Template JSON

In each target template: the app block entry must be **present, enabled (no
`"disabled": true`), keyed with the name the routing matches**, and listed in
`block_order`. Example shape:

```json
"bundle_app": {
  "type": "shopify://apps/bundler/blocks/custom-bundle/<uuid-shopify-wrote>",
  "settings": { "shortcode": "c0h1" }
}
```

`shopify theme check --fail-level=info` before committing. Match the repo's commit
convention (check `git log` — e.g. koora-honey uses Conventional Commits with no AI
attribution); don't skip hooks.

### Phase 4 — Deploy + verify (server-side, then client-side)

**Server-side** — fetch the preview and assert the app's wrapper sits inside the
container, exactly once, with other app widgets untouched:

```powershell
$html = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 60).Content
[regex]::IsMatch($html, '<div class="host__cta">\s*<div id="shopify-block-[^"]*__APP_BLOCK_KEY"')  # inside?
$html.Contains('<div class="host__cta"></div>')                                                    # empty = block missing/disabled
([regex]::Matches($html, 'shopify-block-[A-Za-z0-9_\-]*__APP_BLOCK_KEY')).Count                    # must be exactly 1
```

Beware: container/mount class names may also appear as selector text inside `{% style %}`
blocks — match the actual `<div>` elements, not CSS.

**Client-side** — many app blocks render only a mount node server-side and populate it
with JS. Probe the live page (browser MCP):

```javascript
const cta = document.querySelector('.host__cta');
const mount = cta && cta.querySelector('.APP-MOUNT-CLASS');   // e.g. .bundler-target-element
JSON.stringify({ ctaFound: !!cta, mountFound: !!mount,
  mountChildren: mount ? mount.children.length : -1 });        // children > 0 ⇒ app JS populated it
```

Allow several seconds — app JS fetches its config async; a spinner at probe time is
normal, re-probe before concluding failure.

**Cache gotchas** (these cost the most false alarms):

- Storefront preview pages are cached; made-up query params do NOT bust the cache. A
  semantic param (`?variant=<id>`) forces a fresh render but each value busts **once** —
  single-variant products burn keys fast. `/collections/<any>/products/<handle>` is an
  independent cache key. A theme update (deploy) invalidates cached pages. The
  **theme-editor preview pane always renders fresh** — the reliable fallback.
- GitHub-synced stores deploy on **push**, not commit, and the import takes ~a minute.
  Verify only after the import lands.

### Phase 5 — Report + merchant guardrails

Summarize, then say these two sentences to the user/merchant explicitly — they prevent
the most common post-ship regression:

1. **Don't hide the app block in the customizer.** It is the SAME block now rendering
   inside the container — the eye icon writes `"disabled": true`, which removes it from
   `section.blocks` entirely, so the container goes empty (it does not "remove a
   duplicate"; pre-fix muscle memory makes merchants do exactly this).
2. **Don't delete and re-add the block.** A re-added block gets a random JSON key, and
   the `block.id contains 'KEY'` routing stops matching. Editing its settings is fine.

## Path B — App embed / script app with a manual mount

When the app integrates as an embed or script tag but documents a manual placement —
"paste this div where you want the widget" — the theme owns the mount and the app's JS
populates it:

1. Get the exact mount markup from the app's admin/docs (a class plus data attributes,
   e.g. `<div class="app-target" data-app-id="…">`). Verify against a working page's
   live DOM if one exists — docs drift.
2. Place that div inside your container in the section/snippet Liquid. If the
   placement is per-instance configurable, expose the id/shortcode as a block or
   section setting and echo it into the data attribute.
3. The embed itself must stay **enabled** (Theme settings → App embeds) — the mount div
   is inert without the app's JS.
4. Verify client-side only (server HTML will show just your empty div): mount found,
   children > 0 after the app JS runs.

If the app offers neither an app block nor a manual mount: **it is not injectable.**
Say so plainly, with the evidence (no `shopify://apps` in templates, not in the Add-block
picker, no manual-placement docs). Options to offer, in order: ask the app vendor for a
placement API/manual install; CSS-reposition the widget where it lands (sibling skill
territory); JS relocation of the app's DOM (fragile, opt-in, separate scope).

## Hard-won lessons (load-bearing — internalize, don't just follow)

### 1. `{% render %}` accepts ONLY a quoted snippet name or the literal variable `block`

`{% render app_block %}` silently renders nothing — no error, no theme-check offense,
just an empty container and a long debugging session. The loop variable must literally
be named `block`. The nested shape (inner `for block in section.blocks` inside another
block's `when` branch, shadowing the outer `block`) is PROVEN to work — if the widget
vanishes, don't re-theorize about nesting; check lesson 3 first.

### 2. App block settings are NOT readable from host-section Liquid

`block.settings.shortcode` is nil in section scope even when the template JSON plainly
carries `"shortcode": "c0h1"` — only the app's own block Liquid sees its settings
(that's what emits the widget's data attributes). This is symmetric: theme app
extensions can't read the parent section's properties either (only `section.id`).
So a settings-based guard CANNOT work. Discriminate by **`block.id`**, which surfaces
the JSON template key. `block.type` for app blocks IS `'@app'` in section scope.

### 3. `"disabled": true` makes a block invisible to ALL Liquid — and humans keep writing it

Hiding a block in the customizer (eye icon) writes `"disabled": true` into the template;
the block then vanishes from `section.blocks` — nothing renders anywhere, no error. The
empty-container signature (`<div class="host__cta"></div>`) means the block is missing
or disabled, NOT that the routing broke. After every deploy, inspect new "Update from
Shopify" sync-back commits for `disabled` flips (`git show <sha> | grep -E
'disabled|APP_KEY'`) **before** touching the Liquid: in the reference project the
merchant hid the "duplicate-looking" widget twice in one night, minutes after each
deploy — the code was never broken. That's why Phase 5's guardrail speech exists.

### 4. The JSON key is the routing contract

The `block.id contains 'APP_BLOCK_KEY'` match rides on the template key staying put.
Keys survive setting edits and reorders, but a deleted-and-re-added block gets a
random key. Use the same key across sibling templates (e.g. `bundle_app` in both the
default and variant product templates) so one section routes all of them.

### 5. Skip-guard and container condition must be exact mirrors

If the guard skips more than the container renders, the widget disappears on some
templates; if it skips less, it renders twice (duplicate DOM ids, double app JS init —
apps rarely survive that). One condition, two places, byte-identical.

### 6. Never hand-author or cross-store-copy the `shopify://apps/…` type string

The uuid belongs to the app's extension as installed. Add the block once via the theme
editor and let Shopify write the type string into the template; take over the JSON from
there. Copying it from another store's repo may reference an extension the target store
doesn't have — the block just won't render.

### 7. Sync-back commits rewrite formatting — extract the semantic diff

Stores on the GitHub integration sync customizer saves back as "Update from Shopify"
commits that reformat the whole file (e.g. re-expanding arrays prettier collapsed),
burying a one-line semantic change in a 150-line diff. Don't eyeball: `git show <sha> |
grep -E '^[+-]' | grep -E 'disabled|shortcode|<APP_KEY>|block_order'`. Expect the
formatter ping-pong (prettier hook collapses, Shopify re-expands) — it's cosmetic.

### 8. The widget may be JS-populated — verify in two layers, patiently

Server HTML proves the ROUTING (wrapper inside container). Only the client probe proves
the WIDGET (app JS found its mount and filled it). A populated-but-spinner state a few
seconds after load is normal; re-probe before declaring failure. Style verification
belongs to the sibling skill.

### 9. `enabled_on` can hide an app block from some templates by the app's choice

Apps may restrict their blocks to specific templates and section groups. If the block
isn't offered in the Add-block picker on YOUR template but exists elsewhere, that's the
app's `enabled_on` — not a theme bug. Placement on a restricted template needs the app
vendor, not Liquid.

### 10. One render-routing per section is cheap; per-template enablement is config

The section-side wiring is template-agnostic (guarded by `has_host_block`). Rolling the
injection out to another template is then pure JSON: add/enable the app block + host
block there. Don't duplicate Liquid per template.

## Anti-patterns

- **`{% render some_var %}` with any name but `block`.** Renders nothing, silently. (Lesson 1.)
- **Guarding on `block.settings.*` from section scope.** Always nil there. (Lesson 2.)
- **Copy-pasting the app's rendered HTML into the theme** instead of rendering its block.
  Freezes one snapshot of the widget: breaks on app updates, loses settings/analytics,
  and usually violates the app's support terms. Route the block; never own its DOM.
- **Hand-authoring the `shopify://apps/…/<uuid>` type string.** (Lesson 6.)
- **"Fixing" the duplicate by hiding the block in the customizer.** That disables it
  everywhere — container included. The skip-guard is the only correct de-duplication.
- **CSS `display: none` on the main-flow instance instead of the skip-guard.** Ships two
  widget DOMs (double JS init, duplicate ids) and hides one. Route, don't mask.
- **Assuming an app embed can be routed.** Embeds inject at `</head>`/`</body>` —
  the theme can't move them; only a documented manual mount (Path B) relocates their UI.
- **Verifying against a cached preview page.** A stale fetch shows the OLD markup and
  manufactures phantom failures. Use a fresh cache key or the editor preview. (Phase 4.)
- **Declaring the Liquid broken when the container is empty.** Check
  `disabled`/presence in the template (and recent sync-back commits) first. (Lesson 3.)

## Quick reference

### Injectability decision tree

```
"shopify://apps/…" in templates/*.json (or app listed in a section's Add-block picker)?
  → YES: APP BLOCK → Path A (fully injectable)
       prerequisites: host section schema has { "type": "@app" }; block present,
       enabled, stable key in each target template
  → NO ↓
"shopify://apps/…" in config/settings_data.json (Theme settings → App embeds)?
  → YES: APP EMBED → app docs offer a manual mount div / shortcode?
       → YES: Path B (theme owns the mount; embed stays enabled)
       → NO: not injectable — escalate (vendor / CSS reposition / opt-in JS relocation)
  → NO ↓
Widget renders anyway (external script self-injects DOM)?
  → script-tag app → same manual-mount question as embeds; default NOT injectable
```

### Verification one-liners

```
inside?   <div class="host__cta">\s*<div id="shopify-block-[^"]*__KEY"
empty?    <div class="host__cta"></div>          ← block missing or disabled, not bad Liquid
count     shopify-block-[A-Za-z0-9_\-]*__KEY     ← must be exactly 1
client    mount.children.length > 0 after app JS settles
```

### Reference implementation

koora-honey `sections/product.liquid` (`when 'bundle'` case + `@app` skip-guard),
templates `product.json` / `product.marri-honey-default.json` (key `bundle_app`,
Bundler shortcode setting), verified live on both PDPs 2026-06-11.

## Out-of-scope (escalate to user before doing)

- **Restyling the widget** — sibling skill `shopify-app-style-override-from-figma`.
- **Relocating embed/script-injected DOM without a documented mount** — MutationObserver
  JS relocation is fragile and needs explicit opt-in; separate effort.
- **Changing what the widget shows** (which bundle, pricing, copy) — that's app-dashboard
  configuration; guide the merchant there instead of fighting it in Liquid.
- **Checkout pages** — app blocks cannot render there at all; don't attempt.
