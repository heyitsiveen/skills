---
name: figma-shopify-globals
description: Sync a full-site Figma file's observed colours and existing typography, radius, page-width, breakpoint, and derived interaction-state globals into a draft Shopify theme. Use when the user supplies one Figma file plus a draft theme for a full-site token sync, a pre-build global audit, correction of known theme-wide drift, or an observed design purpose that needs a new global and purpose-qualified consumer rewiring.
---

# Figma → Shopify Globals

Sync a full-site Figma design's observed globals into a draft theme's existing global settings, then derive approved interaction states the design does not draw. When a uniform observed purpose has no global, use the gated [add-setting-and-rewire branch](references/add-setting-and-rewire.md) to propose one and qualify consumers by purpose. Observed design evidence supplies base values; the theme's setting names, token names, ramp positions, and current values are not evidence. Four phases run in order: **research** (read-only on the theme), **plan** (stop for approval), **implement**, **verify**.

This tracer bullet covers colour globals, existing typography globals for font family and line-height, radius, page width/padding, breakpoint counterparts earned by two observed viewport values, interaction-state values derived from approved base colours, and individually approved missing globals with purpose-qualified consumers. It never adds a typography global, syncs font sizes, rewrites setting types, repairs raw per-instance values, or invents an unrelated global. The run stands alone.

## Inputs

Collect these before Phase 1:

1. **One Figma file link** — the file URL is the input. The run inventories every page and component frame through the file link.
2. **A draft client theme** — a local theme repo plus the connected draft theme, or the exact draft-theme identity if the repo's `shopify.theme.toml` supplies it.
3. **Approval contact** — the person who can approve the complete observed-binding table and each hand-tuned value. Ask only for missing inputs.

The run proceeds only after the theme role is proven to be draft. A preview URL or a branch name alone does not prove that; resolve the connected theme's role with the Shopify tooling. If the target is live, stop with the theme identity and the evidence that made it live.

## Shared knowledge docs

The run reads `.agent/THEME-CAPABILITIES.md` and `.agent/COMPONENTS.md` before relying on theme knowledge. Each doc is a cache verified against the theme, and both are this skill's output when absent or stale. Their exact shapes live in [`references/theme-capabilities-format.md`](references/theme-capabilities-format.md) and [`references/components-format.md`](references/components-format.md); read the relevant spec in full before a scanner writes a byte.

The two spec files are deliberately duplicated byte-identical across the producer skills because plugin packages ship skill folders, not a shared file outside a skill. Keep this skill's copies in agreement with the other producers in the same commit.

### Version ladder

For each existing doc, compare its `format:` with the version in the relevant spec:

- Absent or lower → run a full scan.
- Equal and fresh (`scanned:` counts, file lists, and `git:` match) → read it as fresh.
- Equal and changed → run an incremental refresh for the changed entries.
- Higher → read it as-is, leave every byte, and report the higher version as **read-as-newer**.

The user's refresh phrase wins: `refresh theme capabilities` regenerates the catalog; `refresh components` regenerates the reuse inventory. After every scan, merge, or refresh, run the spec's completeness gate. A shortfall dispatches only the deficient section or category, then the gate runs again. A shortfall that remains after the second dispatch is named with expected count, actual count, and missing names.

### Scanner topology

Dispatch only the scanners whose doc is absent or stale. Every dispatched prompt carries the client-repo path, the scan mode, the file scope, the absolute spec path, and the instruction to read that spec in full and reproduce its block.

| scanner | reads | writes |
|---|---|---|
| capability catalog | `config/settings_schema.json`, every `.liquid` file in `sections/` and `blocks/`, section-group JSON for §Conventions, `templates/**/*.json`, the layout, CSS-variable snippet, stylesheets, and sections reading metafields/metaobjects | `.agent/THEME-CAPABILITIES.md`, or `THEME-CAPABILITIES-<n>.md` in the run directory when sharded |
| reuse inventory — JavaScript | the JavaScript source tree | `COMPONENTS-<n>.md` in the run directory, merged into `.agent/COMPONENTS.md` |
| reuse inventory — Liquid/CSS | every Liquid file in `sections/`, `blocks/`, `snippets/`, `layout/`, and `templates/`, plus every stylesheet and inline script/style | `COMPONENTS-<n>.md` in the run directory, merged into `.agent/COMPONENTS.md` |

