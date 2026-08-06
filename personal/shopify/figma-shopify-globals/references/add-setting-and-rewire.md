# Add a setting and rewire its consumers

This is a gated branch of `figma-shopify-globals`. Reach it only when the observed-binding pass finds a uniform design purpose that the theme does not expose as a global, or when an approved new global needs existing consumers pointed at it. Read this reference in full before researching, planning, or editing this branch.

## Guard

Prove the theme's authorship before proposing an edit. Record the repository and theme evidence that shows the agency owns the code. When agency authorship is unproven, produce the complete proposal and site inventory as report-only output; approvals remain visible, but the branch makes no setting or consumer write.

On an agency-authored theme, approval is per consumer site. A setting proposal, a code site, and a verification result are separate rows. One approval never authorizes a batch of sites.

## Research

### 1. Propose one setting at a time

Start with the observed purpose, not a repeated literal. Name what the value paints and where the design uses it. A candidate is eligible only when the same purpose recurs across the selected design and no existing global serves it.

Record one proposal row per setting:

| setting purpose | observed evidence | proposed id/type/default | existing alternative | files/sites to edit | cost | ownership | status |
|---|---|---|---|---|---|---|---|
| `<what it paints>` | `<element + frame + node>` for every recurrence | `<id>` · `<type>` · `<design value>` | `<setting or none>` | `<exact paths and lines>` | `<schema + consumer + verification work>` | agency · unproven | propose · report |

The evidence column lists every recurrence that establishes uniformity. The cost names the schema entry, emitted variable, consumer files, and regression pages that would change. An existing global that already serves the purpose turns this branch into an ordinary observed-binding write; it does not justify a duplicate setting.

### 2. Attribute consumer sites by purpose

Inventory every existing consumer that should use the proposed setting. Inspect the component, section, block, snippet, stylesheet, and variable assignment around each occurrence. For each site, write a sentence in this form:

> `<file:line>` paints `<named purpose>` for `<component>` and should read `<global variable/setting>`.

The purpose sentence is the qualification gate. A value search may locate candidates, but equality never qualifies a site. Qualify only a site whose component role, rendered property, and target global are all named. Keep each qualified site as an individual approval row.

Occurrences whose purpose cannot be named stay byte-for-byte unchanged. Count them by file, property, and reason in the proposal and final report. Do not fold them into the approved site count.

### 3. Build the regression surface from reuse

Read or refresh `.agent/COMPONENTS.md`. For each approved site, enumerate every page, template, or route in the reuse inventory where its owning component is used. This is the regression surface. Figma frames can provide evidence for the value, but never add pages to this surface.

### 4. Reconcile emitted variables before opening a browser

For every variable the branch introduces, build an emission table before any browser or preview command:

| introduced variable | declared setting/default | emission layer and source | consumer reference | emitted name matches | result |
|---|---|---|---|---|---|
| `--<name>` | `<schema id>` · `<default>` | `<exact file:line>` | `<exact file:line>` | yes · no | pass · left |

Trace the setting through the schema and the theme's existing global-variable layer to the emitted custom property. Compare the exact emitted name with every new consumer reference. A variable that cannot be proven to emit is left with its reason and blocks browser verification for that site. The browser opens only after every approved introduced variable has a passing row.

## Plan and approval

Present the proposal rows, emission table, and consumer-site rows together. Approval names each setting and each site. For a new setting, the plan adds its declared default and leaves `settings_data.json` without a recorded `current` value; the default remains available to the client and a later default change continues to apply. For an existing setting, the plan changes only its recorded `current` value and leaves its declared default untouched.

Each consumer row includes the exact old and new source, the property it affects, the reuse-derived regression pages, the verification tier, and its individual approval state. A report-only theme shows the same rows and proposed diff but keeps every action as `report`.

## Implementation

Re-check the branch, draft theme, authorship evidence, and approvals immediately before editing.

1. On a report-only theme, write none of this branch's setting or consumer changes. Retain the proposed changes and approval states in the report.
2. Add a new setting only in the declared schema/global layer. Use the observed value as its declared default and omit a `current` entry from `settings_data.json`.
3. Update an existing setting only at its approved `current.<id>` key. Preserve its declared default and every unrelated sibling.
4. Run the emission reconciliation before editing any consumer site. A failed row leaves that site untouched and counted.
5. Rewire approved consumer sites one at a time from the named old source to the named global reference. Preserve the exact source snapshot for each site. A value-only replacement has no approval path.

## Verification tiers

Use the cheapest tier that answers the question, in order:

1. **Emission reconciliation** — static source/schema proof that every introduced variable emits and every approved consumer references the emitted name.
2. **Measured properties** — on every reuse-derived regression page, read the affected property's computed value and record expected, actual, source site, page, viewport, and pass/fail.
3. **Captures** — capture only an affected surface that tiers 1 and 2 cannot answer; record the unresolved question and why a capture is necessary. A capture never replaces a cheaper check.

If a site causes an unintended change, restore only that site's saved source snapshot, leave other approved sites standing, and re-run the emission and measured checks for the remaining set. Record the reverted site and the evidence; do not roll back the run globally.

## Branch completion criterion

The branch is complete only when every missing global has an individual evidence-and-cost proposal, every consumer site is qualified by a named purpose or counted as unattributable and unchanged, authorship and report-only status are explicit, new settings use defaults without recorded values, existing settings preserve defaults, every introduced variable passes emission reconciliation before browser access, every approved site's full reuse-derived regression surface has measured affected properties, captures are justified as the third tier, and any unintended change is reverted at only its site.
