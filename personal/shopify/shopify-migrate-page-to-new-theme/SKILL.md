---
name: shopify-migrate-page-to-new-theme
description: >-
  Audit an EXISTING Shopify page/template from an OLD theme and produce TWO deliverables — a
  comprehensive markdown spec doc AND a copy-paste handoff prompt for a fresh Claude Code
  session running inside the NEW theme — so that page can be recreated on the new theme with
  its content kept VERBATIM but RESTYLED to the new theme's own design system. It scans the
  new theme/codebase (config/settings_data.json, CSS tokens, fonts) to learn the new theme's
  dominant colors and fonts and adopts THOSE for the recreation — never copying the old
  theme's colors or fonts. Use whenever the user wants to migrate, recreate, rebuild, port,
  re-theme, or "redo" an existing Shopify page, collection, or product template onto a
  different/new Shopify theme or codebase — for example they point at an old-theme template
  JSON plus a new-theme folder, or say "audit this page", "document this template for
  migration", "recreate this page on the new theme", or "give me a prompt to rebuild this
  page on the new theme". Trigger even if they omit the word "audit". Do NOT use it for:
  building or syncing a section/page from a Figma design (use the Figma skills); copying
  sections or blocks between templates within the SAME theme; restyling a third-party app
  widget; editing global theme color/font settings; whole-store or Liquid-to-Hydrogen /
  headless migrations; SEO or performance audits; or designing a brand-new page that has no
  existing source. Shopify themes only.
---

# Migrate a Shopify Page to a New Theme

## What this skill produces

Two artifacts, both saved into the **new theme's `docs/` folder**:

1. **A spec doc** (`docs/<handle>-page.md`) — the page's content and structure captured
   verbatim from the old theme + live site, plus the new theme's design tokens and an
   explicit OLD→NEW restyle mapping.
2. **A handoff prompt** — a self-contained block the user pastes into a *new* Claude Code
   session running **inside the new theme**, instructing it to rebuild the page with the
   new theme's design system. (This skill does NOT build the page itself; it prepares the
   recreation.)

Also save desktop + mobile reference screenshots of the live page next to the doc.

## Core principle: two sources of truth

The whole point of this skill is an **inversion** that a naïve copy-paste gets wrong:

| Aspect | Source of truth | Rule |
|---|---|---|
| **Content & structure** (copy, sections, order, layout intent) | the **OLD** theme (template JSON + live page) | reproduce **verbatim — no revisions**, including typos |
| **Visual style** (colors, fonts, buttons, spacing, radii) | the **NEW** theme (its design tokens) | **adopt the new theme's system** — do NOT carry over the old theme's colors/fonts |

Why: recreating a page should make it look **native to the new theme**, not transplant the
old theme's skin. A maroon/cream/serif page dropped unchanged into a white/gold/Inter theme
looks broken. Keep what the page *says and does*; re-skin *how it looks* to the new theme.

## Inputs to gather (ask only if not obvious from context)

- **Old template JSON** — path or template name (e.g. `templates/page.X.json`). Content source.
- **Live page URL** — to capture rendered UI + theme quirks the JSON omits. If unknown,
  derive it from the live store's `/sitemap.xml` (see Step 2).
- **New theme path** — the destination theme folder. Style source + where the docs go.

## Workflow

### Step 1 — Read the old template JSON
Parse the `sections` map and the `order` array. For each section record: `type`, `blocks`,
key `settings`, and the **`disabled`** flag. The `order` array is render sequence; disabled
sections are present but hidden.

### Step 2 — Capture the live page
Open the live URL in a browser (e.g. the `chrome-helium` or `chrome-devtools` MCP — if one
reports no Chrome executable, try the other). Then:
- **Find the URL if unknown:** fetch `/sitemap.xml`, follow the `sitemap_pages_*` /
  `sitemap_collections_*` child, and match the page. Note: a page's **handle often differs
  from its template suffix** (e.g. template `page.30-days-of-wellness.json` → live handle
  `30-days-wellness-plan`). Append `?pb=0` to suppress any page-builder bar.
- **Scroll to the bottom** (to trigger lazy-loaded images/videos), then capture.
- **Extract per-section**, ideally via one `evaluate_script` saved to a temp file: rendered
  text, computed styles (font-family, font-size, color, background of the heading's
  effective ancestor), image/video `src`, and form/app presence.