The two reuse scanners stand or dispatch together in FULL mode. In INCREMENTAL mode, a side with no changed entries stands down and its rows and counts are carried into the merge. Above 400 `.liquid` files across `sections/` and `blocks/`, shard each standing scanner by contiguous sorted file ranges into the run directory and gate the merged doc.

## Add-setting-and-rewire branch

When the observed-binding pass finds a uniform design purpose with no existing global, or a new global needs existing consumers pointed at it, read [`references/add-setting-and-rewire.md`](references/add-setting-and-rewire.md) in full before continuing. The reference is canonical for this branch's proposal, ownership, approval, emission, rewiring, regression, and cleanup gates. Its report-only status applies to branch edits; ordinary existing-global writes remain under their own approval.

## Phase 1 — Research (read-only on the theme)

Phase 1 makes no theme-setting write. Its deliberate writes are the absent-or-stale knowledge docs and the run artifacts under `.agent/figma-shopify-globals/`; `.agent/` is added to `.git/info/exclude` before those writes if needed.

### 1a. Inventory the Figma file before deep reading

Use the Figma MCP against the single file link. Inventory every page and every frame in the file. Record one row per frame in `.agent/figma-shopify-globals/figma-inventory.md`:

| frame | page | kind | duplicate/orphan evidence | canonical status |
|---|---|---|---|---|
| `<frame name>` (`<node-id>`) | `<page>` | page · component · duplicate · orphan | `<evidence>` | canonical · user choice · excluded |

Classify frames as follows:

- **page** — a frame representing a routable storefront surface or full page composition;
- **component** — a reusable component frame, including its states when the file declares them;
- **duplicate** — same-name or same-purpose frame with another candidate, even when the pixels differ;
- **orphan** — a frame with no page/component relationship or no reachable use in the file's component set.

Before reading variables, styles, reference captures, or node contents deeply, surface every ambiguous duplicate to the user with the candidate names, node ids, pages, and the evidence that made it ambiguous. Wait for the canonical choice. A duplicate that the user excludes stays in the inventory with its reason; a clear duplicate is recorded and not double-counted.

### 1b. Read declared design data directly

After duplicate choices, read the file's declared colour variables, variable modes, collections, paint styles, text styles, layout variables, and font specifications directly through the Figma MCP. Record the resolved value, mode, alias chain, and declaration node. Resolve every text style to its actual font family, weight, size, and line-height from the font specification; a style name is never evidence for any of those values. Weight and size are recorded to resolve the existing font setting; font size is never a sync target.

Flag variables whose normalized names differ only by a separator (`primary-color` vs `primary_color`, for example). Keep both candidates separate until the user resolves them; do not merge them.

Record which interaction states the file declares. A missing hover, focus, active, or disabled state is a **derived-value** candidate, not observed evidence; never present a derived value as designer-specified.

### 1c. Recover values that are not declared

For every colour-, typography-, radius-, or page-width-bearing element in every selected page/component frame:

1. Read the element's actual paint, opacity, blend mode, stroke, fill, text, effect, font, line-height, corner-radius, frame-width, and layout-padding values from its node data.
2. If the value is not declared as a variable or style, measure it from the node or an exact-scale reference capture and record the measurement method.
3. Record the category, element name, node id, page, frame, property, resolved value, viewport/state, and source kind (`variable`, `style`, `node`, or `measurement`).

The evidence table uses this shape and is retained in the observed-binding artifact:

| category | frame | element | node id | property/viewport/state | observed value | source | declaration or measurement |
|---|---|---|---|---|---|---|---|
| colour · typography · radius · page width/padding | `<frame>` | `<element>` | `<node-id>` | fill · desktop · default | `<value>` | variable · style · node · measurement | `<collection/name>` or `<method>` |

Choose values from observed element evidence. A token's name, its position in a ramp, its numeric suffix, or its proximity to another token never supplies a value.

### 1d. Inventory the theme's existing globals

