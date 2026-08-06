# Handoff prompt template

Fill the `<...>` placeholders and give the result to the user as a copy-paste code block.
It is pasted into a **new Claude Code session running inside the NEW theme**, so it must be
fully self-contained (that session has no memory of the audit).

```
Recreate the existing <PAGE NAME> on THIS theme. It's already documented in this repo — read the docs before doing anything.

READ FIRST (in this repo):
- docs/<handle>-page.md — the complete spec: render order, all verbatim copy, the NEW-theme design tokens (§2), the OLD→NEW restyle mapping (§3), images, disabled sections, app dependencies, recreation checklist (§9), and the new-theme section mapping (§10).
- docs/<handle>-desktop-full.jpeg and docs/<handle>-mobile-full.jpeg — reference screenshots of the OLD page (use for LAYOUT/CONTENT reference only — NOT for colors/fonts).

AUTHORITATIVE SOURCES (cross-check content):
- Original template JSON (old theme): <old-theme-path>\templates\<file>.json
- Live old page: <live-url>

STYLE — THE KEY RULE:
- Restyle to THIS theme's own design system. Do NOT copy the old theme's colors or fonts. Use the tokens in §2 and the OLD→NEW mapping in §3:
  - Surface/background: <new bg>   • Text: <new fg>   • Primary/brand (buttons, links, highlights): <new accent>
  - Heading font: <new heading font>   • Body font: <new body font>   • Button radius: <radius>
- The screenshots show the OLD maroon/cream/serif look — that is the CONTENT/LAYOUT reference only. The recreation must look native to THIS theme.

CONTENT — VERBATIM:
- Reproduce all copy exactly as in the spec (including any typos, em-dashes, leading spaces, casing). No rewrites.
- This is a <PAGE/COLLECTION/PRODUCT>. Live handle is `<handle>`; assign template suffix `<suffix>` (note: handle ≠ suffix if applicable). <collection/product handle requirements, if any>.

VISIBLE SECTIONS (in order): <list>.

WATCH FOR (from the live audit):
- <page-specific gotchas: app-owned content (which apps), theme-default visual quirks, bracket=highlight headings, stale hardcoded section-IDs in custom CSS, etc.>
- Disabled sections: <which to reproduce-as-disabled vs which are demo cruft to omit — ASK before dropping>.

ABOUT THIS THEME:
- Custom theme with its own section vocabulary. Prefer REUSING its existing sections (see §10 mapping); build new ones only when there's genuinely no fit. Confirm each candidate section's {% schema %} can hold the content before using it.
- Apps needed for parity: <Judge.me / Bundler / Klaviyo / Seal / ...> — embed the same app blocks; don't rebuild their copy in Liquid.

WORKFLOW:
1. Read the spec doc + screenshots; inspect any existing template for this page; read the {% schema %} of the candidate sections in §10.
2. Produce a confirmed section-by-section mapping (reuse vs build) AND restate the §3 restyle plan, and check both with me BEFORE building.
3. Build the template JSON (and any missing sections/blocks) using THIS theme's tokens, then verify against the live page (content/layout) and the screenshots — colors/fonts should match THIS theme, not the old one.
```