- **Screenshot** full-page desktop (~1440px) and mobile. Read them to ground your
  description. (Desktop Chrome enforces a ~494px min width; that's still below the mobile
  breakpoint, so it's fine for capturing mobile layout.)

Why the live capture matters: the JSON omits **app-rendered content** (review counts,
prices, bundle/form copy) and **theme-default visual quirks** that aren't in the settings
(e.g. a panel that renders on a black background even though `background_color` is
transparent). Capture these from computed styles, not assumptions.

### Step 3 — Scan the NEW theme's design system  ← the key step
Determine the new theme's dominant colors, fonts, and component conventions. Read
`references/scan-new-theme-design.md` for the exact files, both token conventions
(classic Shopify `color_schemes` vs. shadcn-style flat keys), and ready-to-run commands.
Produce a compact **token table**: surface/background, text/foreground, primary-brand
accent (buttons/links/CTAs), secondary, borders, star/price accents, heading font, body
font, button radius.

### Step 4 — Write the spec doc
Use `references/spec-doc-template.md`. Reproduce all content **verbatim**. Add two style
sections: (a) the **new theme's design tokens** (from Step 3), and (b) an **OLD→NEW restyle
mapping** that pairs each old color/font with its new-theme replacement, so the recreation
has zero ambiguity about what to use.

### Step 5 — Generate the handoff prompt
Use `references/handoff-prompt-template.md`. It must tell the new session to: read the spec
doc, **recreate with the new theme's design system (not the old colors/fonts)**, keep
content verbatim, prefer reusing the new theme's existing sections, embed the same apps, and
**check the section + restyle mapping with the user before building**.

### Step 6 — Save & present
Save the doc + screenshots into the new theme's `docs/`. Present the handoff prompt to the
user in a copy-paste code block, and briefly explain the OLD→NEW restyle decisions.

## Fidelity checklist — things that generalize across pages

- **Template kind:** page / collection / product. The default `main-*` section is often
  **disabled** (page is fully section-built); note it.
- **Disabled sections:** reproduce as disabled for a true 1:1 — BUT many themes leave
  **demo/placeholder cruft** disabled (lorem ipsum, unrelated demo content). Flag those for
  **omission** and confirm with the user rather than carrying junk over.
- **App-owned content:** Judge.me, Bundler, Klaviyo, Seal Subscriptions, etc. render their
  own markup/copy. Embed the **same app block**; do NOT rebuild their text in Liquid.
  Verify the app is installed in the new theme (check `config/settings_data.json` →
  `current.blocks`).
- **Stale hardcoded IDs:** custom CSS/Liquid scoped to `#shopify-section-template--<id>__...`
  will not match a new render. Re-point to the new ID or use a class-based selector.
- **Heading conventions:** some themes treat `[bracketed]` heading text as the highlighted
  span (renders without brackets). Note the convention; don't print literal brackets.
- **Verbatim means verbatim:** keep typos, em-dashes, leading spaces, casing.

## Restyling rule of thumb (Step 4/5 detail)

Map by **role**, not by hex value: old *page background* → new *surface/background*; old
*heading color* → new *foreground* (use the new *primary/accent* for emphasis like
underlines); old *buttons/links/highlights* → new *primary-brand* color; old fonts → new
heading/body fonts. If the old page used a dark panel, re-skin it using the new theme's own
dark scheme or surface conventions rather than a raw old hex. Images that are part of the
content (infographics, product shots) are content — reuse them as-is.

**Worked example (illustrative):** Old theme = cream `#f3ede1` bg, maroon `#530000`
headings, gold `#dbaf66`, PT Serif + Lato. New theme tokens = white `#FFFFFF` surface,
near-black `#1a1a1a` text, gold `#d4a017` primary/CTA, Inter for both heading & body.
Restyle: cream→white, maroon headings→`#1a1a1a` (with `#d4a017` underline/accent),
`#dbaf66`→`#d4a017`, PT Serif/Lato→Inter. Content unchanged.

## Reference files
- `references/scan-new-theme-design.md` — how to extract the new theme's tokens (read in Step 3).
- `references/spec-doc-template.md` — the spec doc structure (use in Step 4).
- `references/handoff-prompt-template.md` — the handoff prompt structure (use in Step 5).