Read the theme schema, settings data, consumers, and live knowledge docs. Build the candidate list from existing `color`, `color_scheme_group`, typography, radius, page-width/padding, and breakpoint settings that the theme actually emits. For typography, only existing font-family/font-picker and line-height settings are sync candidates. Inventory existing font-size settings for exclusion; never add a standalone typography setting. For each candidate, record:

- schema group, setting id, type, declared options/range, and declared default;
- current value from `config/settings_data.json`'s `current` object;
- the variable or Liquid assignment that carries it;
- the rendered property and surface it paints;
- the option's actual rendered value, when the setting is an option or constrained range;
- its existing breakpoint counterpart, if any, and the viewports it serves;
- the base setting, foreground, and consumer for each hover/focus/active/disabled surface;
- whether an interaction-specific setting or variable already exists, and whether the consumer can retain a live reference to its base;
- every section/block inheritance row that resolves to it or shadows it with a raw value;
- whether the current value differs from the declared default (**hand-tuned value**);
- evidence paths and line numbers.

`THEME-CAPABILITIES.md`'s `§Globals` is a lead, not proof: verify each row against `settings_schema.json`, `settings_data.json`, the real consumer, and an option's rendered output before declaring a representability gap. Read the current value live; the catalog's default is a different fact.

### 1e. Build observed bindings

For every existing global in scope, compare its real consumer surface with the evidence table. Create one candidate row per setting, even when the result is undetermined or non-uniform:

| category | setting id | paints | design evidence | values across selected frames/viewports | uniformity | representability | current → proposed | breakpoint decision | status |
|---|---|---|---|---|---|---|---|---|---|
| colour · typography · radius · page width/padding | `<id>` | `<property + surface>` | `<element + frame + node>` | `<values>` | uniform · non-uniform · unexercised | exact · named option · genuine gap | `<current> → <value or —>` | `<pair or No breakpoint-specific global needed>` | write · report · undetermined |

Apply these decisions mechanically:

- A **uniform value** is agreed by the whole selected design for the same global purpose. It is eligible for a write. This applies to colours, radius, page width/padding, and existing typography family or line-height.
- A **non-uniform value** belongs to the section or component that deviates. Report every observed value and leave the global unchanged.
- An **unexercised setting** has no selected design evidence. List it as undetermined and keep its current value.
- A **hand-tuned value** gets its own approval line showing current, declared default, proposed value, and the observed evidence. It is not swept into a batch approval.
- An **existing typography global** may update only for font family/font-picker or line-height, and only where the whole design agrees. Never add a typography global. Font sizes are owned by text blocks and are never synced; deviations go to composer or builder. A resolved weight may affect an existing font-picker value only when that setting already supports it; never add a standalone weight global. Record weight, size, and line-height from the font specification, never from a style name.
- A **representability check** traces what each existing option actually renders before declaring a gap. A named option may already be the design's value. If no option carries it, report the nearest option and that option's real rendered value; leave the setting value and type unchanged unless the directly observed design value is already carried by that option.
- A **breakpoint pair** is earned only when the design shows two values for one token at two viewports. Show both values, their evidence, the counterpart setting, and the approval state. For typography, update an existing counterpart only; never create a typography global. A typography difference with no existing counterpart belongs to the text block. When the values are the same or only one viewport is evidenced, report **No breakpoint-specific global needed** as a pass; do not create a counterpart.
- A setting's type is never rewritten. A new breakpoint counterpart, when approved, uses its own declared type and is not a type conversion of the base setting.

Record a separate `separator-collision` warning for every near-identical variable name. The warning remains even when one candidate is later chosen.

### 1f. Research the add-setting-and-rewire branch

When this branch is eligible, read its reference and retain the tables it specifies under `.agent/figma-shopify-globals/`. The branch is complete only when its linked completion criterion passes.

### 1g. Derive missing interaction states

Derive only from an approved, uniform base binding when the design does not provide the interaction state. Treat each candidate as a separate row in the retained artifact:

| state | base setting | foreground | base value | formula | derived value | contrast | status | reason left |
|---|---|---|---|---|---|---|---|---|
| hover · focus · active · disabled | `<id>` | `<id or —>` | `<resolved colour>` | `L ± 0.08` | `<resolved colour or —>` | `<ratio / threshold>` | derived or left | `<reason when left>` |

Apply the same algorithm every time:

