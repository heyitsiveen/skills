# Scanning the NEW theme's design system

Goal: learn the new theme's **dominant** colors, fonts, and component conventions so the
recreation looks native to it. Work top-down — stop once you have a confident token table.

## Source priority

### 1. `config/settings_data.json` → `current` (authoritative — the merchant's *active* values)
Two conventions exist; detect which the theme uses:

**(a) Classic Shopify color schemes.** Look for `current.color_schemes` (keys like
`scheme-1`, `background-1`). Each scheme has `settings` with `background`, `text`,
`button`, `button_label`, `secondary_button`, `shadow`, etc. The scheme used by most
sections (often `scheme-1` / the first) is the dominant palette. Section/template JSON
files reference a scheme via a `color_scheme` setting.

**(b) shadcn/ui-style flat tokens** (modern custom themes). Flat `*_background_color` /
`*_foreground_color` pairs directly under `current`, e.g. `background_color`,
`foreground_color`, `primary_background_color`, `primary_foreground_color`,
`secondary_*`, `accent_*`, `border_color`, `input_color`, `ring_color`,
`add_to_cart_background_color`, `checkout_*`, `star_rating_foreground_color`,
`price_foreground_color`, `muted_foreground_color`, plus `button_border_radius`.

**Typography** lives under `current` too: `body_font`, `heading_font` (Shopify font
handles like `inter_n4`, `assistant_n4`), and `button_font_family` / `button_font_weight`.
Resolve the handle's family (e.g. `inter_n4` → Inter, weight 400).

### 2. `config/settings_schema.json` (fallback for labels/defaults)
If a value is absent from `settings_data.json`, the schema's `default` applies. Also useful
to confirm which font/color settings exist and their human labels.

### 3. `assets/*.css` (CSS custom properties + real usage)
Many themes expose tokens as CSS vars in `:root` / base CSS: `--color-foreground`,
`--color-background`, `--color-primary`, `--font-heading--family`, etc. And the raw
**hex-frequency** across CSS/Liquid reveals what's actually used most.

## Commands (PowerShell + ripgrep)

```powershell
# Active color + font tokens
Get-Content config\settings_data.json | Select-String -Pattern 'color|font|scheme|radius'

# CSS custom properties
rg -n -- '--color|--font|--background|--foreground' assets

# Most-used hex colors across the theme (dominant palette signal)
rg -o -- '#[0-9a-fA-F]{6}' sections blocks assets snippets | rg -o -- '#[0-9a-fA-F]{6}' | Sort-Object | Group-Object | Sort-Object Count -Descending | Select-Object -First 15
```

(On bash/macOS: `rg -o '#[0-9a-fA-F]{6}' sections blocks assets | sort | uniq -c | sort -rn | head -15`.)

## Produce this token table

| Role | New-theme value | Source |
|---|---|---|
| Surface / background | `#......` | settings_data |
| Text / foreground | `#......` | settings_data |
| Primary / brand (buttons, links, CTAs) | `#......` | settings_data |
| Secondary | `#......` | settings_data |
| Border | `#......` | settings_data |
| Star / price accents | `#......` | settings_data |
| Heading font | `Family (weight)` | body/heading_font |
| Body font | `Family (weight)` | body/heading_font |
| Button radius | `..rem` | settings_data |

Then derive the **page palette**: one dominant surface, one text color, one brand/accent
for emphasis. That trio drives the OLD→NEW restyle mapping in the spec doc.

## Worked example — the koora-honey theme

Detected convention: **shadcn-style flat tokens**.

| Role | Value |
|---|---|
| Surface / background | `#FFFFFF` (white) |
| Text / foreground | `#1a1a1a` (near-black) |
| Primary / brand (border, add-to-cart, checkout, CTAs) | `#d4a017` (gold), hover `#e0ac1a` |
| Secondary (text) | `#a67c00` (dark gold) |
| Input / surface tint | `#fdf6e3` (cream) |
| Star rating / price | `#fcc419` / `#ff3b30` |
| Heading & body font | Inter (`inter_n4`) |
| Button radius | `0.5rem` |

Net identity: **white + near-black + gold**, Inter throughout. Installed apps (from
`current.blocks`): Avada SEO, Judge.me, Bundler, Klaviyo, Seal Subscriptions.
