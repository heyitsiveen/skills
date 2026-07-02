# Spec doc template

Fill this in for the page being migrated. Reproduce all page copy **verbatim**. Save as
`<new-theme>/docs/<handle>-page.md` (or `-landing-page.md`). Keep the `[ ]`-style notes as
real content; delete the parenthetical guidance.

```markdown
# Page Spec — "<Page title>"

> Faithful reference for recreating this page on the NEW theme
> (`<new-theme-path>`). **Content is reproduced verbatim — no revisions.** Visual style is
> RESTYLED to the new theme's design system (see §2/§3), NOT copied from the old theme.

| Field | Value |
|---|---|
| Live URL | <url> |
| Page type | Page / Collection / Product |
| Live handle | <handle> |
| Template suffix | <suffix>  (note if it differs from the handle) |
| Source template file | templates/<file>.json |
| Browser <title> | <title> |
| Live runtime section prefix | template--<id>__ |
| Reference screenshots | ./<handle>-desktop-full.jpeg, ./<handle>-mobile-full.jpeg |

## 1. What this page is
(1–3 sentences: the page's job, and the at-a-glance section flow.)

## 2. NEW theme design tokens (style source of truth)
(The token table from references/scan-new-theme-design.md — surface, text, primary/brand,
secondary, borders, accents, heading font, body font, button radius.)

## 3. OLD → NEW restyle mapping
(Pair every old visual token with its new-theme replacement, mapped by ROLE not hex.)

| Element | OLD theme | NEW theme (use this) |
|---|---|---|
| Page background | <old> | <new surface> |
| Body text | <old> | <new foreground> |
| Headings | <old> | <new foreground> (+ <new accent> for highlight) |
| Buttons / links / highlights | <old> | <new primary/brand> |
| Heading font | <old> | <new heading font> |
| Body font | <old> | <new body font> |
| (Dark panels, if any) | <old hex> | <new dark scheme / surface convention> |

> Content images (infographics, product shots) are CONTENT — reuse as-is; do not restyle.

## 4. Section render order (quick reference)
| # | Section key | type | State | Purpose / heading |
|---|---|---|---|---|
(One row per entry in the `order` array. Mark ✅ enabled / ⛔ disabled.)

## 5. Section-by-section breakdown (verbatim content)
(For each ENABLED section: heading(s), body copy verbatim, images by handle, layout/
alignment, and any theme-default visual quirk observed live — e.g. "renders on black bg".)

## 6. Disabled sections
(Reproduce as disabled for 1:1. FLAG any theme-demo/placeholder cruft to omit — confirm
with user.)

## 7. Image & media asset inventory
| Used in | Theme handle (shopify://) | Live CDN URL |
|---|---|---|

## 8. Apps & dynamic content
(Each app block + what it renders. Note its content lives in the APP, not the theme.
List apps required for parity.)

## 9. Recreation notes & checklist
- Prerequisites (collection/product/page exists with matching handle; apps installed; images re-uploaded)
- Fidelity reminders (verbatim copy; disabled sections; bracket=highlight; etc.)
- **Restyle reminder: apply §3 — use NEW theme colors/fonts, not the old ones.**
- Decisions to confirm with the user.

## 10. New-theme section inventory & preliminary mapping
(List the new theme's sections/blocks. Map each old section type → candidate new-theme
section (reuse) or "build". Mappings are by-name hypotheses — confirm via each section's
{% schema %} before building.)
```
