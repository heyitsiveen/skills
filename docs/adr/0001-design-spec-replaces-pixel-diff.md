# The design spec replaces the pixel-diff loop

`figma-shopify-builder`, `figma-shopify-composer` and `shopify-app-restyle` each closed with an iterative pixel-diff gate: capture the render, diff it against the Figma screenshot, diagnose from the diff image, fix, repeat up to eight times per breakpoint against a ≤1% threshold. It worked, and it was the slowest and most token-expensive part of every run. We removed it from all three. In its place, `figma-spec.md` is promoted to the design spec — the single authority a build reads from — and the run ends with a style report (computed styles vs the spec's values) plus the rendered result saved to the visual-check folder for the user to judge by eye.

## The belief being tested

The premise is narrow and falsifiable: **if the design spec describes the Figma design exactly, the loop is not needed.** The loop was never the thing producing accuracy; it was the net under a spec nobody trusted to be sufficient. So the spec gained what the net used to catch — layout intent, stacking and overlap, and the spacing rhythm between groups — written from the Figma screenshot rather than the node tree, each claim backed by a value from the design context.

If that premise is false, the correct repair is to fix the design spec, not to restore the loop.

## Consequences

**Passing is no longer numeric, and the skills stopped claiming it is.** The style report cannot fail a build; it reports. "Fidelity is measured … never eyeballed" left all three `description:` lines, and "proven pixel-accurate" left the README. Pixel accuracy is still the goal — it is no longer a claim the skill makes on its own behalf. The judgment moved to a human, deliberately.

**The rescue loop is deferred, not deleted.** A user-invoked fourth skill, `figma-shopify-pixel-match`, would re-run the diff against a retained visual-check folder. The name is reserved and unbuilt: building it now would hedge the premise before it has been measured, and an available rescue path gets reached for reflexively. Ship, run several real designs, count the miss rate, then decide. The old machinery remains in this repo's git history. So that the skill stays buildable later without a migration, the design spec already records its producer and that producer's permitted write surface — builder may edit a section file, composer template JSON only, restyle only its override stylesheet.

**Two mechanisms survive with rewritten rationale.** Hardcode-then-revert and its stranded-hardcode check were justified by "the diff would measure a hole"; they are now justified by "the result screenshot would show a hole". The real risk they address — an unwanted edit left live in a client's theme — never had anything to do with measurement.

**Verify-section byte-identity was rejected in favour of a named shape.** The three skills share a seven-step Phase 4 with exactly one permitted variation each (builder: the data check; composer: reconciling the style report against the fidelity forecast; restyle: a per-state axis). Byte-identity would have forced papering over real differences; naming the permitted variations keeps the rule enforceable by reading rather than by `cmp`.
