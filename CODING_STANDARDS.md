# Coding standards

Read at **review** time, not while writing. This file holds the rules that need **judgement** — the ones no script can decide. The mechanical rules are not here: they are assertions in `scripts/check.sh`, because a check can fail and a sentence in a Markdown file cannot.

The conventions themselves live in [`CLAUDE.md`](CLAUDE.md); this is where they get enforced. When a check turns out to be wrong, change the rule in `CLAUDE.md` and the assertion in `check.sh` **in the same commit** — a check nobody believes is worse than no check.

## What `check.sh` already asserts — don't review for these

| # | Assertion |
| ---: | :--- |
| 1 | The two knowledge-doc format specs are byte-identical across the five producer skills |
| 2 | `## Asset export` is byte-identical across the three Figma-driven skills |
| 3 | Every skill is listed in all three registries |
| 4 | The retired pixel-diff vocabulary appears in no spec-driven skill, nor the README |
| 5 | Phase 4's seven steps are present, in order, with no eighth |
| 6 | Each spec-driven skill specifies the design spec's producer header |
| 7 | Every registry entry names a directory that exists |
| 8 | `## Asset export` requests PDF and carries the alpha check |
| 9 | Every skill sits at `<bucket>/<domain>/<skill>/SKILL.md` under a known bucket, folder named exactly its `name:` |
| 10 | Every skill carries a non-empty `name:` and `description:` |
| 11 | No skill occupies the reserved name `figma-shopify-pixel-match` |
| 12 | The root glossary is `GLOSSARY.md`, and no tracked doc still names the filename it replaced |
| 13 | Every `<sub>.myshopify.com` host in a tracked file, `deprecated/` included, names a placeholder store, never a client's |

Run `./scripts/check.sh` from anywhere. The script's header comment is the authoritative list; this table is a convenience copy, so trust the script where they disagree.

## Judgement calls — review for these

### Phase 4 has exactly three variations

`check.sh` asserts the seven steps are present and in order. It cannot tell whether a **fourth variation** has crept in, and `CLAUDE.md` is explicit that this one is enforced by reading the four Phase 4 sections, not by `cmp`.

The three permitted variations: builder's metafield/metaobject data check (step 2); reconciliation against the fidelity forecast (step 6), shared by composer and `shopify-page-replicate`; and restyle's per-state axis (steps 3, 4 and 6 run per state as well as per breakpoint). Anything else is a rule break.

**Not variations, though they read like them:** `shopify-page-replicate`'s step 5 splitting by pass (settings values for a reused section, code edits for a replica) is each surface's existing constraint applied. Its two approval stops are deliberate — see ADR 0004.

### Duplication that is deliberate

Three sets of text are duplicated **on purpose**, and `check.sh` asserts they stay identical. A reviewer's instinct to factor them into one shared file is the thing to resist: the point is that each skill carries its own copy, and that a change to one forces a conscious change to all.

| Duplicated text | Across |
| :--- | :--- |
| `references/theme-capabilities-format.md`, `references/components-format.md` | the five producer skills |
| `## Asset export` | the three Figma-driven skills |

### Divergence that is deliberate

The mirror image, and the easier mistake: forcing consistency where the skills genuinely differ. `## Asset delivery` and `## Hardcode-then-revert` diverge across the three because their write surfaces differ — builder owns a section file, composer only template JSON, restyle only its override stylesheet. Where a skill cannot reach a destination it says so rather than downgrading silently.

`shopify-page-replicate` sits outside the asset-export set on purpose: it exports nothing from Figma, so holding its `## Asset capture` to that section would be wrong rather than consistent.

### `deprecated/` is a snapshot, not a bucket

It holds byte-identical copies of skills as they stood before a rewrite. Nothing reads a skill from it, it appears in no registry, and `check.sh` skips it. To roll back, copy the folder over its `<bucket>/<domain>/` counterpart — then expect the retired-vocabulary and Phase 4 assertions to fail until the copy is brought forward.

**Reject:** a registry entry pointing into `deprecated/`; a skill edited in place there; a snapshot taken of something that was never rewritten.

### Descriptions are triggers, not summaries

A model-invoked skill fires on its `description` and nothing else. `check.sh` only checks one exists. Whether it fires at the *right* time is the review.

**Reject:** a description that summarises what the skill does without naming the situations that should trigger it; synonyms that rename one trigger rather than adding a distinct branch; a description that would fire on tasks the skill cannot do.

### Invocation grouping

`README.md` groups each category under **User-invoked** / **Model-invoked**. A skill is user-invoked when it is a slash command or its frontmatter sets `user-invocable: true` or `disable-model-invocation: true`. The grouping cannot be checked mechanically, because a slash command carries no frontmatter flag — so confirm by hand that a skill's README group matches how it is actually reached.

### Don't re-litigate ADRs

`docs/adr/` records decisions that were expensive to make. If a change contradicts one, say so explicitly and reopen the ADR; don't quietly override it.

### Scope

A new skill earns its place only when the behaviour does not compose from existing ones. Prefer extending a skill over adding one, and prefer a shared reference file over a third copy of the same prose — except where the duplication is deliberate, above.

## Upstream alignment

This repo borrows its agent-skill conventions from [mattpocock/skills](https://github.com/mattpocock/skills), currently **v1.3.1**. Both halves of that are review material.

**Adopted.** The domain-doc convention is upstream's: a root `GLOSSARY.md` plus `docs/adr/`, renamed in v1.3.0 from the filename it carried before. `docs/agents/domain.md` and `docs/agents/issue-tracker.md` are this repo's copies of the `setup-matt-pocock-skills` templates, so re-running that skill should read as a clean diff against them rather than a rewrite. Three sections of `issue-tracker.md` are local additions the template lacks, and a re-run must keep them: "When working in a git worktree", "When an implementation ticket is done" and "When orchestrating a feature's tickets". Assertion 12 holds the rename down; nothing holds the templates in step, so check them by hand when upstream moves.

**Not adopted.** Three divergences, each deliberate:

- Upstream banned em-dashes from its own prose in v1.3.0. This repo keeps them: every `SKILL.md` here is written with them. Don't rewrite one to match upstream's house style.
- `setup-matt-pocock-skills` writes a `docs/agents/triage-labels.md` whenever `triage` is installed, and it is. This repo has none. `triage` is for issues you did **not** create, and every ticket under `.scratch/` came from `to-tickets`, which `ask-matt` says explicitly not to triage. A label table nothing reads goes stale unread. Write one the day an issue arrives from outside, not before.
- `GLOSSARY-FORMAT.md` caps a definition at one or two sentences and bans implementation detail. **Welding** and **Pre-flight** break both, and stay: welding is a failure mode whose definition *is* the behaviour it describes, and a pre-flight that doesn't name what it audits can't be checked against. Tighten a glossary entry when it has drifted into spec, not merely when it is long.