1. Resolve the approved base colour to HSL and read its own lightness `L`. Use the fixed step `ΔL = 0.08`: when `L ≤ 0.50`, add the step (lighten); when `L > 0.50`, subtract it (darken); clamp the result to `[0, 1]`. The direction comes from the base colour itself, so a dark base lightens instead of darkening invisibly.
2. Never choose a ramp neighbour, numeric suffix, or nearby token. The base setting is the only source for the derived value.
3. If an interaction-specific setting already exists, show the existing setting and the computed base → derived result for approval. If no setting exists, add a custom property in the theme's existing global-variable layer with a live base reference, using the equivalent of `hsl(from var(--<base>) h s calc(l + 8%))` for lightening or `hsl(from var(--<base>) h s calc(l - 8%))` for darkening. Clamp the resulting lightness to `[0%, 100%]`. Preserve the theme's naming and variable conventions. Never write a hardcoded derived colour where a base reference is required.
4. Resolve the foreground painted by that same consumer and check the derived colour against it with the WCAG 2 relative-luminance contrast ratio: `4.5:1` for normal text, `3:1` for large text or non-text controls. Record the foreground source, ratio, threshold, and pass/fail. If the foreground is ambiguous, the ratio fails, or the base is not an approved uniform binding, leave the candidate and name the reason.
5. Label every successful computed value `derived`, show `base → derived` in the plan, and keep observed and derived evidence distinct. Label every rejected or unresolved candidate `left` with its reason. Count every candidate exactly once as `derived` or `left`; report both totals even when one is zero.

#### Interaction derivation completion criterion

The interaction-state pass is complete only when every missing state has one row, every row names its base, formula, foreground, contrast result, and derived/left status, every approved missing-setting path references the base variable, and the derived plus left totals equal the candidate count.

### 1h. Check the reference-theme discriminant

Run the candidate inventory against the reference theme when that fixture is in scope. The report must surface all seven settings still carrying the base theme's factory colour, including the primary hover. Name every setting, its factory default, its current value, the design evidence status, and the proposed action. When the connected draft is not that fixture, record `reference-theme discriminant: not this fixture` and run the same complete factory-colour audit against the connected theme; a run that silently omits the seven-setting check has failed the research gate.

### 1i. Research completion criterion

Phase 1 is complete only when the artifact tree contains the frame inventory, declared-variable/style record, resolved font-spec record, observed-evidence table, existing-global inventory, observed-binding candidates, any add-setting branch artifacts required by its reference, breakpoint decisions, interaction-state table with base → derived formulas and contrast checks, derived and left totals, and reference-theme discriminant; every ambiguous duplicate has a user decision; every candidate is classified as write, report, undetermined, derived, left, or report-only; font-size targets are explicitly excluded; every representability check traces actual option output; the theme role is proven draft; both knowledge docs have a recorded version-ladder result and a passing completeness gate when scanned; and the tooling ledger lists browser, Figma access, Shopify access, temporary working directory, and any temporary installs.

## Phase 2 — Plan (stop for approval)

Present the complete plan and stop. Write only after the user approves the plan. Approval covers the complete observed-binding table, each hand-tuned value on its own line, every nearest-option report, every approved breakpoint pair with both values, and the bulk set of uniform values that changes current settings.

The plan contains:

1. **Theme identity and safety** — repo path, branch, connected theme id/name, proof it is draft, and the files whose sibling keys will be preserved.
2. **Figma inventory verdict** — pages, components, canonical duplicate choices, excluded duplicates, orphans, declared variables/styles, and measured values.
3. **Observed-binding table** — every candidate setting, its observed element and frame, current value, declared default, proposed value, uniformity, representability, and action. Include undetermined and non-uniform rows; keep them visible.
4. **Hand-tuned table** — each current value that differs from its declared default as its own approval line; ordinary uniform values are approved through the complete observed-binding table.
5. **Add-setting-and-rewire branch** — the proposal, site, ownership, emission, regression, and outcome artifacts required by [`references/add-setting-and-rewire.md`](references/add-setting-and-rewire.md), with individual approvals.
6. **Interaction-state derivations** — one row per hover/focus/active/disabled candidate: base setting and observed value, foreground, `L`, fixed step and direction, existing/new consumer variable, base → derived value, contrast ratio and threshold, approval, and derived/left status. State the total derived and total left.
7. **Typography exclusions** — every existing font-size setting inventoried but left out of the write set, with the text-block owner of any deviation. Record any weight carried by an existing font-picker separately; add no standalone weight global.
8. **Breakpoint decisions** — one row per token: viewport evidence, both values, existing/new counterpart, type/options, consumer, cost, and approval. A same-value or one-viewport result is written as **No breakpoint-specific global needed — pass**.
9. **Separator-collision list** — both variable names, their observed elements, and the unresolved/approved treatment.
10. **Reference-theme discriminant** — the seven factory-colour settings, with primary hover explicitly present.
11. **Inheritance residue** — every raw per-instance value that disagrees with a global candidate, whether that global is written, unchanged, or undetermined, each read from the inheritance trace with its section/block and evidence. These are reported only; no repair is planned here.
12. **Write set** — exact existing `current.<setting-id>` keys and values, approved derived interaction settings, each approved new setting's schema/default change with no `current` value, and each purpose-qualified consumer edit with its exact old/new source. Include approved non-typography breakpoint schema/consumer files with their exact changes. Existing typography counterparts may be updated only when already present. State that `blocks`, `sections`, and `content_for_index` remain unchanged and that no whole object is replaced. Existing schema defaults remain unchanged except for an approved new setting's declared default; a new breakpoint counterpart uses its own declared default.
13. **Undetermined and non-uniform values** — the values that keep their current state and the skill/section that owns the future deviation, where known.
14. **Verification** — JSON/schema parse, emission reconciliation before browser access, option-render trace, derived-expression and contrast checks, reuse-derived measured properties for every approved site, captures only for unresolved questions, Shopify theme check where available, draft preview, and a plan-versus-outcome report.
15. **Artifacts and cleanup** — `.agent/figma-shopify-globals/` paths, `.git/info/exclude`, temporary tools, ledger entries, and retained deliberate leftovers.

### Plan completion criterion

The plan is complete only when the complete observed-binding table covers every candidate, the linked add-setting branch completion criterion passes with individual approvals, the interaction-state table names every derived or left candidate and its counts, every derived row shows base → derived plus foreground contrast evidence, typography exclusions are explicit, every hand-tuned value is isolated on its own approval line, every reported/undetermined setting is named, every write cites an element and frame or an approved base setting, every representability check records actual option output, every breakpoint decision shows both values or the pass statement, the seven-setting reference discriminant is present or explicitly recorded as not this fixture, the exact key-by-key and site-by-site write set is shown, and the user has approved it.

## Phase 3 — Implement (main agent only)

Touch only the approved files. Delegated scanners do not edit theme settings.

1. Re-check the connected theme is still the same draft theme and the branch is unchanged from the approved plan.
2. Read `config/settings_data.json` and validate the approved current values before writing.
3. Write approved existing-global values one key at a time under `current`. For an approved derived interaction state, update only the named existing setting or add the named variable in the existing global-variable layer with its base reference; never replace the planned relation with a literal derived colour. For an approved non-typography breakpoint pair, add only the named counterpart schema/consumer changes and use its declared default; for typography, update only an existing counterpart. Never rewrite the base setting's type. Preserve the `blocks`, `sections`, and `content_for_index` siblings byte-for-byte. Preserve every unapproved current value, including all font-size settings.
4. If the add-setting branch is approved and not report-only, apply its implementation and emission gates from the linked reference before any consumer-site edit. A report-only branch retains its proposal and approvals without changing the theme.
5. Append the approved run line to an existing knowledge doc's `updates:` list only when this run changes a fact that belongs there and the doc is at this skill's format; the append goes under `updates:` and nowhere else. A higher-format doc is read-as-newer and left byte-for-byte unchanged. Refresh the doc gate after an append.
6. Write the retained observed-binding table and run report under `.agent/figma-shopify-globals/`. Keep the Figma inventory and the source evidence with it.

The implementation scope includes only approved interaction-state derivations and the approved add-setting-and-rewire branch. It ends before arbitrary new globals, unapproved interaction states or consumer sites, hardcoded derived values where a live base reference is required, value-only rewiring, edits on a report-only theme, typography globals beyond existing family/font-picker/line-height settings, font-size sync, averaged non-uniform values, ramp-neighbour selection, raw section/block repair, `current` object replacement, app-configuration writes, page-layout rewrites, and declared setting-type changes.

### Implement completion criterion

Every approved setting and purpose-qualified consumer site meets its linked branch criterion, every unapproved key and protected sibling is unchanged, the observed-binding, add-setting, and interaction-state tables record final values and derived/left totals, the knowledge-doc gate passes, and `git diff` contains only the approved theme/config and site changes plus artifact/exclusion changes.

## Phase 4 — Verify

Verification compares the approved plan with the draft theme after the writes.

### Static checks

- Parse `config/settings_data.json` and confirm the approved keys resolve to the approved values.
- Parse the settings schema and confirm every existing setting's id, type, default, and options are unchanged. If a breakpoint counterpart was approved, confirm only the named new schema entry exists and its type/options match the plan.
- Confirm every approved derived variable references its named base variable, uses the fixed `ΔL = 0.08` direction recorded in the plan, and contains no hardcoded derived colour.
- Recompute every derived base → derived pair and record the WCAG 2 contrast ratio against its own foreground, threshold, and pass/fail; a failed or unresolvable check remains in the left count.
- Apply the linked add-setting reference's pre-browser emission reconciliation and default/current checks.
- Apply its per-site purpose, unchanged-unattributable, and individual-approval checks.
- Confirm every existing font-size setting is unchanged and no typography setting was added. Any changed weight is carried only by an existing font-picker setting whose type already supports it.
- Re-run the option-render trace: a named option that carries the design value is a pass; a genuine gap names the nearest option and its real rendered value.
- Compare the pre-write and post-write `current.blocks`, `current.sections`, and `current.content_for_index` values byte-for-byte.
- Confirm no unapproved `current` key changed and no whole-object replacement occurred.
- Run `shopify theme check` on the changed surface when the CLI is available; record the command and result.

### Rendered checks

Use the draft preview or `shopify theme dev` and inspect every page, template, or route recorded in the reuse inventory's regression surface for each approved consumer site. Figma frames supply value evidence, not regression-page selection. For every approved binding, record the rendered property, expected value, actual value, element, frame/page, viewport, and pass/fail. A component without a reuse-inventory route is reported as unreachable with its evidence; verify an owning surface only when that surface is itself recorded by the reuse inventory.

For a setting with a declared global variable, inspect the resolved custom property and the final computed style. For an option or constrained range, inspect the actual rendered value. Verify both viewport values for every approved breakpoint pair. For a raw per-instance shadow, record the mismatch in the inheritance residue; it is not a failed global write because this skill reports that downstream work.

For each derived interaction state, inspect the base and interaction custom properties, the computed colour, its foreground, and the rendered state. In a disposable draft-preview check, change the base temporarily and verify that the derived variable moves with it; restore the base before the final outcome check.

For the add-setting-and-rewire branch, apply the linked reference's measured-property, capture, and per-site restoration gates.

### Outcome checks

Compare the observed-binding table with the final theme:

- every approved uniform binding passes or carries a named representability gap with the nearest option and its real value;
- every non-uniform binding remains unchanged and is reported;
- every unexercised setting remains unchanged and is listed as undetermined;
- every existing typography family/font-picker/line-height write is uniform, while font-size settings remain unchanged;
- every radius and page-width/padding write is uniform;
- every breakpoint pair has both approved values, and every no-pair result is recorded as **No breakpoint-specific global needed — pass**;
- every interaction candidate is counted exactly once as derived or left, every derived row shows base → derived and its contrast result, and no derived value was selected from ramp position;
- every hand-tuned replacement is individually present in the outcome;
- every separator collision remains visible;
- every reference-theme factory-colour setting is accounted for, including primary hover and the complete set of seven, or the connected draft is explicitly recorded as not that fixture;
- every raw per-instance value that disagrees with any global candidate is listed from the inheritance trace and left untouched.
- the linked add-setting-and-rewire reference's outcome criterion passes.

### Verify completion criterion

Verification is complete only when the static checks pass, every approved binding and derived interaction state has a rendered or explicitly unreachable result at each relevant viewport/state, the linked add-setting-and-rewire verification criterion passes, the plan-versus-outcome table accounts for every candidate and exclusion, derived and left totals reconcile, every representability decision is evidenced by rendered output, the seven-setting discriminant is complete, all protected siblings are unchanged, and the final artifact report plus tooling ledger is retained.

## Final output

Use a compact, evidence-first report:

- draft theme identity and branch;
- files changed and protected sibling confirmation;
- Figma inventory counts and duplicate/orphan decisions;
- observed-binding result per setting: written · non-uniform/left · undetermined/left · nearest representable option;
- add-setting-and-rewire result from [`references/add-setting-and-rewire.md`](references/add-setting-and-rewire.md), including its proposal, site, ownership, emission, regression, approval, and outcome artifacts;
- interaction-state result: derived and left totals, with each row's base → derived value, formula, foreground contrast, and reason left;
- typography exclusions and results: existing family/font-picker/line-height only; font-size unchanged and no standalone weight global;
- breakpoint decision per token, with both values or **No breakpoint-specific global needed — pass**;
- each hand-tuned approval and result;
- separator-collision warnings;
- the seven reference-theme factory-colour settings, with primary hover named, or the explicit not-this-fixture result;
- raw per-instance values that disagree with any global candidate;
- static and rendered verification results;
- knowledge-doc status for both paths: created, refreshed, read as fresh, or read as newer, with completeness counts or declared shortfall;
- observed-binding artifact path `.agent/figma-shopify-globals/` and its file inventory;
- tooling ledger with removal confirmation, or `nothing installed`.

## Rules

- One Figma file link supplies the complete frame inventory; frame-level links are not inputs.
- Observed element evidence decides values. Names, separators, ramp positions, and numeric suffixes only identify candidates and warnings.
- Apply the linked add-setting-and-rewire reference when a missing global or purpose-qualified consumer rewire is in scope.
- Interaction states absent from the design are derived values, never observed values; label them derived and show base → derived for approval.
- Derive interaction colours from the approved base's HSL lightness with fixed `ΔL = 0.08`; lighten at `L ≤ 0.50`, darken above it, and clamp. Never select a ramp neighbour.
- When no interaction setting exists, add a base-referencing variable in the existing global-variable layer; never hardcode a derived colour that would stop tracking the base.
- Check every derived value against its own foreground using WCAG 2 contrast thresholds, and leave any ambiguous or failing candidate with a named reason.
- Report how many interaction candidates were derived and how many were left; their sum must equal the candidate count.
- Read declared Figma variables, styles, and resolved font specifications directly; measure undeclared values and retain the method. Read weight, size, and line-height from the resolved font specification, never from a style name.
- Write only a uniform, directly evidenced value to a global: colours, radius, page width/padding, and existing typography family/line-height. Report non-uniform values and leave them for the skill that owns the deviating section.
- Never add a typography global. Font sizes are text-block values and never sync; a resolved weight may affect an existing font-picker only when its type already supports it.
- Trace the actual rendered value of every existing option before declaring a gap. If no option carries the design value, report the nearest option and its real rendered value.
- Create a breakpoint counterpart only when two values for one token are observed at two viewports; show both for approval. Never create a typography global: update an existing typography counterpart only, otherwise leave the difference to the text block. Report **No breakpoint-specific global needed — pass** when no pair is evidenced.
- Never rewrite a setting's type. An approved breakpoint counterpart is a separate declared setting, not a conversion of its base.
- Keep unexercised settings at their current values and label them undetermined.
- Give every setting write its element, node id, frame, property, and source evidence.
- Give every current-versus-default replacement its own approval line.
- Write `settings_data.json` by individual keys under `current`; preserve app configuration and page-layout siblings.
- Keep the run on a proven draft theme.
- Keep `.agent/` out of git through `.git/info/exclude`; retain the observed-binding artifact for review and the next run.
- Installed CLI tools run directly; missing tools use an on-demand runner, never a global install. Record temporary installs and remove them at cleanup.
- The run stays standalone. Downstream skills receive reported inheritance residue through the final artifact, not an automatic invocation.

## Usage

```
Use the figma-shopify-globals skill.
- Figma file: <one file link>
- Draft theme: <connected draft theme or shopify.theme.toml environment>
```
